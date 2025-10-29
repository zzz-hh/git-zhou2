# -*- coding:utf-8 -*-
# @Project   :PyCharm
# @FileName  :hfl_mobilenet_server.py
# @Time      :2025/3/11 上午10:14
# @Author    :liujiachang
# @Email     :liujiachang@cmict.chinamobile.com
from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel, check_contribution_alg
from fediux.FL.utils.file import save_json_file
from fediux.utils.logger_util import logger

import torch

from python.fediux.contribution.contribution_assessor_manager import ContributionAssessorManager
from .base import create_model
from .hfl_server import Plaintext_Server as MLP_Plaintext_Server
from .hfl_server import DPSGD_Server as MLP_DPSGD_Server


class Server(BaseModel):
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

        contribution_alg = self.common_params.get('contribution_alg', None)
        method = self.common_params['method']
        if method == 'Plaintext':
            server = Plaintext_Server(method,
                                      device,
                                      client_channel,
                                      contribution_alg)
        elif method == 'DPSGD':
            server = DPSGD_Server(method,
                                  device,
                                  client_channel,
                                  contribution_alg)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

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


class Plaintext_Server(MLP_Plaintext_Server):

    def __init__(self, method, device, client_channel, contribution_alg):
        self.task = 'classification'
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

        self.model = create_model(method,
                                  self.output_dim,
                                  device,
                                  'mobilenet')

        self.input_shape = None
        self.recv_input_shapes()
        self.lazy_module_init()

        self.num_examples_weights = None
        self.recv_params()
        if self.multiclass:
            self.acc_on_last_round = 1/self.output_dim 
        else:
            self.acc_on_last_round = 0.5


class DPSGD_Server(Plaintext_Server, MLP_DPSGD_Server):

    def train(self):
        MLP_DPSGD_Server.train(self)
