import numpy as np

from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file, \
                                   save_pickle_file, \
                                   load_pickle_file, \
                                   save_csv_file
from fediux.FL.utils.dataset import read_data
from fediux.utils.logger_util import logger
from fediux.FL.preprocessing import StandardScaler
from fediux.FL.metrics import classification_metrics
import pandas as pd
from sklearn.utils.validation import check_array
from sklearn.svm import SVC
import torch
from sklearn.model_selection import train_test_split


class SVMClient(BaseModel):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        process = self.common_params['process']
        logger.info(f"process: {process}")
        if process == 'train':
            self.train()
        elif process == 'predict':
            self.predict()
        else:
            error_msg = f"Unsupported process: {process}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def train(self):
        # setup communication channels
        remote_party = self.roles[self.role_params['others_role']]
        server_channel = GrpcClient(local_party=self.role_params['self_name'],
                                    remote_party=remote_party,
                                    node_info=self.node_info,
                                    task_info=self.task_info)

        # load dataset
        selected_column = self.common_params.get('selected_column')
        if selected_column is None:
            selected_column = self.role_params.get('selected_column')
        x = read_data(data_info=self.role_params['data'],
                      selected_column=selected_column,
                      droped_column=self.common_params['id'])
        label = self.common_params['label']
        test_size = self.common_params.get('test_size', 0.2)
        y = x.pop(label).values
        x = check_array(x, dtype='numeric')
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_size, shuffle=True)
        # client init
        method = self.common_params['method']
        if method == 'Plaintext':
            client = Plaintext_Client(x_train, y_train, server_channel, self.common_params.get('kernel'))
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # data preprocessing
        scaler = StandardScaler(FL_type='H',
                                role=self.role_params['self_role'],
                                channel=server_channel)
        x_train = scaler.fit_transform(x_train)

        # client training
        logger.info("-------- start training --------")

        client.model.fit(x_train, y_train)

        client.train()

        # print metrics
        if self.common_params['print_metrics']:
            client.print_metrics(x_test, y_test)
        logger.info("-------- finish training --------")

        # send final metrics
        trainMetrics = client.send_metrics(x_test, y_test)
        save_json_file(trainMetrics, self.role_params['metric_path'])

        # save model for prediction
        modelFile = {
            "selected_column": selected_column,
            "id": self.common_params['id'],
            "label": label,
            "preprocess": scaler.module,
            "model": client.model
        }
        save_pickle_file(modelFile, self.role_params['model_path'])

    def predict(self):
        # load model for prediction
        modelFile = load_pickle_file(self.role_params['model_path'])

        # load dataset
        origin_data = read_data(data_info=self.role_params['data'],
                                selected_column=modelFile['selected_column'],
                                droped_column=modelFile['id'])

        x = origin_data.copy()
        if modelFile['label'] in x.columns:
            y = x.pop(modelFile['label']).values

        x = check_array(x, dtype='numeric')

        # data preprocessing
        scaler = modelFile['preprocess']
        x = scaler.transform(x)

        # test data prediction
        model = modelFile['model']
        pred_y = model.predict(x)

        result = pd.DataFrame({
            'pred_y': pred_y
        })

        data_result = pd.concat([origin_data, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])


class Plaintext_Client:
    def __init__(self, x, y, server_channel, kernel):
        self.kernel = kernel
        self.model = SVC(kernel=self.kernel)
        self.server_channel = server_channel

        self.input_shape = None
        self.send_input_shape(x)

        self.output_dim = None
        self.send_output_dim(y)

        self.num_examples = x.shape[0]
        self.send_params()
        self.global_model = None

    def recv_server_model(self):
        return self.server_channel.recv("server_model")

    def get_model(self):
        return {
            'coef': self.model.coef_,
            'intercept': self.model.intercept_,
            'num_samples': self.num_examples
        }

    def send_input_shape(self, x):
        self.input_shape = x[0].shape
        self.server_channel.send('input_shape', self.input_shape)

        all_input_shapes_same = self.server_channel.recv("input_dim_same")
        if not all_input_shapes_same:
            error_msg = "Input shapes don't match for all clients"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def send_params(self):
        # send other params to compute aggregated metrics
        self.server_channel.send('num_examples', self.num_examples)

    def send_output_dim(self, y):
        # assume labels start from 0
        self.output_dim = len(np.unique(y))

        if self.output_dim == 2:
            # binary classification
            self.output_dim = 1

        self.server_channel.send('output_dim', self.output_dim)
        self.output_dim = self.server_channel.recv('output_dim')

    def train(self):
        self.server_channel.send("client_model", self.get_model())
        self.global_model = self.recv_server_model()
        self._update_model()

    def _update_model(self):
        self.model.__dict__['coef_'] = self.global_model['coef']
        self.model.__dict__['intercept_'] = self.global_model['intercept']

    def send_metrics(self, x, y):
        y_true, y_pred = y, self.model.decision_function(x)
        y_pred = torch.tensor(y_pred)
        metrics_name = ["acc", "f1", "precision", "recall", "auc", "confusion_matrix"]
        if self.output_dim == 1:
            metrics_name.append("ks")
            metrics_name.append("roc")
            metrics_name.append("bimodal")
            y_score = torch.sigmoid(y_pred).reshape(-1)
            metrics = classification_metrics(
                y_true,
                y_score,
                multiclass=False,
                prefix="train_",
                metrics_name=metrics_name,
            )
        else:
            y_score = torch.softmax(y_pred, dim=1)
            metrics = classification_metrics(
                y_true,
                y_score,
                multiclass=True,
                prefix="train_",
                metrics_name=metrics_name,
            )
        if self.output_dim == 1:
            metrics_name.pop(-1)
            metrics_name.pop(-1)
        for metric in metrics_name:
            self.server_channel.send(metric, metrics[f"train_{metric}"])

        return metrics

    def print_metrics(self, x, y):
        self.send_metrics(x, y)
