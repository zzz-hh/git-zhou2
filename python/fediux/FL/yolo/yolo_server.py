# -*- coding:utf-8 -*-
# @Project   :PyCharm
# @FileName  :yolo_server.py
# @Time      :2025/3/27 下午2:47
# @Author    :liujiachang
# @Email     :liujiachang@cmict.chinamobile.com
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.utils.logger_util import logger

import os
import time
import torch
from importlib import import_module
# python3 train.py --weights models/yolov5s.pt --data data/coco1.yaml --epochs 10 --project output/result --name exp1

class YOLOServer(BaseModel):

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
        self.channel = MultiGrpcClients(
            local_party=self.role_params['self_name'],
            remote_parties=remote_parties,
            node_info=self.node_info,
            task_info=self.task_info)

        num_examples_weights = self.channel.recv_all('num_examples')
        total_sample = sum(num_examples_weights)
        weights = [k / total_sample for k in num_examples_weights]

        #receive weights
        for i in range(self.common_params['global_epoch']):
            client_models = self.channel.recv_all(f'client_res_{i}')
            new_prefix_state_dict = {}

            for idx, prefix_state_dict in enumerate(client_models):
                for k, v in prefix_state_dict.items():
                    if k not in new_prefix_state_dict:
                        new_prefix_state_dict[k] = v * weights[idx]
                    else:
                        new_prefix_state_dict[k] += v * weights[idx]

            self.channel.send_all(f'server_res_{i}', new_prefix_state_dict)


    def predict(self):
        pass