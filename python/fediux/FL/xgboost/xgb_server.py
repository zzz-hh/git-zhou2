from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file
from fediux.utils.logger_util import logger
from fediux.FL.preprocessing import StandardScaler

from typing import List
import numpy as np
from .base import *
import copy

class XGBServer(BaseModel):

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
        # setup communication channels
        remote_parties = self.roles[self.role_params['others_role']]
        client_channel = MultiGrpcClients(local_party=self.role_params['self_name'],
                                          remote_parties=remote_parties,
                                          node_info=self.node_info,
                                          task_info=self.task_info)

        # server init
        method = self.common_params['method']
        if method == 'Plaintext':
            server = Plaintext_Server(client_channel)
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

        server.train()

        # print metrics
        if self.common_params['print_metrics']:
            server.print_metrics()
        logger.info("-------- finish training --------")

        # receive final metrics
        trainMetrics = server.get_metrics()
        save_json_file(trainMetrics, self.role_params['metric_path'])


class Plaintext_Server:

    def __init__(self, client_channel):
        self.client_channel = client_channel
        self.input_shape = None
        self.recv_input_shapes()
        self.output_dim = None
        self.global_model = None
        self.recv_output_dims()
        self.recv_params()

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

    def recv_output_dims(self):
        # recv output dims for all clients
        Output_Dims = self.client_channel.recv_all('output_dim')

        # set final output dim
        self.output_dim = max(Output_Dims)

        # send output dim to all clients
        self.client_channel.send_all("output_dim", self.output_dim)

    def recv_params(self):
        self.num_examples_weights = self.client_channel.recv_all('num_examples')
        self.num_examples_weights = np.array(self.num_examples_weights)
        self.num_examples_weights_sum = self.num_examples_weights.sum()

    def client_model_aggregate(self):
        """聚合客户端状态"""
        client_models = self.client_channel.recv_all("client_model")
        for xgb_model in client_models:
            if self.global_model is None:

                self.global_model = xgb_model
            else:
            
                global_model = copy.copy(self.global_model)
                self.global_model =aggregate(global_model, xgb_model)

    def server_model_broadcast(self):
        """生成可序列化的广播参数"""
        return self.client_channel.send_all("server_model", self.global_model)

    def train(self):
        self.client_model_aggregate()
        self.server_model_broadcast()

    def get_scalar_metrics(self, metrics_name):
        metrics_name = metrics_name.lower()
        supported_metrics = ['acc']
        if metrics_name not in supported_metrics:
            error_msg = f"""Unsupported metrics {metrics_name}, use {supported_metrics} instead"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        client_metrics = self.client_channel.recv_all(metrics_name)
        logger.info(f"client {metrics_name}: {client_metrics}")
        return np.average(client_metrics, weights=self.num_examples_weights)

    def get_metrics(self):
        server_metrics = {}

        acc = self.get_scalar_metrics('acc')
        server_metrics["train_acc"] = acc

        logger.info(f"acc={acc}")

        return server_metrics

    def print_metrics(self):
        self.get_metrics()
