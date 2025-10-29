# _*_ coding: utf-8 _*_
from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file
from fediux.utils.logger_util import logger
from fediux.FL.crypto.paillier import Paillier
from fediux.FL.preprocessing import StandardScaler
from fediux.FL.utils.base import check_contribution_alg
from fediux.contribution.contribution_assessor_manager import ContributionAssessorManager

import numpy as np
from phe import paillier

class LogisticRegressionServer(BaseModel):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        process = self.common_params['process']
        logger.info(f"process: {process}")
        if process == 'train':
            self.train()
        else:
            error_msg = f"Unsupported process: {process}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def train(self):
        remote_parties = self.roles[self.role_params['others_role']]
        client_channel = MultiGrpcClients(local_party=self.role_params['self_name'],
                                          remote_parties=remote_parties,
                                          node_info=self.node_info,
                                          task_info=self.task_info)

        # server init
        method = self.common_params['method']
        contribution_alg = self.common_params.get('contribution_alg', None)
        contribution_alg = check_contribution_alg(contribution_alg)
        if method == 'Plaintext' or method == 'DPSGD':
            server = Plaintext_DPSGD_Server(self.common_params['alpha'],
                                            client_channel,
                                            contribution_alg)
        elif method == 'Paillier':
            server = Paillier_Server(self.common_params['alpha'],
                                     self.common_params['n_length'],
                                     client_channel,
                                     contribution_alg)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # data preprocessing
        scaler = StandardScaler(FL_type='H',
                                role=self.role_params['self_role'],
                                channel=client_channel)
        scaler.fit()

        # server training
        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i+1} / {global_epoch} --------")
            server.train(i)

            # print metrics
            if self.common_params['print_metrics']:
                server.print_metrics()
        logger.info("-------- finish training --------")

        # receive final epsilons when using DPSGD
        if method == 'DPSGD':
            delta = self.common_params['delta']
            eps = client_channel.recv_all("eps")
            logger.info(f"For delta={delta}, the current epsilon is {max(eps)}")
        # send plaintext model when using Paillier
        elif method == 'Paillier':
            server.plaintext_server_model_broadcast()

        # receive final metrics
        trainMetrics = server.get_metrics()
        if server.contribution_alg:
            contribution = server.get_contribution()
            client_channel.send_all("contribution", contribution)
            trainMetrics['contribution'] = contribution
        save_json_file(trainMetrics, self.role_params['metric_path'])


class Plaintext_DPSGD_Server:

    def __init__(self, alpha, client_channel, contribution_alg=None):
        # setup contribution assessor
        self.contribution_alg = contribution_alg
        client_num_in_total = len(client_channel.remote_parties)
        self.accessor = ContributionAssessorManager(self.contribution_alg, client_num_in_total) 

        self.alpha = alpha
        self.client_channel = client_channel
        self.party_dict = {i:party for i, party in enumerate(client_channel.remote_parties)}
        self.indices = list(self.party_dict.keys())

        self.theta = None
        self.multiclass = None
        self.recv_output_dims()

        self.recv_params()
        if self.multiclass:
            self.acc_on_last_round = 1/self.output_dim 
        else:
            self.acc_on_last_round = 0.5

    def recv_output_dims(self):
        # recv output dims for all clients
        Output_Dims = self.client_channel.recv_all('output_dim')

        # set final output dim
        self.output_dim = max(Output_Dims)
        if self.output_dim == 1:
            self.multiclass = False
        else:
            self.multiclass = True

        # send output dim to all clients
        self.client_channel.send_all("output_dim", self.output_dim)

    def recv_params(self):
        self.num_examples_weights = self.client_channel.recv_all('num_examples')

    def client_model_aggregate(self):
        recv_models = self.client_channel.recv_all("client_model")
        self.client_models = {idx: model for idx, model in enumerate(recv_models)}

        self.theta = self.model_aggregate(self.client_models)

    def model_aggregate(self, client_models):
        model_weights = [self.num_examples_weights[i] for i in client_models.keys()]
        client_models = list(client_models.values())
        return np.average(client_models,
                                weights=model_weights,
                                axis=0)

    def server_model_broadcast(self):
        self.client_channel.send_all("server_model", self.theta)

    def train(self, round_idx):
        self.client_model_aggregate()
        # 先评估贡献度，再更新模型
        if self.contribution_alg:
            # 当前轮次聚合模型的准确率
            acc_on_last_round = self.acc_on_last_round
            self.acc_on_last_round = self.get_scalar_metrics('acc')
            self.accessor.run(
                client_index_for_this_round=self.indices,
                aggregation_func=self.model_aggregate,
                local_weights_from_clients=self.client_models,
                acc_on_last_round=acc_on_last_round, 
                acc_on_aggregated_model=self.acc_on_last_round, 
                validation_func=self.validate,
                round_idx=round_idx
            )
            self.contribution_over()
            self.get_contribution()

        # 更新模型
        self.server_model_broadcast()

    def get_contribution(self):
        contribution = self.accessor.get_final_contribution_assignment()
        mapped_contribution = {self.party_dict[key]: contribution[key] for key in self.party_dict if key in contribution}
        logger.info(f"contribution: {mapped_contribution}")
        return mapped_contribution

    def get_loss(self):
        loss =  self.get_scalar_metrics('loss')
        if self.alpha > 0:
            loss += 0.5 * self.alpha * (self.theta ** 2).sum()
        return loss

    def get_scalar_metrics(self, metrics_name):
        metrics_name = metrics_name.lower()
        supported_metrics = ['loss', 'acc']
        if metrics_name not in supported_metrics:
            error_msg = f"""Unsupported metrics {metrics_name}, use {supported_metrics} instead"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        client_metrics = self.client_channel.recv_all(metrics_name)

        return np.average(client_metrics, weights=self.num_examples_weights)

    def validate(self, agg_model_C):
        """
        贡献计算过程中，聚合模型发送到客户端进行评估</br>
        评估指标为准确率或其他指标。</br>
        指标选择原则：值与模型表现正相关</br>
        """
        valid_data = {"valid_model": agg_model_C, "status":0}
        self.client_channel.send_all("valid_data", valid_data)
        return self.get_scalar_metrics('acc')

    def contribution_over(self):
        """
        贡献度计算结束，发送结束信号</br>
        """
        valid_data = {"status":1}
        self.client_channel.send_all("valid_data", valid_data)

    def get_metrics(self):
        server_metrics = {}

        loss = self.get_loss()
        server_metrics["train_loss"] = loss

        acc = self.get_scalar_metrics('acc')
        server_metrics["train_acc"] = acc

        logger.info(f"loss={loss}, acc={acc}")

        return server_metrics

    def print_metrics(self):
        self.get_metrics()

class Paillier_Server(Plaintext_DPSGD_Server, Paillier):

    def __init__(self, alpha, n_length, client_channel, contribution_alg):
        Plaintext_DPSGD_Server.__init__(self, alpha, client_channel, contribution_alg)
        self.public_key,\
        self.private_key = paillier.generate_paillier_keypair(n_length=n_length) 
        self.public_key_broadcast()
        if self.contribution_alg:
            self.acc_on_last_round = -self.get_loss(encrypted=True) # 取相loss反数
            logger.info(f"acc_on_last_round={self.acc_on_last_round}")

    def public_key_broadcast(self):
        self.client_channel.send_all("public_key", self.public_key)

    def client_model_aggregate(self):
        recv_models = self.client_channel.recv_all("client_model")
        self.client_models = {idx: model for idx, model in enumerate(recv_models)}

        self.theta = np.mean(recv_models, axis=0)
        self.theta = np.array(self.encrypt_vector(self.decrypt_vector(self.theta)))

    def plaintext_server_model_broadcast(self):
        self.theta = np.array(self.decrypt_vector(self.theta))
        self.server_model_broadcast()

    def get_loss(self, encrypted=False):
        client_loss = self.client_channel.recv_all('loss')
        if encrypted:
            client_loss = self.decrypt_vector(client_loss)
        loss =  np.average(client_loss, weights=self.num_examples_weights)
        logger.info(f"loss={client_loss}")
        return loss

    def train(self, round_idx):
        self.client_model_aggregate()
        # 先评估贡献度，再更新模型
        if self.contribution_alg:
            # 当前轮次聚合模型的准确率
            acc_on_last_round = self.acc_on_last_round
            self.acc_on_last_round = -self.get_loss(encrypted=True) # 取相loss反数
            self.accessor.run(
                client_index_for_this_round=self.indices,
                aggregation_func=self.model_aggregate,
                local_weights_from_clients=self.client_models,
                acc_on_last_round=acc_on_last_round, 
                acc_on_aggregated_model=self.acc_on_last_round, 
                validation_func=self.validate,
                round_idx=round_idx
            )
            self.contribution_over()
            self.get_contribution()

        # 更新模型
        self.server_model_broadcast()

    def validate(self, agg_model_C):
        """
        贡献计算过程中，聚合模型发送到客户端进行评估</br>
        评估指标为准确率或其他指标。</br>
        指标选择原则：值与模型表现正相关</br>
        """
        valid_data = {"valid_model": agg_model_C, "status":0}
        self.client_channel.send_all("valid_data", valid_data)
        return -self.get_loss(encrypted=True) # 取相loss反数

    def print_metrics(self):
        # print loss
        # pallier only support compute approximate loss
        loss = self.get_loss(encrypted=True)

        logger.info(f"loss={loss}")
