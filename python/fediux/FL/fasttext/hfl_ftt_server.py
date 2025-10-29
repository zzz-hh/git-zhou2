from collections import Counter
from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file
from fediux.FL.utils.base import check_contribution_alg
from fediux.utils.logger_util import logger

import torch
import torch.nn as nn

from python.fediux.contribution.contribution_assessor_manager import ContributionAssessorManager
from .base import create_model


class FasttextServer(BaseModel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        process = self.common_params['process']
        role_name = self.role_params.get('self_name', 'unknown')
        logger.info(f"[Algorithm] Horizontal FastText | role={role_name} | process={process}")
        logger.info(f"process: {process}")
        if process == 'train':
            self.train()
        else:
            error_msg = f"Unsupported process: {process}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def train(self):
        # setup communication channels
        remote_parties = self.roles[self.role_params['others_role']]
        client_channel = MultiGrpcClients(local_party=self.role_params['self_name'],
                                          remote_parties=remote_parties,
                                          node_info=self.node_info,
                                          task_info=self.task_info)
        # server init
        # Get cpu or gpu device for training.
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using {device} device")

        method = self.common_params['method']
        if method == 'Plaintext':
            server = Plaintext_Server(method,
                                      self.common_params,
                                      device,
                                      client_channel)
        elif method == 'DPSGD':
            server = DPSGD_Server(method,
                                  self.common_params['vocab_size'],
                                  self.common_params['max_seq_len'],
                                  self.common_params['embedding_dim'],
                                  device,
                                  client_channel)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # model training
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

        # receive final metrics
        trainMetrics = server.get_metrics()
        if server.contribution_alg:
            contribution = server.get_contribution()
            client_channel.send_all("contribution", contribution)
            trainMetrics['contribution'] = contribution
        save_json_file(trainMetrics, self.role_params['metric_path'])


class Plaintext_Server:

    def __init__(self, method, common_params, device, client_channel):
        self.device = device
        self.client_channel = client_channel
        self.party_dict = {i:party for i, party in enumerate(client_channel.remote_parties)}
        self.indices = list(self.party_dict.keys())
        max_seq_len = common_params['max_seq_len']
        embedding_dim = common_params['embedding_dim']
        contribution_alg = common_params.get('contribution_alg', None)
        self.contribution_alg = check_contribution_alg(contribution_alg)

        client_num_in_total = len(client_channel.remote_parties)
        self.accessor = ContributionAssessorManager(self.contribution_alg, client_num_in_total)
        
        self.multiclass = None
        self.output_dim = None
        self.vocab_size = common_params['vocab_size']
        self.recv_output_dims()

        self.model = create_model(method, self.vocab_size, embedding_dim, self.output_dim, device)

        self.input_shape = (max_seq_len,embedding_dim)
        # self.recv_input_shapes()
        self.recv_vocabs()
        self.lazy_module_init()

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


    def recv_vocabs(self):
        # recv vocabs for all clients
        counters = self.client_channel.recv_all('input_token_count')
        merged_counter = Counter()
        for counter in counters:
            merged_counter.update(counter)
        most_common = merged_counter.most_common(self.vocab_size)
        vocab_list = [word for word, _ in most_common]
        self.client_channel.send_all("vocab_list", vocab_list)

    def lazy_module_init(self):
        nn.init.xavier_uniform_(self.model.embedding.weight)

        # 初始化全连接层的权重和偏置
        nn.init.xavier_uniform_(self.model.fc.weight)
        nn.init.zeros_(self.model.fc.bias)

        self.model.load_state_dict(self.model.state_dict())

        self.server_model_broadcast()

    def recv_params(self):
        # receive other params to compute aggregated metrics
        self.num_examples_weights = self.client_channel.recv_all('num_examples')
        self.num_examples_weights = torch.tensor(self.num_examples_weights,
                                                 dtype=torch.float32).to(self.device)
        self.num_examples_weights_sum = self.num_examples_weights.sum()

    def client_model_aggregate(self):
        recv_models = self.client_channel.recv_all("client_model")
        self.client_models = {idx: model for idx, model in enumerate(recv_models)}

        server_model = self.model_aggregate(self.client_models)        
        self.model.load_state_dict(server_model)

    def model_aggregate(self, client_models):
        server_model = self.model.state_dict()
        for layer in server_model:
            clayers = []
            for idx, cmodel in client_models.items():
                clayers.append(cmodel[layer])

            if len(clayers) == 1:
                server_model[layer] = clayers[0]
            else:
                server_model[layer] = torch.stack(clayers,
                                              dim=len(server_model[layer].size())) \
                                    @ self.num_examples_weights \
                                    / self.num_examples_weights_sum
        return server_model

    def server_model_broadcast(self, prefix=''):
        self.client_channel.send_all("server_model",
                                     self.model.state_dict(prefix=prefix))

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

    def get_scalar_metrics(self, metrics_name):
        metrics_name = metrics_name.lower()
        supported_metrics = ['loss', 'acc', 'mse', 'mae']
        if metrics_name not in supported_metrics:
            error_msg = f"""Unsupported metrics {metrics_name},
                          use {supported_metrics} instead"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        client_metrics = self.client_channel.recv_all(metrics_name)

        metrics = torch.tensor(client_metrics, dtype=torch.float).to(self.device) \
                        @ self.num_examples_weights \
                        / self.num_examples_weights_sum
        return float(metrics)

    def get_metrics(self):
        server_metrics = {}

        loss = self.get_scalar_metrics('loss')
        server_metrics["train_loss"] = loss

        acc = self.get_scalar_metrics('acc')
        server_metrics["train_acc"] = acc

        logger.info(f"loss={loss}, acc={acc}")

        return server_metrics

    def print_metrics(self):
        self.get_metrics()


class DPSGD_Server(Plaintext_Server):

    def train(self, round_idx):
        self.client_model_aggregate()
        # opacus make_private will add '_module.' prefix
        self.server_model_broadcast(prefix='_module.')
