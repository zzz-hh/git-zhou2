# -*- coding: utf-8 -*-
from typing import List, Dict, Callable, Any

import numpy as np
import math
from .base_contribution_assessor import BaseContributionAssessor
from fediux.utils.logger_util import logger


class TMCShapleyValue(BaseContributionAssessor):
    def __init__(self,client_num_in_total):
        super().__init__()
        self.client_num_in_total = client_num_in_total

        # trunc paras
        self.eps = 0.001
        self.round_trunc_threshold = 0.01

        self.Contribution_records = []

        # converge paras
        self.CONVERGE_MIN_K = 3 * 10
        self.last_k = 10
        self.CONVERGE_CRITERIA = 0.05

        # key is the round_index;
        # value is the dictionary contribution (key - client_index; value - relative contribution
        self.shapley_values_by_round = dict()

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
        logger.info(f"【TMC-Shapley计算开始】轮次 {round_idx}，参与客户端: {client_index_for_this_round}")
        N = len(client_index_for_this_round)
        self.max_permutations = math.factorial(N) 
        self.Contribution_records = []
        logger.info(f"基础信息: 客户端数量={N}，最大排列数={self.max_permutations}")

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

        k = 0
        logger.info(f"开始迭代计算，收敛条件: eps={self.eps}, 截断阈值={self.round_trunc_threshold}")
        while self._is_not_converged(k):
            logger.info(f"【迭代轮次 {k}】开始计算")
            for pi in client_index_for_this_round:
                k += 1
                logger.info(f"处理客户端 {pi}，当前迭代次数 k={k}")
                v = [0 for i in range(N + 1)]
                v[0] = util[s_0]
                marginal_contribution_k = [0 for i in range(N)]

                # 将当前客户端 pi 与其余客户端的随机排列组合在一起，生成一个新的索引列表 idxs_k
                np.random.seed(round_idx * 10000 + k*100 + pi)  # 新增种子设置，确保不同轮次、不同k值不同起始客户端，种子不同
                idxs_k = np.concatenate(
                    (np.array([pi]), np.random.permutation([p for p in client_index_for_this_round if p != pi]))
                )
                logger.info(f"生成随机排列: {idxs_k}")
                
                for j in range(1, N + 1):
                    # key = C subset
                    C = idxs_k[:j] # 对于每一个 j（从1到N），生成当前排列 idxs_k 的前 j 个元素组成的子集 C
                    C = tuple(np.sort(C, kind="mergesort")) # 将 C 转换为元组并排序，确保唯一性和可哈希性
                    logger.info(f"处理子集 {j}: {C}")

                    # truncation
                    if abs(util[s_all] - v[j - 1]) >= self.eps: # 检查当前子集效用值v[j - 1]是否接近全集效用值util[s_all]
                        logger.info(f"子集 {C} 需要计算效用值，当前差异: {abs(util[s_all] - v[j - 1]):.6f}")
                        if util.get(C) != None:
                            v[j] = util[C]
                            logger.info(f"子集 {C} 效用值已缓存: {v[j]}")
                        else:
                            logger.info(f"计算子集 {C} 的聚合模型效用值")
                            agg_model_C = BaseContributionAssessor.get_aggregated_model_with_client_subset(
                                aggregation_func, local_weights_from_clients, C
                            )
                            # 分发模型，计算指标
                            v[j] = validation_func(agg_model_C)
                            logger.info(f"子集 {C} 效用值计算完成: {v[j]}")
                    else:
                        v[j] = v[j - 1]
                        logger.info(f"子集 {C} 采用截断处理，效用值沿用前一个: {v[j]}")

                    # record calculated V(C)
                    util[C] = v[j]
                    # update SV
                    mc = max(v[j] - v[j - 1], 0)
                    logger.info(f"子集 {C} 边际贡献: {mc}")
                    # 判断客户端索引是否从0开始
                    if min(client_index_for_this_round) == 0:
                        # 客户端索引从0开始，直接使用idxs_k[j - 1]作为索引
                        marginal_contribution_k[idxs_k[j - 1]] = mc
                    else:
                        marginal_contribution_k[idxs_k[j - 1] - 1] = mc
                logger.info(f"util={util}")
                logger.info(f"k={k}, marginal_contribution_k={marginal_contribution_k}")
                self.Contribution_records.append(marginal_contribution_k)
                logger.info(f"记录客户端 {pi} 的边际贡献向量，当前记录总数: {len(self.Contribution_records)}")
            if len(util) == len(powerset) and k >= self.max_permutations:
                logger.info(f"所有子集效用值已计算完成，且达到最大排列数，退出迭代")
                break
        
        # shapley value 计算
        logger.info(f"开始计算Shapley值，贡献记录数量: {len(self.Contribution_records)}")
        shapley_values = (
            np.cumsum(self.Contribution_records, 0)
            / np.reshape(np.arange(1, len(self.Contribution_records) + 1), (-1, 1))
        )[-1:].tolist()[0]
        logger.info(f"Shapley值计算完成: {shapley_values}")

        for index, client_ind in enumerate(client_index_for_this_round):
            (self.shapley_values_by_round.setdefault(round_idx, {})
                .setdefault(client_ind, [])
                .append(shapley_values[index]))
            logger.info(f"客户端 {client_ind} 的Shapley值: {shapley_values[index]}")
        
        logger.info(f"【TMC-Shapley计算完成】轮次 {round_idx}，所有客户端Shapley值已记录")

    def _is_not_converged(self, k):
        logger.info(f"【收敛判断分析】当前迭代次数 k={k}，最小迭代次数 CONVERGE_MIN_K={self.CONVERGE_MIN_K}")
        if k <= self.CONVERGE_MIN_K:
            logger.info(f"未达到最小迭代次数，继续迭代")
            return True
        all_vals = (
            np.cumsum(self.Contribution_records, 0)
            / np.reshape(np.arange(1, len(self.Contribution_records) + 1), (-1, 1))
        )[-self.last_k :]
        errors = np.mean(np.abs(all_vals[-self.last_k :] - all_vals[-1:]) / (np.abs(all_vals[-1:]) + 1e-12), -1)
        max_error = np.max(errors)
        logger.info(f"收敛分析: 最近{self.last_k}次迭代的误差分析，最大误差={max_error:.6f}，收敛阈值={self.CONVERGE_CRITERIA}")
        if max_error > self.CONVERGE_CRITERIA:
            logger.info(f"最大误差超过收敛阈值，继续迭代")
            return True
        logger.info(f"算法已收敛，停止迭代")
        return False

    def get_final_contribution_assignment(self):
        """
        return: 贡献分配字典，键是客户端索引，值是客户端的相对贡献。
            所有客户端的相对贡献之和为1。
        """
        logger.info(f"【最终贡献分配开始】Shapley值汇总和归一化")
        contribution_assignment = dict()
        SV = {}  # dict: {id:SV,...}
        SV_summed = {}  # dict: {id: SV_summed_over_all_iter, ...}

        logger.info(f"开始汇总各轮次的Shapley值，总轮次数: {len(self.shapley_values_by_round)}")
        for round_idx, shapley_t in self.shapley_values_by_round.items():
            logger.info(f"处理轮次 {round_idx}，参与客户端数量: {len(shapley_t)}")
            for id in shapley_t:
                SV.setdefault(id, []).append(shapley_t[id])
                logger.info(f"客户端 {id} 在轮次 {round_idx} 的Shapley值: {shapley_t[id]}")

        logger.info(f"开始计算各客户端的Shapley值总和，总客户端数: {self.client_num_in_total}")
        for id in range(self.client_num_in_total):
            SV_summed[id] = np.sum(SV[id])
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

        logger.info(f"【最终分配结果】TMC-Shapley最终贡献分配: {contribution_assignment}")
        return contribution_assignment