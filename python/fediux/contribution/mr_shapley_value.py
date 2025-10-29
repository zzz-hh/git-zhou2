# -*- coding: utf-8 -*-
from typing import List, Dict, Callable, Any

import numpy as np
from scipy.special import comb

from .base_contribution_assessor import BaseContributionAssessor
from fediux.utils.logger_util import logger


class MRShapleyValue(BaseContributionAssessor):
    def __init__(self,client_num_in_total):
        super().__init__()
        self.client_num_in_total = client_num_in_total

        # trunc paras
        self.eps = 0.001
        self.round_trunc_threshold = 0.01

        self.Contribution_records = []

        # key is the round_index;
        # value is the dictionary contribution (key - client_index; value - relative contribution
        self.shapley_values_by_round = {}

    def run(
            self,
            client_index_for_this_round: List,  # e.g., 4 selected clients from 8 clients [1, 3, 4, 7]
            aggregation_func: Callable,
            local_weights_from_clients: List[Dict],
            acc_on_last_round: float,
            acc_on_aggregated_model: float,
            validation_func: Callable[[Dict, Any, Any], float],
            round_idx,
    ):
        logger.info(f"【MR-Shapley计算开始】轮次 {round_idx}，参与客户端: {client_index_for_this_round}")
        powerset = list(BaseContributionAssessor.generate_power_set(client_index_for_this_round))
        logger.info(f"幂集生成完成，子集数量: {len(powerset)}")
        
        util = {}
        # 历史迭代准确率
        s_0 = ()
        util[s_0] = acc_on_last_round
        logger.info(f"历史迭代准确率: {acc_on_last_round}")

        # 所有参与方，更新在当前迭代中的准确率
        s_all = powerset[-1]
        util[s_all] = acc_on_aggregated_model
        logger.info(f"全集准确率: {acc_on_aggregated_model}")

        logger.info(f"开始计算各子集效用值")
        for i, S in enumerate(powerset):
            if S in util:
                logger.info(f"子集 {i+1}/{len(powerset)}: {S} 已缓存，跳过计算")
                continue
            logger.info(f"计算子集 {i+1}/{len(powerset)}: {S} 的效用值")
            agg_model_with_subset_S = BaseContributionAssessor.get_aggregated_model_with_client_subset(
                aggregation_func, local_weights_from_clients, S
            )
            util[S] = validation_func(agg_model_with_subset_S)
            logger.info(f"子集 {S} 效用值计算完成: {util[S]}")

        logger.info(f"所有子集效用值计算完成，开始计算Shapley值")
        shapley_result = self.shapley_value(util, client_index_for_this_round)
        self.shapley_values_by_round[round_idx] = shapley_result
        logger.info(f"【MR-Shapley计算完成】轮次 {round_idx}，Shapley值: {shapley_result}")

    def shapley_value(self, utility, idxs):
        logger.info(f"【Shapley值计算开始】客户端列表: {idxs}")
        N = len(idxs)
        sv_dict = {id: 0 for id in idxs}
        logger.info(f"初始化Shapley值字典: {sv_dict}")
        
        valid_subsets = [S for S in utility.keys() if S != ()]
        logger.info(f"有效子集数量: {len(valid_subsets)}，开始计算各客户端的边际贡献")
        
        for i, S in enumerate(valid_subsets):
            logger.info(f"处理子集 {i+1}/{len(valid_subsets)}: {S}")
            for id in S:
                # 计算去掉当前客户端后的子集
                S_without_id = tuple(i for i in S if i != id)
                logger.info(f"客户端 {id} 在子集 {S} 中的边际贡献计算")
                logger.info(f"原效用值: {utility[S]}，去掉客户端后的效用值: {utility.get(S_without_id, 'N/A')}")
                
                marginal_contribution = max(utility[S] - utility[S_without_id], 0)
                weight = 1.0 / ((comb(N - 1, len(S) - 1)) * N)
                contribution = marginal_contribution * weight
                
                logger.info(f"边际贡献: {marginal_contribution}，权重: {weight:.6f}，加权贡献: {contribution:.6f}")
                sv_dict[id] += contribution
                logger.info(f"客户端 {id} 当前累计Shapley值: {sv_dict[id]:.6f}")

        logger.info(f"【Shapley值计算完成】最终结果: {sv_dict}")
        return sv_dict

    def get_final_contribution_assignment(self):
        """
        return: contribution_assignment
            (key is client_index; value is the client's relative contribution);
            the sum of values in the dictionary is equal to 1
        """
        logger.info(f"【最终贡献分配开始】MR-Shapley值汇总和归一化")
        contribution_assignment = {}        
        SV = {}  # dict: {id:SV,...}
        SV_summed = {}  # dict: {id: SV_summed_over_all_iter, ...}

        logger.info(f"开始汇总各轮次的Shapley值，总轮次数: {len(self.shapley_values_by_round)}")
        for round_idx, shapley_t in self.shapley_values_by_round.items():
            logger.info(f"处理轮次 {round_idx}，参与客户端数量: {len(shapley_t)}")
            for id in shapley_t:
                SV.setdefault(id, []).append(shapley_t[id])
                logger.info(f"客户端 {id} 在轮次 {round_idx} 的Shapley值: {shapley_t[id]}")
        
        logger.info(f"汇总结果 SV: {SV}")
        logger.info(f"开始计算各客户端的Shapley值总和，总客户端数: {self.client_num_in_total}")
        for id in range(self.client_num_in_total):
            SV_summed[id] = np.sum(SV.get(id, []))
            logger.info(f"客户端 {id} 的Shapley值总和: {SV_summed[id]}")

        total_sv = sum(SV_summed.values())
        logger.info(f"所有客户端Shapley值总和: {total_sv}")
        
        if total_sv == 0:
            logger.info(f"Shapley值总和为0，采用平均分配策略")
            # 均分贡献
            contribution_assignment = {
                id: 1.0 / self.client_num_in_total
                for id in range(self.client_num_in_total)
            }
            logger.info(f"平均分配结果: 每个客户端贡献值 = {1.0 / self.client_num_in_total:.6f}")
        else:
            logger.info(f"Shapley值总和不为0，采用比例分配策略")
            contribution_assignment = {id: sv / total_sv for id, sv in SV_summed.items()}
            for id, contrib in contribution_assignment.items():
                logger.info(f"客户端 {id} 的最终贡献比例: {contrib:.6f}")

        logger.info(f"【最终分配结果】MR-Shapley最终贡献分配: {contribution_assignment}")
        return contribution_assignment