# -*- coding: utf-8 -*-
from typing import List, Dict, Callable, Any
from .base_contribution_assessor import BaseContributionAssessor
from fediux.utils.logger_util import logger


class LeaveOneOut(BaseContributionAssessor):
    def __init__(self,client_num_in_total):
        super().__init__()
        self.client_num_in_total = client_num_in_total
        self.Contribution_records = {}

        # trunc paras
        self.round_trunc_threshold = 0.001
        self.similar_threshold = 0.01

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
        logger.info(f"【LOO计算开始】第{round_idx}轮留一法贡献评估，参与客户端: {client_index_for_this_round}")
        
        # 获取全集准确率（所有参与方）
        acc_all = acc_on_aggregated_model
        logger.info(f"【全集准确率】所有客户端聚合模型准确率: {acc_all:.4f}")

        # 初始化边际贡献记录
        marginal_contributions = self.Contribution_records.setdefault(round_idx, {})
        logger.info(f"【初始化记录】第{round_idx}轮边际贡献记录已初始化")
        
        # 负准确率截断：如果在这个迭代模型中没有足够的指标改进，每一方的贡献都是0
        # if abs(acc_all - acc_on_last_round) <= self.round_trunc_threshold:
        #     logger.info(f"【截断条件】准确率改进不足({abs(acc_all - acc_on_last_round):.4f} <= {self.round_trunc_threshold})，所有客户端贡献设为0")
        #     # 记录当前轮次所有客户端的零贡献
        #     for client_id in client_index_for_this_round:
        #         marginal_contributions.setdefault(client_id, 0.0)
        #     return

        # 遍历每个客户端计算留一贡献
        logger.info(f"【开始计算】开始对每个客户端进行留一法贡献计算")
        for client_id in client_index_for_this_round:
            logger.info(f"【计算客户端{client_id}】排除客户端{client_id}，计算剩余子集准确率")
            
            # 创建排除当前客户端的子集
            subset = [x for x in client_index_for_this_round if x != client_id]
            logger.info(f"【子集信息】排除客户端{client_id}后的子集: {subset}")
            
            # 获取排除后的模型准确率
            agg_model = BaseContributionAssessor.get_aggregated_model_with_client_subset(
                                        aggregation_func, local_weights_from_clients, subset
                                    )
            acc_subset = validation_func(agg_model)
            logger.info(f"【子集准确率】排除客户端{client_id}后的模型准确率: {acc_subset:.4f}")

            # 计算边际贡献（全集准确率 - 排除后的准确率）
            mc = max(acc_all - acc_subset, 0) # 负贡献归零
            marginal_contributions.setdefault(client_id, mc)
            logger.info(f"【边际贡献】客户端{client_id}的边际贡献: {mc:.4f} (全集{acc_all:.4f} - 子集{acc_subset:.4f})")
        
        logger.info(f"【LOO计算完成】第{round_idx}轮所有客户端边际贡献计算完成: {marginal_contributions}")

    def get_final_contribution_assignment(self):
        """
        通过累加所有轮次的留一贡献计算最终分配
        """
        logger.info("【最终贡献分配】开始计算所有轮次的累计贡献分配")
        
        # 初始化贡献字典
        total_contributions = {client_id: 0.0 for client_id in range(self.client_num_in_total)}
        logger.info("【贡献记录汇总】所有轮次的贡献记录: {}".format(self.Contribution_records))

        # 累加所有轮次的贡献值
        logger.info("【开始累加】开始累加各轮次贡献值")
        for round_idx, round_data in self.Contribution_records.items():
            logger.info(f"【处理轮次{round_idx}】该轮次贡献数据: {round_data}")
            for client_id, mc in round_data.items():
                total_contributions[client_id] += mc
                logger.info(f"【客户端{client_id}】累计贡献: {total_contributions[client_id]:.4f} (新增: {mc:.4f})")

        logger.info("【累计贡献结果】所有客户端累计贡献: {}".format(total_contributions))
        
        # 归一化处理
        total = sum(total_contributions.values())
        logger.info(f"【贡献总和】所有客户端贡献总和: {total:.4f}")
        
        if total == 0:
            logger.info(f"【特殊情况】总贡献为0，采用平均分配，每个客户端获得: {1.0/self.client_num_in_total:.4f}")
            return {k: 1.0/self.client_num_in_total for k in total_contributions}
        elif total < self.similar_threshold: # 正贡献不明显，判定为相似数据
            logger.info(f"【相似数据情况】总贡献过小({total:.4f} < {self.similar_threshold})，判定为相似数据，采用平均分配")
            return {k: 1.0/self.client_num_in_total for k in total_contributions}

        final_assignment = {k: v / total for k, v in total_contributions.items()}
        logger.info(f"【最终分配结果】归一化后的最终贡献分配: {final_assignment}")
        return final_assignment