import copy
from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file
from fediux.utils.logger_util import logger
import torch


class PegasusServer(BaseModel):
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
        # Get cpu or gpu device for training.
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using {device} device")

        server = Plaintext_Server(device, client_channel)

        # model training
        logger.info("-------- server start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- server global epoch {i+1} / {global_epoch} --------")
            server.train()

            if self.common_params['print_metrics']:
                server.print_metrics()
        logger.info("-------- server finish training --------")

        # receive final metrics
        trainMetrics = server.get_metrics()
        save_json_file(trainMetrics, self.role_params['metric_path'])


class Plaintext_Server:

    def __init__(self, device, client_channel):
        self.device = device
        self.client_channel = client_channel

        self.output_dim = None
        self.recv_params()

    def recv_params(self):
        # receive other params to compute aggregated metrics
        self.num_examples_weights = self.client_channel.recv_all('num_examples')
        self.num_examples_weights = torch.tensor(self.num_examples_weights,
                                                 dtype=torch.float32).to(self.device)
        self.num_examples_weights_sum = self.num_examples_weights.sum()

    def client_model_aggregate(self):
        client_models = self.client_channel.recv_all('client_model')

        self.server_model = client_models[0]
        for layer in self.server_model:
            clayers = []
            for cmodel in client_models:
                clayers.append(cmodel[layer])

            self.server_model[layer] = torch.stack(clayers,
                                              dim=len(self.server_model[layer].size())) \
                                    @ self.num_examples_weights \
                                    / self.num_examples_weights_sum

    def server_model_broadcast(self):
        server_model = copy.deepcopy(self.server_model)
        self.client_channel.send_all("server_model", server_model)

    def train(self):
        self.client_model_aggregate()
        self.server_model_broadcast()

    def get_metrics(self):
        server_metrics = {}

        metrics = self.client_channel.recv_all('avg_rouge')
        if metrics and len(metrics) > 0:
            # 获取所有key
            keys = metrics[0].keys()
            # 对每个key进行加权平均
            for key in keys:
                values = torch.tensor([m[key] for m in metrics], dtype=torch.float).to(self.device)
                weighted_avg = values @ self.num_examples_weights / self.num_examples_weights_sum
                server_metrics[key] = float(weighted_avg)
        
        logger.info(f"Metrics: {server_metrics}")
        return server_metrics

    def print_metrics(self):
        self.get_metrics()
