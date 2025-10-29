# -*- coding:utf-8 -*-
# @Project   :PyCharm
# @FileName  :yolo_client.py
# @Time      :2025/3/27 下午2:47
# @Author    :liujiachang
# @Email     :liujiachang@cmict.chinamobile.com
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.net_work import GrpcClient
from fediux.utils.logger_util import logger

import os
import time


class YOLOClient(BaseModel):

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
        role_params = self.role_params

        num_examples = self.role_params['num_examples']
        #send num_sampes
        remote_party = self.roles[self.role_params['others_role']]
        self.channel = GrpcClient(local_party=self.role_params['self_name'],
                                  remote_party=remote_party,
                                  node_info=self.node_info,
                                  task_info=self.task_info)
        self.channel.send('num_examples', num_examples)

        path = role_params['path']
        os.chdir(path)
        global_epoch = self.common_params["global_epoch"]
        data_config = self.role_params["data_config"]
        checkpoint = "/app/model/yolov5s.pt"
        for i in range(global_epoch):
            timestamp = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))
            cmd = f"python3 train.py \
                        --img 640 \
                        --epochs 1 \
                        --data {data_config} \
                        --name {timestamp} \
                        --workers 0 \
                        --weights {checkpoint} \
                        "

            print(f"cmd is {cmd}")
            os.system(cmd)
            time.sleep(5)  # for save
            import torch
            ckpt = torch.load(os.path.join(path, "runs/train", timestamp, "weights", "last.pt"))
            model = ckpt['model'].state_dict()
            del torch

            self.channel.send(f'client_res_{i}', model)
            res = self.channel.recv(f'server_res_{i}')
            import torch
            ckpt['model'].load_state_dict(res)
            torch.save(ckpt, os.path.join(path, "runs/train", timestamp, "weights", "last.pt"))
            if i == global_epoch - 1:
                os.makedirs(os.path.dirname(self.role_params["model_path"]), exist_ok=True)
                torch.save(ckpt, self.role_params["model_path"])
            del torch
            checkpoint = f"runs/train/{timestamp}/weights/last.pt"


    def predict(self):
        model_path = self.role_params['model_path']
        source = self.role_params['source']
        predict_path = self.role_params['predict_path']
        path = self.role_params['path']
        timestamp = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))
        os.chdir(path)
        cmd = f"python3 detect.py \
                    --imgsz 640 \
                    --weights {model_path} \
                    --source {source} \
                    --name {timestamp} \
                    "
        print(f"cmd is {cmd}")
        os.system(cmd)
        time.sleep(5)  # for save
        os.makedirs(predict_path, exist_ok=True)
        os.system(f"cp -r runs/detect/{timestamp} {predict_path}")
