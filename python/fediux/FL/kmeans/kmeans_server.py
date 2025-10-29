# _*_ coding: utf-8 _*_
import numpy as np
from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file
from fediux.FL.preprocessing import StandardScaler
from fediux.utils.logger_util import logger


class KmeansServer(BaseModel):
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
        
        # data preprocessing
        scaler = StandardScaler(FL_type='H',
                                role=self.role_params['self_role'],
                                channel=client_channel)
        scaler.fit()

        # server init
        method = self.common_params['method']
        if method == 'Plaintext':
            server = Plaintext_Server(client_channel)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # model training
        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i+1} / {global_epoch} --------")
            server.train()

            if self.common_params['print_metrics']:
                server.print_metrics()
        logger.info("-------- finish training --------")

        # receive final metrics
        trainMetrics = server.get_metrics()
        save_json_file(trainMetrics, self.role_params['metric_path'])


class Plaintext_Server:

    def __init__(self, client_channel):
        self.client_channel = client_channel

        self.recv_params()

    def recv_params(self):
        self.num_examples_weights = self.client_channel.recv_all('num_examples')
        self.num_examples_weights_sum = sum(self.num_examples_weights)

    def client_model_aggregate(self):
        client_models = self.client_channel.recv_all('client_model')
        logger.info(f"client_models: {client_models}")

        # 初始化聚合后的中心点矩阵
        aggregated_centers = np.zeros_like(client_models[0])
        
        # 计算加权平均值
        for i, model in enumerate(client_models):
            weight = self.num_examples_weights[i] / self.num_examples_weights_sum
            aggregated_centers += model * weight
            
        # 更新服务器模型
        self.k_points = aggregated_centers
        logger.info(f"aggregated_centers: {aggregated_centers}")

    def server_model_broadcast(self):
        self.client_channel.send_all("server_model", self.k_points)

    def train(self):
        self.client_model_aggregate()
        self.server_model_broadcast()

    def get_scalar_metrics(self, metrics_name):
        metrics_name = metrics_name.lower()
        supported_metrics = ['silhouette']
        if metrics_name not in supported_metrics:
            error_msg = f"""Unsupported metrics {metrics_name},
                          use {supported_metrics} instead"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        client_metrics = self.client_channel.recv_all(metrics_name)

        # 计算加权平均轮廓系数
        weighted_sum = sum(m * w for m, w in zip(client_metrics, self.num_examples_weights))
        metrics = weighted_sum / self.num_examples_weights_sum
        
        return float(metrics)

    def get_metrics(self):
        server_metrics = {}

        silhouette = self.get_scalar_metrics('silhouette')
        server_metrics["silhouette"] = silhouette
        logger.info(f"silhouette={silhouette}")

        return server_metrics

    def print_metrics(self):
        self.get_metrics()

