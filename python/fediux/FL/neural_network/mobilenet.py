# -*- coding:utf-8 -*-
# @Project   :PyCharm
# @FileName  :mobilenet.py
# @Time      :2025/3/11 上午10:14
# @Author    :liujiachang
# @Email     :liujiachang@cmict.chinamobile.com
import torch
from torch import nn
from torchvision import models


class MobileNet(nn.Module):
    def __init__(self, output_dim):
        super().__init__()
        self.layers = models.mobilenet_v3_small(num_classes=output_dim, weights=None)

    def forward(self, x):
        output = self.layers(x)
        return output
