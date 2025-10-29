# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Callable

from fediux.utils.logger_util import logger
from .gtg_shapley_value import GTGShapleyValue
from .tmc_shapley_value import TMCShapleyValue
from .leave_one_out import LeaveOneOut
from .mr_shapley_value import MRShapleyValue


class ContributionAssessorManager:
    def __init__(self, contribution_alg, client_num_in_total):
        self.contribution_alg = contribution_alg
        self.client_num_in_total = client_num_in_total
        self.assessor = self._build_assessor()

    def _build_assessor(self):
        if not self.contribution_alg:
            logger.info("contribution_alg is not set, assessor is None")
            return None
        
        if self.contribution_alg == "LOO":
            assessor = LeaveOneOut(self.client_num_in_total)
        elif self.contribution_alg == "GTG":
            assessor = GTGShapleyValue(self.client_num_in_total)
        elif self.contribution_alg == "TMC":
            assessor = TMCShapleyValue(self.client_num_in_total)
        elif self.contribution_alg == "MR":
            assessor = MRShapleyValue(self.client_num_in_total)
        else:
            logger.info("no such contribution_alg, assessor is None")
            assessor = None
        return assessor

    def get_assessor(self):
        return self.assessor

    def run(
        self,
        client_index_for_this_round,
        aggregation_func: Callable,
        local_weights_from_clients: List[Dict],
        acc_on_last_round: float,
        acc_on_aggregated_model: float,
        validation_func: Callable[[Dict, Any, Any], float],
        round_idx,
    ):
        if self.assessor is None:
            return

        self.assessor.run(
            client_index_for_this_round,
            aggregation_func,
            local_weights_from_clients,
            acc_on_last_round,
            acc_on_aggregated_model,
            validation_func,
            round_idx,
        )

    def get_final_contribution_assignment(self):
        if self.assessor is None:
            return None
        return self.assessor.get_final_contribution_assignment()
