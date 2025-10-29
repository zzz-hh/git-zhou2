# -*- coding: utf-8 -*-
from typing import List, Dict, Callable, Any

import numpy as np
import math
from .base_contribution_assessor import BaseContributionAssessor
from fediux.utils.logger_util import logger


class GTGShapleyValue(BaseContributionAssessor):
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
        logger.info(f"【GTG-Shapley计算开始】第{round_idx}轮GTG-Shapley值计算，参与客户端: {client_index_for_this_round}")
        
        N = len(client_index_for_this_round)
        self.max_permutations = math.factorial(N) 
        self.Contribution_records = []

        logger.info(f"【基础信息】客户端数量: {N}，最大排列数: {self.max_permutations}")

        powerset = list(BaseContributionAssessor.generate_power_set(client_index_for_this_round))
        logger.info(f"【幂集生成】生成幂集，包含 {len(powerset)} 个子集")

        util = {}

        # 历史迭代准确率
        s_0 = ()
        util[s_0] = acc_on_last_round
        logger.info(f"【历史准确率】空集准确率 (历史迭代): {acc_on_last_round:.4f}")

        # 所有参与方，更新在当前迭代中的准确率
        s_all = powerset[-1]
        util[s_all] = acc_on_aggregated_model
        logger.info(f"【全集准确率】所有客户端聚合准确率: {acc_on_aggregated_model:.4f}")

        # 负准确率截断:
        # 如果在这个迭代模型中没有足够的指标改进，每一方的贡献都是0
        accuracy_improvement = abs(util[s_all] - util[s_0])
        logger.info(f"【准确率改进】准确率改进幅度: {accuracy_improvement:.4f} (阈值: {self.round_trunc_threshold})")
        
        if accuracy_improvement <= self.round_trunc_threshold:
            logger.info(f"【截断处理】准确率改进不足，所有客户端Shapley值设为0")
            # 记录当前轮次所有客户端的零贡献
            round_dict = self.shapley_values_by_round.get(round_idx, {})
            for client_ind in client_index_for_this_round:
                round_dict.setdefault(client_ind, []).append(0.0)
            self.shapley_values_by_round[round_idx] = round_dict
            return 

        logger.info(f"【开始迭代】开始Shapley值计算迭代过程")
        k = 0
        while self._is_not_converged(k):
            logger.info(f"【第{k+1}次迭代】当前迭代次数: {k+1}")
            for pi in client_index_for_this_round:
                k += 1
                logger.info(f"【处理客户端{pi}】作为第{k}个排列的起始客户端")
                
                v = [0 for i in range(N + 1)]
                v[0] = util[s_0]
                marginal_contribution_k = [0 for i in range(N)]

                # 将当前客户端 pi 与其余客户端的随机排列组合在一起，生成一个新的索引列表 idxs_k
                np.random.seed(round_idx * 10000 + k*100 + pi)  # 新增种子设置，确保不同轮次、不同k值不同起始客户端，种子不同
                idxs_k = np.concatenate(
                    (np.array([pi]), np.random.permutation([p for p in client_index_for_this_round if p != pi]))
                )
                logger.info(f"【生成长度为{N}的排列】起始客户端{pi}，排列: {idxs_k}")
                
                for j in range(1, N + 1):
                    # key = C subset
                    C = idxs_k[:j] # 对于每一个 j（从1到N），生成当前排列 idxs_k 的前 j 个元素组成的子集 C
                    C = tuple(np.sort(C, kind="mergesort")) # 将 C 转换为元组并排序，确保唯一性和可哈希性
                    logger.info(f"【子集C{j}】前{j}个元素组成的子集: {C}")

                    # truncation
                    if abs(util[s_all] - v[j - 1]) >= self.eps: # 检查当前子集效用值v[j - 1]是否接近全集效用值util[s_all]
                        logger.info(f"【需要计算】子集{C}效用值需要重新计算 (差异: {abs(util[s_all] - v[j - 1]):.4f} >= {self.eps})")
                        if util.get(C) != None:
                            v[j] = util[C]
                            logger.info(f"【缓存命中】子集{C}效用值从缓存获取: {v[j]:.4f}")
                        else:
                            logger.info(f"【模型聚合】开始聚合子集{C}的模型")
                            agg_model_C = BaseContributionAssessor.get_aggregated_model_with_client_subset(
                                aggregation_func, local_weights_from_clients, C
                            )
                            # 分发模型，计算指标
                            v[j] = validation_func(agg_model_C)
                            logger.info(f"【效用计算】子集{C}效用值计算完成: {v[j]:.4f}")
                    else:
                        v[j] = v[j - 1]
                        logger.info(f"【截断优化】子集{C}效用值直接使用前一个值: {v[j]:.4f} (差异过小)")

                    # record calculated V(C)
                    util[C] = v[j]
                    # update SV
                    mc = max(v[j] - v[j - 1], 0)
                    logger.info(f"【边际贡献】位置{j}的边际贡献: {mc:.4f} (当前{v[j]:.4f} - 前一个{v[j-1]:.4f})")
                    
                    # 判断客户端索引是否从0开始
                    if min(client_index_for_this_round) == 0:
                        # 客户端索引从0开始，直接使用idxs_k[j - 1]作为索引
                        marginal_contribution_k[idxs_k[j - 1]] = mc
                        logger.info(f"【贡献记录】客户端{idxs_k[j-1]}的边际贡献: {mc:.4f}")
                    else:
                        client_idx = idxs_k[j - 1] - 1
                        marginal_contribution_k[client_idx] = mc
                        logger.info(f"【贡献记录】客户端{idxs_k[j-1]}(索引{client_idx})的边际贡献: {mc:.4f}")

                self.Contribution_records.append(marginal_contribution_k)
                logger.info(f"【单次排列完成】第{k}次排列的边际贡献记录: {marginal_contribution_k}")
                
            if len(util) == len(powerset) and k >= self.max_permutations:
                logger.info(f"【完全计算】所有子集效用值已计算完成，总计算次数: {len(util)}")
                break

        # shapley value 计算
        logger.info(f"【Shapley值计算】开始计算最终Shapley值，贡献记录数: {len(self.Contribution_records)}")
        shapley_values = (
            np.cumsum(self.Contribution_records, 0)
            / np.reshape(np.arange(1, len(self.Contribution_records) + 1), (-1, 1))
        )[-1:].tolist()[0]
        logger.info(f"【Shapley值结果】计算得到的Shapley值: {shapley_values}")

        for index, client_ind in enumerate(client_index_for_this_round):
            shapley_val = shapley_values[index]
            (self.shapley_values_by_round.setdefault(round_idx, {})
                .setdefault(client_ind, [])
                .append(shapley_val))
            logger.info(f"【客户端{client_ind}】Shapley值: {shapley_val:.4f}")
            
        logger.info(f"【GTG-Shapley计算完成】第{round_idx}轮GTG-Shapley值计算完成")

    def _is_not_converged(self, k):
        logger.info(f"【收敛判断】当前迭代次数: {k}，最小迭代次数: {self.CONVERGE_MIN_K}")
        
        if k <= self.CONVERGE_MIN_K:
            logger.info(f"【未收敛】迭代次数不足，继续迭代")
            return True
            
        logger.info(f"【收敛分析】开始分析最近{self.last_k}次迭代的收敛情况")
        all_vals = (
            np.cumsum(self.Contribution_records, 0)
            / np.reshape(np.arange(1, len(self.Contribution_records) + 1), (-1, 1))
        )[-self.last_k :]
        
        errors = np.mean(np.abs(all_vals[-self.last_k :] - all_vals[-1:]) / (np.abs(all_vals[-1:]) + 1e-12), -1)
        max_error = np.max(errors)
        
        logger.info(f"【误差分析】最大误差: {max_error:.6f}，收敛阈值: {self.CONVERGE_CRITERIA}")
        
        if max_error > self.CONVERGE_CRITERIA:
            logger.info(f"【未收敛】误差过大，继续迭代")
            return True
        
        logger.info(f"【已收敛】误差在允许范围内，停止迭代")
        return False

    def get_final_contribution_assignment(self):
        """
        return: 贡献分配字典，键是客户端索引，值是客户端的相对贡献。
            所有客户端的相对贡献之和为1。
        """
        logger.info("【最终贡献分配】开始计算GTG-Shapley最终贡献分配")
        
        contribution_assignment = dict()
        SV = {}  # dict: {id:SV,...}
        SV_summed = {}  # dict: {id: SV_summed_over_all_iter, ...}

        logger.info(f"【Shapley值汇总】开始汇总所有轮次的Shapley值")
        for round_idx, shapley_t in self.shapley_values_by_round.items():
            logger.info(f"【处理轮次{round_idx}】该轮次Shapley值数据: {shapley_t}")
            for id in shapley_t:
                SV.setdefault(id, []).append(shapley_t[id])
                logger.info(f"【客户端{id}】该轮次Shapley值: {shapley_t[id]}")

        logger.info(f"【客户端Shapley值汇总】各客户端所有轮次Shapley值: {SV}")
        
        logger.info(f"【开始求和】计算每个客户端的Shapley值总和")
        for id in range(self.client_num_in_total):
            if id in SV:
                SV_summed[id] = np.sum(SV[id])
                logger.info(f"【客户端{id}】Shapley值总和: {SV_summed[id]:.4f} (共{len(SV[id])}个值)")
            else:
                SV_summed[id] = 0.0
                logger.info(f"【客户端{id}】无Shapley值记录，设为0.0")

        logger.info(f"【Shapley值总和】所有客户端Shapley值总和: {SV_summed}")
        
        total_sv = sum(SV_summed.values())
        logger.info(f"【总和计算】所有客户端Shapley值总和: {total_sv:.4f}")
        
        if total_sv == 0:
            logger.info(f"【特殊情况】总Shapley值为0，采用平均分配")
            # 均分贡献
            contribution_assignment = {
                id: 1.0 / self.client_num_in_total
                for id in range(self.client_num_in_total)
            }
            logger.info(f"【平均分配】每个客户端获得: {1.0/self.client_num_in_total:.4f}")
        else:
            logger.info(f"【按比例分配】按Shapley值比例进行分配")
            contribution_assignment = {id: sv / total_sv for id, sv in SV_summed.items()}
            for id, contribution in contribution_assignment.items():
                logger.info(f"【客户端{id}】最终贡献比例: {contribution:.4f} (Shapley值: {SV_summed[id]:.4f})")

        logger.info(f"【最终分配结果】GTG-Shapley最终贡献分配: {contribution_assignment}")
        return contribution_assignment