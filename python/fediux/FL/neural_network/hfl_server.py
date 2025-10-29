import random
import numpy as np
from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel, check_contribution_alg
from fediux.FL.utils.file import save_json_file
from fediux.utils.logger_util import logger
from fediux.FL.preprocessing import StandardScaler

import torch

from python.fediux.contribution.contribution_assessor_manager import ContributionAssessorManager
from .base import create_model,supported_metrics


class NeuralNetworkServer(BaseModel):
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
        # 1. 固定随机种子
        seed = 42
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        np.random.seed(seed)
        random.seed(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
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

        contribution_alg = self.common_params.get('contribution_alg', None)
        method = self.common_params['method']
        if method == 'Plaintext':
            server = Plaintext_Server(method,
                                      self.common_params['task'],
                                      device,
                                      client_channel,
                                      contribution_alg)
        elif method == 'DPSGD':
            server = DPSGD_Server(method,
                                  self.common_params['task'],
                                  device,
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

        server.set_regression_mse()

        # model training
        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i + 1} / {global_epoch} --------")
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

    def __init__(self, method, task, device, client_channel, contribution_alg):
        self.task = task
        self.device = device
        self.client_channel = client_channel
        self.party_dict = {i:party for i, party in enumerate(client_channel.remote_parties)}
        self.indices = list(self.party_dict.keys())
        self.contribution_alg = check_contribution_alg(contribution_alg)

        client_num_in_total = len(client_channel.remote_parties)
        self.accessor = ContributionAssessorManager(self.contribution_alg, client_num_in_total)

        self.multiclass = None
        self.output_dim = None
        self.recv_output_dims()

        self.model = create_model(method, self.output_dim, device)

        self.input_shape = None
        self.recv_input_shapes()
        self.lazy_module_init()

        self.recv_params()
        if self.multiclass:
            self.acc_on_last_round = 1/self.output_dim 
        else:
            self.acc_on_last_round = 0.5

    def set_regression_mse(self):
        if self.contribution_alg and self.task == 'regression':
            self.acc_on_last_round = -self.get_scalar_metrics('mse') # 取相mse反数
            logger.info(f"acc_on_last_round={self.acc_on_last_round}")

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

    def recv_input_shapes(self):
        # recv input shapes for all clients
        Input_Shapes = self.client_channel.recv_all('input_shape')

        # check if all input shapes are the same
        all_input_shapes_same = True
        input_shape = Input_Shapes[0]
        for idx, cinput_shape in enumerate(Input_Shapes):
            if input_shape != cinput_shape:
                all_input_shapes_same = False
                error_msg = f"""Not all input shapes are the same,
                                client {list(self.client_channel.Clients.keys())[idx]}'s
                                input shape is {cinput_shape},
                                but others' are {input_shape}"""
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        # send signal of input shapes to all clients
        self.client_channel.send_all("input_dim_same", all_input_shapes_same)

        if all_input_shapes_same:
            self.input_shape = input_shape

    def lazy_module_init(self):
        input_shape = list(self.input_shape)
        # set batch size equals to 1 to initialize lazy module
        input_shape.insert(0, 1)
        self.model.forward(torch.ones(input_shape).to(self.device))
        torch.manual_seed(42)          # 再次固定，防止后续 init 带来差异
        self.model.apply(self._init_weights)  # 自定义初始化
        self.model.load_state_dict(self.model.state_dict())

        self.server_model_broadcast()

    def _init_weights(self, m):
        """统一初始化方式，保证可复现"""
        # logger.info(f"Initialize module {m}"+"*"*40)
        if isinstance(m, torch.nn.Conv2d):
            torch.nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            if m.bias is not None:
                torch.nn.init.zeros_(m.bias)
        elif isinstance(m, torch.nn.BatchNorm2d):
            torch.nn.init.ones_(m.weight)
            torch.nn.init.zeros_(m.bias)
        elif isinstance(m, torch.nn.Linear):
            torch.nn.init.xavier_uniform_(m.weight)
            if m.bias is not None:
                torch.nn.init.zeros_(m.bias)

    def recv_params(self):
        # receive other params to compute aggregated metrics
        self.num_examples_weights = self.client_channel.recv_all('num_examples')
        self.num_examples_weights = torch.tensor(self.num_examples_weights, dtype=torch.float32).to(self.device)
        self.num_examples_weights_sum = self.num_examples_weights.sum()

    def client_model_aggregate(self):
        # logger.info("*" * 50)
        logger.info("Start receive all model")
        recv_models = self.client_channel.recv_all("client_model")
        self.client_models = {idx: model for idx, model in enumerate(recv_models)}
        # logger.info("*" * 50)
        logger.info("end receive self.client_model_aggregate")
        server_model = self.model_aggregate(self.client_models)
        self.model.load_state_dict(server_model)

    def model_aggregate(self, client_models):
        server_model = self.model.state_dict()
        for layer in server_model:
            clayers = []
            for idx, cmodel in client_models.items():
                clayers.append(cmodel[layer].float())

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
        logger.info("*"*50)
        logger.info("Start receive self.client_model_aggregate")
        self.client_model_aggregate()
        # 先评估贡献度，再更新模型
        if self.contribution_alg:
            # 当前轮次聚合模型的准确率
            acc_on_last_round = self.acc_on_last_round
            index = 'acc'
            if self.task == 'regression':
                index = 'mse'
            self.acc_on_last_round = self.get_scalar_metrics(index)
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
        logger.info("receive self.client_model_aggregate")

        self.server_model_broadcast()
        logger.info("end receive self.client_model_aggregate")

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
        index = 'acc'
        if self.task == 'regression':
            index = 'mse'
        return self.get_scalar_metrics(index)

    def contribution_over(self):
        """
        贡献度计算结束，发送结束信号</br>
        """
        valid_data = {"status":1}
        self.client_channel.send_all("valid_data", valid_data)

    def get_scalar_metrics(self, metrics_name):
        metrics_name = metrics_name.lower()

        if metrics_name.replace("train_","") not in supported_metrics:
            error_msg = f"""Unsupported metrics {metrics_name.lower("train_",'')},
                          use {supported_metrics} instead"""
            logger.error(error_msg)


            raise RuntimeError(error_msg)

        client_metrics = self.client_channel.recv_all(metrics_name)
        if metrics_name.replace("train_","") == 'confusion_matrix':
            metrics = torch.tensor(client_metrics).sum(dim=0).numpy().tolist()
            return metrics
        else:
            metrics = torch.tensor(client_metrics, dtype=torch.float).to(self.device) \
                      @ self.num_examples_weights \
                      / self.num_examples_weights_sum
            return float(metrics)

    def get_metrics(self):
        server_metrics = {}

        if self.task == 'classification':
            loss = self.get_scalar_metrics('loss')
            server_metrics["train_loss"] = loss

            #metrics_name = ["acc", "f1", "precision", "recall", "auc", "confusion_matrix"]
            metrics_name = self.client_channel.recv_all("metrics_keys")[0]
            # if self.output_dim == 1:
            #     metrics_name.append("ks")
            #     metrics_name.append("roc")
            #     metrics_name.append("bimodal")

            logger.info(metrics_name)
            for name in metrics_name:
                if name not in supported_metrics:
                    continue

                metrics = self.get_scalar_metrics(name)
                server_metrics[ name] = metrics
            # metrics_name.pop(-1)
            # metrics_name.pop(-1)
            logger.info(f"metrics={server_metrics}")

        if self.task == 'regression':
            mse = self.get_scalar_metrics('mse')
            server_metrics["train_mse"] = mse

            mae = self.get_scalar_metrics('mae')
            server_metrics["train_mae"] = mae

            logger.info(f"mse={mse}, mae={mae}")

        return server_metrics

    def print_metrics(self):
        self.get_metrics()


class DPSGD_Server(Plaintext_Server):

    def train(self, round_idx):
        self.client_model_aggregate()
        # 先评估贡献度，再更新模型
        logger.info("self.contribution_alg : {}".format(self.contribution_alg))
        if self.contribution_alg:
            # 当前轮次聚合模型的准确率
            acc_on_last_round = self.acc_on_last_round
            index = 'acc'
            if self.task == 'regression':
                index = 'mse'
            self.acc_on_last_round = self.get_scalar_metrics(index)
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
        # opacus make_private will add '_module.' prefix
        self.server_model_broadcast(prefix='_module.')
