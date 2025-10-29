# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from itertools import chain, combinations
from typing import Callable, List, Dict, Any


class BaseContributionAssessor(ABC):
    @abstractmethod
    def run(
        self,
        client_index_for_this_round: List,  # 数据参与方索引列表
        aggregation_func: Callable,
        local_weights_from_clients: List[Dict],
        acc_on_last_round: float,
        acc_on_aggregated_model: float,
        val_dataloader: Any,
        validation_func: Callable[[Dict, Any, Any], float],
        device,
    ):  # -> List[float]:
        pass

    @abstractmethod
    def get_final_contribution_assignment(self) -> dict:
        pass

    @staticmethod
    def get_aggregated_model_with_client_subset(aggregation_func, local_weights_from_clients, client_subset_list):
        """
        :param aggregation_func: 聚合函数
        :param local_weights_from_clients: 所有客户端的本地模型参数集合
        :param client_subset_list: 当前参与本轮训练的客户端索引列表
        :return:
            aggregated model with the client subset
        """
        local_weights_from_subset = {
            client_index: local_weights_from_clients[client_index] for client_index in client_subset_list
        }
        return aggregation_func(local_weights_from_subset)

    @staticmethod
    def generate_power_set(input_iterable):
        """
        生成输入集合的幂集
        powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)
        """
        s = list(input_iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))
