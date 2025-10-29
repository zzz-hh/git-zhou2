from abc import abstractmethod, ABCMeta

import torch
from fediux.utils.logger_util import logger


class BaseModel(metaclass=ABCMeta):

    def __init__(self, **kwargs):
        self.roles = kwargs['roles']
        self.common_params = kwargs['common_params']
        self.role_params = kwargs['role_params']
        self.node_info = kwargs['node_info']
        self.task_info = kwargs['task_info']
        print("roles:", self.roles)
        print("common_params: ", self.common_params)
        print("role_params: ", self.role_params)
        print("node_info: ", self.node_info)
        print("task_info: ", self.task_info)

    @abstractmethod
    def run(self):
        pass

def choose_loss_fn(output_dim, task):
    task = task.lower()
    if task == 'classification':
        if output_dim == 1:
            return torch.nn.BCEWithLogitsLoss()
        else:
            return torch.nn.CrossEntropyLoss()
    if task == 'regression':
        return torch.nn.MSELoss()
    else:
        error_msg = f"Unsupported task: {task}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def choose_optimizer(model, optimizer, learning_rate, alpha):
    optimizer = optimizer.lower()
    if optimizer == 'adadelta':
        return torch.optim.Adadelta(model.parameters(),
                                    lr=learning_rate,
                                    weight_decay=alpha)
    elif optimizer == 'adagrad':
        return torch.optim.Adagrad(model.parameters(),
                                   lr=learning_rate,
                                   weight_decay=alpha)
    elif optimizer == 'adam':
        return torch.optim.Adam(model.parameters(),
                                lr=learning_rate,
                                weight_decay=alpha)
    elif optimizer == 'adamw':
        return torch.optim.AdamW(model.parameters(),
                                 lr=learning_rate,
                                 weight_decay=alpha)
    elif optimizer == 'adamax':
        return torch.optim.Adamax(model.parameters(),
                                  lr=learning_rate,
                                  weight_decay=alpha)
    elif optimizer == 'asgd':
        return torch.optim.ASGD(model.parameters(),
                                lr=learning_rate,
                                weight_decay=alpha)
    elif optimizer == 'nadam':
        return torch.optim.NAdam(model.parameters(),
                                 lr=learning_rate,
                                 weight_decay=alpha)
    elif optimizer == 'radam':
        return torch.optim.RAdam(model.parameters(),
                                 lr=learning_rate,
                                 weight_decay=alpha)
    elif optimizer == 'rmsprop':
        return torch.optim.RMSprop(model.parameters(),
                                   lr=learning_rate,
                                   weight_decay=alpha)
    elif optimizer == 'sgd':
        return torch.optim.SGD(model.parameters(),
                               lr=learning_rate,
                               weight_decay=alpha)
    else:
        error_msg = f"Unsupported optimizer: {optimizer}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def check_contribution_alg(contribution_alg):
    if contribution_alg is None:
        return None
    
    contribution_alg = contribution_alg.upper()
    valid_contribution_alg = {"GTG", "TMC", "MR", "LOO"}
    if contribution_alg not in valid_contribution_alg:
        error_msg = f"Unsupported contribution algorithm: {contribution_alg}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    return contribution_alg