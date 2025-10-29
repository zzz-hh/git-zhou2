from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file, \
    save_pickle_file, \
    load_pickle_file, \
    save_csv_file
from fediux.FL.utils.dataset import read_data
from fediux.utils.logger_util import logger
from fediux.FL.preprocessing import StandardScaler
from fediux.FL.metrics import regression_metrics, \
    classification_metrics

import pandas as pd
from sklearn.utils.validation import check_array
import torch
import torch.utils.data as data_utils
from torch.utils.data import DataLoader
from opacus import PrivacyEngine
from .base import create_model, \
    choose_loss_fn, \
    choose_optimizer


class Plaintext_Client:

    def __init__(self, x, y, method, task, device,
                 optimizer, learning_rate, alpha,
                 server_channel):
        self.task = task
        self.device = device
        self.server_channel = server_channel

        self.output_dim = None
        self.send_output_dim(y)
        out_chanels=1
        self.model = create_model(method,out_chanels, device)

        self.loss_fn = choose_loss_fn()
        self.optimizer = choose_optimizer(self.model,
                                          optimizer,
                                          learning_rate,
                                          alpha)

        self.input_shape = None
        self.send_input_shape(x)
        self.lazy_module_init()

        self.num_examples = x.shape[0]
        self.send_params()

    def recv_server_model(self):
        return self.server_channel.recv("server_model")

    def get_model(self):
        return self.model.state_dict()

    def set_model(self, model):
        self.model.load_state_dict(model)
        self.model.to(self.device)

    def send_output_dim(self, y):
        if self.task == 'regression' or self.task == 'AIGC':
            self.output_dim = 1
        if self.task == 'classification':
            # assume labels start from 0
            self.output_dim = y.max() + 1

            if self.output_dim == 2:
                # binary classification
                self.output_dim = 1

        self.server_channel.send('output_dim', self.output_dim)
        self.output_dim = self.server_channel.recv('output_dim')

    def send_input_shape(self, x):
        self.input_shape = x[0].shape
        self.server_channel.send('input_shape', self.input_shape)

        all_input_shapes_same = self.server_channel.recv("input_dim_same")
        if not all_input_shapes_same:
            error_msg = "Input shapes don't match for all clients"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def lazy_module_init(self):
        self.set_model(self.recv_server_model())

    def send_params(self):
        # send other params to compute aggregated metrics
        self.server_channel.send('num_examples', self.num_examples)

    def fit(self, dataloader):
        self.model.train()
        for x, y in dataloader:
            x, y = x.to(self.device), y.to(self.device)
            noise=torch.randn_like(x).to(self.device)
            
            # Compute prediction error
            pred = self.model(x,noise)
            loss = self.loss_fn(pred, noise)

            # Backpropagation
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

    def train(self):
        self.server_channel.send("client_model", self.get_model())
        self.set_model(self.recv_server_model())

    def send_metrics(self, dataloader):
        size = len(dataloader.dataset)
        self.model.eval()
        y_true, y_pred = torch.tensor([], dtype=torch.float64), \
            torch.tensor([], dtype=torch.float64)
        loss = 0

        with torch.no_grad():
            for x, y in dataloader:
                x, y = x.to(self.device), y.to(self.device)

                noise=torch.randn_like(x).to(self.device)
                pred = self.model(x,noise)

                y_true = torch.cat((y_true, noise.cpu()))
                y_pred = torch.cat((y_pred, pred.cpu()))

                if self.task == 'classification' or self.task=='AIGC':
                    loss += self.loss_fn(pred, noise).item() * len(x)

        if self.task == 'classification':
            loss /= size
            logger.info(f"loss: {loss}")
            self.server_channel.send("loss", loss)

            if self.output_dim == 1:
                y_score = torch.sigmoid(y_pred)
                metrics = classification_metrics(
                    y_true,
                    y_score,
                    multiclass=False,
                    prefix="train_",
                    metrics_name=["acc",
                                  "f1",
                                  "precision",
                                  "recall",
                                  "auc",
                                  "roc",
                                  "ks", ],
                )
            
            else:
                y_score = torch.softmax(y_pred, dim=1)
                metrics = classification_metrics(
                    y_true,
                    y_score,
                    multiclass=True,
                    prefix="train_",
                    metrics_name=["acc",
                                  "f1",
                                  "precision",
                                  "recall",
                                  "auc", ],
                )
            self.server_channel.send("acc", metrics["train_acc"])
        elif self.task == 'AIGC':
                loss /= size
                logger.info(f"loss: {loss}")
                self.server_channel.send("loss", loss)

                metrics ={"loss":loss}
        elif self.task == 'regression':
            metrics = regression_metrics(
                y_true,
                y_pred,
                prefix="train_",
                metrics_name=["ev",
                              "maxe",
                              "mae",
                              "mse",
                              "rmse",
                              "medae",
                              "r2", ],
            )
            self.server_channel.send("mse", metrics["train_mse"])
            self.server_channel.send("mae", metrics["train_mae"])

        return metrics

    def print_metrics(self, dataloader):
        size = len(dataloader.dataset)
        self.model.eval()
        y_true, y_pred = torch.tensor([]), torch.tensor([])
        loss = 0

        with torch.no_grad():
            for x, y in dataloader:
                x, y = x.to(self.device), y.to(self.device)

                noise=torch.randn_like(x).to(self.device)
                pred = self.model(x,noise)

                
              

                y_true = torch.cat((y_true, noise.cpu()))
                y_pred = torch.cat((y_pred, pred.cpu()))

                if self.task == 'classification' or self.task == 'AIGC':
                    loss += self.loss_fn(pred, noise).item() * len(x)

        if self.task == 'classification' :
            loss /= size
            logger.info(f"loss: {loss}")
            self.server_channel.send("loss", loss)

            if self.output_dim == 1:
                y_score = torch.sigmoid(y_pred)
                metrics = classification_metrics(
                    y_true,
                    y_score,
                    multiclass=False,
                    metrics_name=["acc", ],
                )
            else:
                y_score = torch.softmax(y_pred, dim=1)
                metrics = classification_metrics(
                    y_true,
                    y_score,
                    multiclass=True,
                    metrics_name=["acc", ],
                )
            self.server_channel.send("acc", metrics["acc"])

        elif self.task == 'regression':
            metrics = regression_metrics(
                y_true,
                y_pred,
                metrics_name=["mae",
                              "mse", ],
            )
            self.server_channel.send("mse", metrics["mse"])
            self.server_channel.send("mae", metrics["mae"])
        elif self.task == 'AIGC':
            loss /= size
            logger.info(f"loss: {loss}")
            self.server_channel.send("loss", loss)
            metrics ={"loss":loss}

class DPSGD_Client(Plaintext_Client):

    def __init__(self, data_tenor, method, task, device,
                 optimizer, learning_rate, alpha,
                 noise_multiplier, max_grad_norm,
                 server_channel):
        super().__init__(data_tenor, method, task, device,
                         optimizer, learning_rate, alpha,
                         server_channel)
        self.noise_multiplier = noise_multiplier
        self.max_grad_norm = max_grad_norm
        self.privacy_engine = PrivacyEngine(accountant='rdp')
        self.train_dataloader = None

    def lazy_module_init(self):
        # opacus lib needs to init lazy module first
        input_shape = list(self.input_shape)
        # set batch size equals to 1 to initialize lazy module
        input_shape.insert(0, 1)

        ones_tensor = torch.ones(input_shape).to(self.device)

        noise = torch.randn_like(ones_tensor).to(self.device)

        self.model.forward(ones_tensor, noise)

        super().lazy_module_init()

    def enable_DP_training(self, train_dataloader):
        self.model, \
            self.optimizer, \
            self.train_dataloader = self.privacy_engine.make_private(
            module=self.model,
            optimizer=self.optimizer,
            data_loader=train_dataloader,
            noise_multiplier=self.noise_multiplier,
            max_grad_norm=self.max_grad_norm,
        )

    def get_model(self):
        # remove '_module.' prefix added by opacus make_private
        return self.model._module.state_dict()

    def compute_epsilon(self, delta):
        if delta >= 1. / self.num_examples:
            logger.error(f"delta {delta} should be set less than 1 / {self.num_train_examples}")
        return self.privacy_engine.get_epsilon(delta)