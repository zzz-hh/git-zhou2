# import pdb
# pdb.set_trace()
from fediux.FL.utils.base import BaseModel
import numpy as np
from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file
from fediux.utils.logger_util import logger


class LightGBMServer(BaseModel):

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
        logger.info(method)
        if method == 'Plaintext':
            server = Plaintext_LightGBM_Server(client_channel)
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


class Plaintext_LightGBM_Server:

    def __init__(self, client_channel):
        self.client_channel = client_channel
        self.trees=[]
        self.recv_output_dims()
        self.recv_params()

    def recv_output_dims(self):
        Output_Dims = self.client_channel.recv_all('output_dim')

        self.output_dim = max(Output_Dims)
        if self.output_dim == 1:
            self.multiclass = False
        else:
            self.multiclass = True

        self.client_channel.send_all("output_dim", self.output_dim)

    def recv_params(self):
        self.num_examples_weights = self.client_channel.recv_all('num_examples')

    def client_model_aggregate(self):
        client_trees = self.client_channel.recv_all('client_trees')
        for  tree in client_trees:
            self.trees.append(tree)

    def server_model_broadcast(self):
        self.client_channel.send_all("server_trees", self.trees)

    def train(self):
        self.client_model_aggregate()
        self.server_model_broadcast()

    def get_scalar_metrics(self, metrics_name):
        metrics_name = metrics_name.lower()
        supported_metrics = ['loss', 'acc']
        if metrics_name not in supported_metrics:
            error_msg = f"""Unsupported metrics {metrics_name}, use {supported_metrics} instead"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        client_metrics = self.client_channel.recv_all(metrics_name)

        return np.average(client_metrics, weights=self.num_examples_weights)

    def get_metrics(self):
        server_metrics = {}

        acc = self.get_scalar_metrics('acc')
        server_metrics["train_acc"] = acc

        logger.info(f"acc={acc}")

        return server_metrics


    def print_metrics(self):
        self.get_metrics()
