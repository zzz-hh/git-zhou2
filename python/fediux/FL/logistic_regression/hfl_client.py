# _*_ coding: utf-8 _*_
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
from fediux.FL.utils.base import check_contribution_alg

import pandas as pd
import numpy as np
import dp_accounting
from sklearn.utils.validation import check_array
from sklearn.model_selection import train_test_split

from .base import LogisticRegression,\
                  LogisticRegression_DPSGD,\
                  LogisticRegression_Paillier


class LogisticRegressionClient(BaseModel):
    
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
        id = self.common_params['id']
        x = read_data(data_info=self.role_params['data'],
                      selected_column=selected_column,
                      droped_column=id)
        label = self.common_params['label']
        y = x.pop(label).values
        feature_names = x.columns.tolist()
        x = check_array(x, dtype='numeric')

        # client init
        method = self.common_params['method']
        contribution_alg = self.common_params.get('contribution_alg', None)
        contribution_alg = check_contribution_alg(contribution_alg)
        if method == 'Plaintext':
            client = Plaintext_Client(x, y,
                                      self.common_params['learning_rate'],
                                      self.common_params['alpha'],
                                      server_channel,
                                      contribution_alg)
        elif method == 'DPSGD':
            client = DPSGD_Client(x, y,
                                  self.common_params['learning_rate'],
                                  self.common_params['alpha'],
                                  contribution_alg,
                                  self.common_params['noise_multiplier'],
                                  self.common_params['l2_norm_clip'],
                                  self.common_params['secure_mode'],
                                  server_channel)
        elif method == 'Paillier':
            client = Paillier_Client(x, y,
                                     self.common_params['learning_rate'],
                                     self.common_params['alpha'],
                                     contribution_alg,
                                     server_channel)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # data preprocessing
        scaler = StandardScaler(FL_type='H',
                                role=self.role_params['self_role'],
                                channel=server_channel)
        x = scaler.fit_transform(x)

        # get test_size
        test_size = 0.2
        try:
            test_size = self.common_params['test_size']
        except:
            logger.info("test_size use default value 0.2")

        # data split
        X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=test_size, random_state=42)

        # client training
        num_examples = client.num_examples
        batch_size = min(num_examples, self.common_params['batch_size'])
        if method == 'DPSGD':
            # DP data loader: Poisson sampling
            train_dataloader = DPDataLoader(X_train, y_train,
                                            batch_size)
        else:    
            train_dataloader = DataLoader(X_train, y_train,
                                          batch_size,
                                          shuffle=False)

        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i+1} / {global_epoch} --------")
            
            local_epoch = self.common_params['local_epoch']
            for j in range(local_epoch):
                logger.info(f"-------- local epoch {j+1} / {local_epoch} --------")
                for batch_x, batch_y in train_dataloader:
                    client.model.fit(batch_x, batch_y)

            client.train(X_train, y_train) # 更新为聚合模型

            # print metrics
            if self.common_params['print_metrics']:
                client.print_metrics(X_train, y_train)
        logger.info("-------- finish training --------")

        # send final epsilon when using DPSGD
        if method == 'DPSGD':
            delta = self.common_params['delta']
            steps = global_epoch * local_epoch * num_examples // batch_size
            eps = client.compute_epsilon(steps, batch_size, delta)
            server_channel.send("eps", eps)
            logger.info(f"For delta={delta}, the current epsilon is {eps}")
        # receive plaintext model when using Paillier
        elif method == 'Paillier':
            client.model.set_theta(server_channel.recv("server_model"))
        
        # send final metrics
        trainMetrics = client.send_metrics(X_test, y_test)
        if client.contribution_alg:
            contribution = server_channel.recv("contribution")
            logger.info(f"contribution: {contribution}")
            trainMetrics["contribution"] = contribution
        trainMetrics["train_feature_names"] = feature_names
        trainMetrics["train_feature_importances"] = client.get_feature_weights()
        save_json_file(trainMetrics, self.role_params['metric_path'])

        # save model for prediction
        modelFile = {
            "selected_column": selected_column,
            "id": id,
            "label": label,
            "preprocess": scaler.module,
            "model": client.model
        }
        save_pickle_file(modelFile, self.role_params['model_path'])

    def predict(self):
        # load model for prediction
        modelFile = load_pickle_file(self.role_params['model_path'])

        # load dataset
        origin_data = read_data(data_info=self.role_params['data'])

        x = origin_data.copy()
        selected_column = modelFile['selected_column']
        if selected_column:
            x = x[selected_column]
        id = modelFile['id']
        if id in x.columns:
            x.pop(id)
        label = modelFile['label']
        if label in x.columns:
            y = x.pop(label).values
        x = check_array(x, dtype='numeric')

        # data preprocessing
        scaler = modelFile['preprocess']
        x = scaler.transform(x)

        # test data prediction
        model = modelFile['model']
        pred_prob = model.predict_prob(x)

        if model.multiclass:
            pred_y = np.argmax(pred_prob, axis=1)
            pred_prob = pred_prob.tolist()
        else:
            pred_y = np.array(pred_prob > 0.5, dtype='int')

        result = pd.DataFrame({
            'pred_prob': pred_prob,
            'pred_y': pred_y
        })
        
        data_result = pd.concat([origin_data, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])


class Plaintext_Client:

    def __init__(self, x, y, learning_rate, alpha, server_channel, contribution_alg=None):
        self.contribution_alg = contribution_alg
        self.model = LogisticRegression(x, y, learning_rate, alpha)
        self.param_init(x, y, server_channel)

    def param_init(self, x, y, server_channel):
        self.server_channel = server_channel

        self.send_output_dim(y)

        self.num_examples = x.shape[0]
        self.send_params()

    def train(self, x, y):
        self.server_channel.send("client_model", self.model.get_theta())
        # 确认接收次数
        if self.contribution_alg:
            self.valid(x, y)
            mid_valid_data = self.server_channel.recv("valid_data")
            status = mid_valid_data['status']
            while status == 0:
                # 更新模型并评估
                self.model.set_theta(mid_valid_data['valid_model'])
                self.valid(x, y)

                mid_valid_data = self.server_channel.recv("valid_data")
                status = mid_valid_data['status']

        # 更新模型
        self.model.set_theta(self.server_channel.recv("server_model"))
    
    def valid(self, x, y):
        y_score = self.model.predict_prob(x)
        metrics = classification_metrics(
            y,
            y_score,
            multiclass=self.model.multiclass,
            metrics_name=["acc",],
        )
        self.server_channel.send("acc", metrics["acc"])

    def send_output_dim(self, y):
        # assume labels start from 0
        output_dim = y.max() + 1

        if output_dim == 2:
            # binary classification
            output_dim = 1

        self.server_channel.send('output_dim', output_dim)
        output_dim = self.server_channel.recv('output_dim')
        
        # init theta
        if self.model.multiclass:
            if output_dim != self.model.bias.shape[1]:
                self.model.set_theta(
                    np.zeros((self.model.weight.shape[0] + 1, output_dim))
                )
        else:
            if output_dim > 1:
                self.model.set_theta(
                    np.zeros((self.model.weight.shape[0] + 1, output_dim))
                )
                self.model.multiclass = True

    def send_params(self):
        self.server_channel.send('num_examples', self.num_examples)

    def send_loss(self, x, y):
        loss = self.model.loss(x, y)
        if self.model.alpha > 0:
            loss -= 0.5 * self.model.alpha * (self.model.weight ** 2).sum()
        logger.info(f"loss: {loss}")
        self.server_channel.send("loss", loss)
        return loss

    def get_feature_weights(self):
        # 获取权重参数(排除bias)
        weights = self.model.weight.flatten()
        abs_weights = np.abs(weights)
        total = np.sum(abs_weights)
        if total > 0:
            feature_weights = abs_weights / total
        else:
            feature_weights = np.zeros_like(abs_weights)
        return feature_weights.tolist()

    def send_metrics(self, x, y):
        self.send_loss(x, y)

        y_score = self.model.predict_prob(x)
        if self.model.multiclass:
            metrics = classification_metrics(
                y,
                y_score,
                multiclass=self.model.multiclass,
                prefix="train_",
                metrics_name=["acc",
                              "f1",
                              "precision",
                              "recall",
                              "auc",],
            )
        else:
            metrics = classification_metrics(
                y,
                y_score,
                multiclass=self.model.multiclass,
                prefix="train_",
                metrics_name=["acc",
                              "f1",
                              "precision",
                              "recall",
                              "auc",
                              "roc",
                              "ks",
                              "confusion_matrix",
                              "bimodal"],
            )

        self.server_channel.send("acc", metrics["train_acc"])
        return metrics

    def print_metrics(self, x, y):
        self.send_loss(x, y)

        y_score = self.model.predict_prob(x)
        metrics = classification_metrics(
            y,
            y_score,
            multiclass=self.model.multiclass,
            metrics_name=["acc",],
        )

        self.server_channel.send("acc", metrics["acc"])


class DPSGD_Client(Plaintext_Client):

    def __init__(self, x, y, learning_rate, alpha, contribution_alg,
                 noise_multiplier, l2_norm_clip, secure_mode,
                 server_channel):
        self.contribution_alg = contribution_alg
        data_size = len(x)
        self.model = LogisticRegression_DPSGD(x, y, learning_rate, alpha,
                                              noise_multiplier, l2_norm_clip, secure_mode,random_seed = data_size)
        self.param_init(x, y, server_channel)

    def compute_epsilon(self, steps, batch_size, delta):
        if self.model.noise_multiplier == 0.0:
            return float('inf')
        orders = [1 + x / 10. for x in range(1, 100)] + list(range(12, 64))
        accountant = dp_accounting.rdp.RdpAccountant(orders)

        sampling_probability = batch_size / self.num_examples
        event = dp_accounting.SelfComposedDpEvent(
            dp_accounting.PoissonSampledDpEvent(
                sampling_probability,
                dp_accounting.GaussianDpEvent(self.model.noise_multiplier)), steps)

        accountant.compose(event)
        
        if delta >= 1. / self.num_examples:
            logger.error(f"delta {delta} should be set less than 1 / {self.num_examples}")
        return accountant.get_epsilon(target_delta=delta)
    

class Paillier_Client(Plaintext_Client, Paillier):

    def __init__(self, x, y, learning_rate, alpha,contribution_alg,
                 server_channel):
        self.contribution_alg = contribution_alg
        self.model = LogisticRegression_Paillier(x, y, learning_rate, alpha)
        self.param_init(x, y, server_channel)

        self.public_key = server_channel.recv("public_key")
        self.model.set_theta(self.encrypt_vector(self.model.get_theta()))
        if self.contribution_alg:
            self.send_loss(x, y)

    def send_loss(self, x, y):
        # pallier only support compute approximate loss without penalty
        loss = self.model.loss(x, y)
        self.server_channel.send("loss", loss)
        return loss
    
    def valid(self, x, y):
        self.send_loss(x, y)

    def print_metrics(self, x, y):
        # print loss
        self.send_loss(x, y)
        logger.info('View metrics at server while using Paillier')
