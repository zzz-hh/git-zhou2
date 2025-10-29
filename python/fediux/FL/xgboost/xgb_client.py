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
from xgboost import DMatrix
import torch
import xgboost as xgb


class XGBClient(BaseModel):

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
        y = x.pop(label).values
        x = check_array(x, dtype='numeric')

        # client init
        method = self.common_params['method']
        if method == 'Plaintext':
            client = Plaintext_Client(x, y, server_channel, self.common_params.get('max_depth'))
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # data preprocessing
        scaler = StandardScaler(FL_type='H',
                                role=self.role_params['self_role'],
                                channel=server_channel)
        x = scaler.fit_transform(x)

        # client training
        logger.info("-------- start training --------")

        client.train(x, y, self.common_params)

        # print metrics
        if self.common_params['print_metrics']:
            client.print_metrics(x, y)
        logger.info("-------- finish training --------")

        # send final metrics
        trainMetrics = client.send_metrics(x, y)
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

        x1 = DMatrix(x, label=y, enable_categorical=True)

        model = modelFile['model']
        pred_y = model.predict(x1)
        result = pd.DataFrame({
            'pred_y': pred_y
        })

        data_result = pd.concat([origin_data, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])


class Plaintext_Client:
    def __init__(self, x, y, server_channel, max_depth):
        self.model = None
        self.server_channel = server_channel

        self.input_shape = None
        self.send_input_shape(x)

        self.output_dim = None
        self.send_output_dim(y)

        self.num_examples = x.shape[0]
        self.send_params()

    def recv_server_model(self):
        return self.server_channel.recv("server_model")

    def get_model(self):
        model = self.model.copy()
        self.config = model.save_config()

        local_model = model.save_raw("json")
        local_model = bytes(local_model)
        return local_model

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
        self.output_dim = y.max() + 1

        if self.output_dim == 2:
            self.output_dim = 1

        self.server_channel.send('output_dim', self.output_dim)
        self.output_dim = self.server_channel.recv('output_dim')

    def train(self, x, y, common_params):
        test_size = 0.2
        objective = "multi:softmax"
        max_depth = 6
        num_class=4
        eta=0.3
        try:
            test_size = float(common_params["test_size"])
            num_class=int(common_params["num_class"])
            max_depth=int(common_params["max_depth"])
            objective=str(common_params["objective"])
            eta=float(common_params["eta"])
        except :
            logger.info("common_params use default value")
        params = {
            "objective": objective,  # or "objective": "multi:softprob",
            "num_class": num_class,  # Set num_classes if known
            "eta": eta,
            "max_depth": max_depth
        }

        logger.info("paras={}".format(params))

        train_dmatrix = DMatrix(x[0:int(len(x) * (1 - test_size))], label=y[0:int(len(x) * (1 - test_size))],
                                enable_categorical=True)
        valid_dmatrix = DMatrix(x[int(len(x) *  (1 - test_size)):], label=y[int(len(x) *  (1 - test_size)):], enable_categorical=True)
        self.model = xgb.train(params, train_dmatrix, num_boost_round=5,
                               evals=[(valid_dmatrix, "validate"), (train_dmatrix, "train")])

        self.server_channel.send("client_model", self.get_model())
        model_paramas = self.recv_server_model()
        model_paramas = bytearray(model_paramas)
        self.model.load_model(model_paramas)
        self.model.load_config(self.config)

    def send_metrics(self, x, y):
        x1 = DMatrix(x, label=y, enable_categorical=True)

        y_pred = self.model.predict(x1)
        y_pred = y_pred.astype(int)

        logger.info("shape={}".format(y_pred.shape))

        y_pred_torch = torch.from_numpy(y_pred)
        y_pred_torch = torch.nn.functional.one_hot(y_pred_torch)
        metrics_name = ["acc", "f1", "precision", "recall", "auc", "confusion_matrix"]

        if y_pred_torch.shape[1] == 2:
            multiclass = False
            metrics_name.append("roc")
            metrics_name.append("ks")
            metrics_name.append("bimodal")
        else:
            y_pred = y_pred_torch.detach().numpy()
            logger.info("shape={}".format(y_pred.shape))
            multiclass = True


        metrics = classification_metrics(
            y,
            y_pred,
            multiclass=multiclass,
            prefix="train_",
            metrics_name=metrics_name,
        )

        self.server_channel.send("acc", metrics["train_acc"])

        return metrics

    def print_metrics(self, x, y):
        metrics = self.send_metrics(x, y)
        logger.info("-------- metrics --------")
        logger.info(metrics)
