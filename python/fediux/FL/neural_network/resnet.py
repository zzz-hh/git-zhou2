# -*- coding:utf-8 -*-
# @Project   :PyCharm
# @FileName  :resnet.py
# @Time      :2025/3/10 下午1:59
# @Author    :liujiachang
# @Email     :liujiachang@cmict.chinamobile.com
import torch
from torch import nn
from torchvision import models


class ResNet(nn.Module):
    def __init__(self, output_dim):
        super().__init__()
        self.layers = models.resnet18(num_classes=output_dim, weights=None)

    def forward(self, x):
        output = self.layers(x)
        return output
