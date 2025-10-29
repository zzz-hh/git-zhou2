import numpy as np

from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file,\
                                   save_pickle_file,\
                                   load_pickle_file,\
                                   save_csv_file
from fediux.FL.utils.dataset import read_data,\
                                      DataLoader,\
                                      DPDataLoader
from fediux.utils.logger_util import logger
from fediux.FL.crypto.paillier import Paillier
from fediux.FL.preprocessing import StandardScaler
from fediux.FL.metrics import classification_metrics
import pandas as pd
from sklearn.utils.validation import check_array
from sklearn.tree import DecisionTreeClassifier
import torch
from sklearn.model_selection import train_test_split


class DecisionTreeClient(BaseModel):

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
        feature_names = x.columns.tolist()
        x = check_array(x, dtype='numeric')
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_size, shuffle=True)

        # client init
        method = self.common_params['method']
        if method == 'Plaintext':
            client = Plaintext_Client(x_train, y_train, server_channel, self.common_params.get('max_depth'))
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
        trainMetrics["train_feature_names"] = feature_names
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
    def __init__(self, x, y, server_channel, max_depth):
        self.model = DecisionTreeClassifier(
            max_depth=max_depth,
            min_samples_split=10,
            random_state=42,
            min_samples_leaf=10,  # 强制叶节点最小样本数
            max_leaf_nodes=2,  # 限制最大叶节点数
        )
        self.server_channel = server_channel

        self.input_shape = None
        self.send_input_shape(x)

        self.output_dim = None
        self.send_output_dim(y)

        self.num_examples = x.shape[0]
        self.send_params()
        self.global_tree = None

    def recv_server_model(self):
        return self.server_channel.recv("server_model")

    def get_model(self):
        tree = self.model.tree_
        state = tree.__getstate__()
        return {
            'node_count': state['node_count'],
            'nodes': state['nodes'],
            'values': state['values'],
            'split_features': state['nodes']['feature'],
            'split_thresholds': state['nodes']['threshold'],
            'impurity': state['nodes']['impurity'],
            'n_node_samples': state['nodes']['n_node_samples'],
            'feature_importances': tree.compute_feature_importances()
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
        self.output_dim = y.max() + 1

        if self.output_dim == 2:
            # binary classification
            self.output_dim = 1

        self.server_channel.send('output_dim', self.output_dim)
        self.output_dim = self.server_channel.recv('output_dim')

    def train(self):
        self.server_channel.send("client_model", self.get_model())
        self.global_tree = self.recv_server_model()
        # 修改树对象参数
        tree = self.model.tree_
        self._modify_tree_structure(tree)

    def _modify_tree_structure(self, tree):
        """修改sklearn树对象内部参数"""
        original_state = tree.__getstate__().copy()

        # 2. 更新关键参数
        original_state.update({
            'node_count': self.global_tree['node_count'],
            'nodes': self.global_tree['nodes'],
            'values': self.global_tree['values'],
            'impurity': self.global_tree['impurity'],
            'n_node_samples': self.global_tree['n_node_samples']
        })

        # 4. 安全设置状态
        tree.__setstate__(original_state)

        # 5. 更新特征重要性（需重新计算）
        self.model.n_features_ = self.input_shape[0]
        self.model.n_classes_ = self.output_dim
        self.model.tree_.compute_feature_importances()

    def send_metrics(self, x, y):
        y_true, y_pred = y, self.model.predict_proba(x)
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

        metrics["train_feature_importances"] = self.model.feature_importances_.tolist()
        self.server_channel.send("train_feature_importances", metrics["train_feature_importances"])
        return metrics

    def print_metrics(self, x, y):
        self.send_metrics(x, y)


