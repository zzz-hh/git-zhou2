# encoding:utf-8
from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.utils.base import BaseModel, check_contribution_alg, choose_loss_fn, choose_optimizer
from fediux.FL.utils.file import save_json_file,\
                                   save_pickle_file,\
                                   load_pickle_file,\
                                   save_csv_file
from fediux.FL.utils.dataset import read_data,ChineseTextDataset
from fediux.utils.logger_util import logger
from fediux.FL.metrics import classification_metrics
import pandas as pd
import torch
from torch.utils.data import DataLoader
from opacus import PrivacyEngine
from .base import create_model
from sklearn.model_selection import train_test_split


class FasttextClient(BaseModel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        process = self.common_params['process']
        role_name = self.role_params.get('self_name', 'unknown')
        logger.info(f"Running Horizontal FastText algorithm, role={role_name}, process={process}")
        logger.info(f"process: {process}")
        if process == 'train':
            self.train()
        elif process == 'predict':
            self.predict()
        else:
            error_msg = f"Unsupported process: {process}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def train(self):
        # setup communication channels
        remote_party = self.roles[self.role_params['others_role']]
        server_channel = GrpcClient(local_party=self.role_params['self_name'],
                                    remote_party=remote_party,
                                    node_info=self.node_info,
                                    task_info=self.task_info)

        # 加载数据
        selected_column = self.common_params.get('selected_column')
        if selected_column is None:
            selected_column = self.role_params.get('selected_column')
        id = self.common_params['id']
        df = read_data(data_info=self.role_params['data'],
                      selected_column=selected_column,
                      droped_column=id)
        label = self.common_params['label']
        df.dropna(inplace=True)
        x = df['text'].tolist()
        y = df[label].tolist()

        # client 初始化
        # Get cpu or gpu device for training.
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using {device} device")

        contribution_alg = self.common_params.get('contribution_alg', None)
        contribution_alg = check_contribution_alg(contribution_alg)
        method = self.common_params['method']
        if method == 'Plaintext':
            client = Plaintext_Fasttext_Client(x, y,
                                      method,
                                      device,
                                      self.common_params,
                                      server_channel,
                                      contribution_alg)
        elif method == 'DPSGD':
            client = DPSGD_Client(x, y,
                                  method,
                                  device,
                                  self.common_params['optimizer'],
                                  self.common_params['learning_rate'],
                                  self.common_params['alpha'],
                                  self.common_params['noise_multiplier'],
                                  self.common_params['l2_norm_clip'],
                                  server_channel,
                                  contribution_alg)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        num_examples = client.num_examples 
        batch_size = min(num_examples, self.common_params['batch_size'])
        train_dataloader = DataLoader(client.train_set,
                                      batch_size=batch_size,
                                      shuffle=False)
        test_dataloader = DataLoader(client.test_set,
                                      batch_size=batch_size,
                                      shuffle=False)

        if method == 'DPSGD':
            client.enable_DP_training(train_dataloader)

        # client training
        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i+1} / {global_epoch} --------")
            
            local_epoch = self.common_params['local_epoch']
            for j in range(local_epoch):
                logger.info(f"-------- local epoch {j+1} / {local_epoch} --------")
                if method == 'DPSGD':
                    # DP data loader: Poisson sampling 
                    client.fit(client.train_dataloader)
                else:
                    client.fit(train_dataloader)

            client.train(train_dataloader)

            # print metrics
            if self.common_params['print_metrics']:
                client.print_metrics(train_dataloader)
        logger.info("-------- finish training --------")

        # send final epsilon when using DPSGD
        if method == 'DPSGD':
            delta = self.common_params['delta']
            eps = client.compute_epsilon(delta)
            server_channel.send("eps", eps)
            logger.info(f"For delta={delta}, the current epsilon is {eps}")
        
        # send final metrics
        trainMetrics = client.send_metrics(test_dataloader)
        if client.contribution_alg:
            contribution = server_channel.recv("contribution")
            logger.info(f"contribution: {contribution}")
            trainMetrics["contribution"] = contribution
        save_json_file(trainMetrics, self.role_params['metric_path'])

        # save model for prediction
        modelFile = {
            "output_dim": client.output_dim,
            "selected_column": selected_column,
            "id": id,
            "label": label,
            "vocab": client.train_set.vocab,
            "model": client.model
        }
        save_pickle_file(modelFile, self.role_params['model_path'])

    def predict(self):
        # Get cpu or gpu device for training.
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using {device} device")

        # load model for prediction
        modelFile = load_pickle_file(self.role_params['model_path'])

        # load dataset
        selected_column = modelFile['selected_column']
        df = read_data(data_info=self.role_params['data'],
                      selected_column=selected_column,
                      droped_column=id)
        df.dropna(inplace=True)
        x = df['text'].tolist()
        y = [0] * len(x)  # 用0填充

        data_set = ChineseTextDataset(x, y,modelFile['output_dim'])
        data_set.load_vocab(modelFile['vocab'])

        dataloader = DataLoader(data_set, batch_size=len(x))

        # test data prediction
        model = modelFile['model'].to(device)
        model.eval()
        with torch.no_grad():
            for x, _ in dataloader:
                x = x.to(device)
                pred = model(x)

                if modelFile['output_dim'] == 1:
                    pred_prob = torch.sigmoid(pred)
                    pred_y = (pred_prob > 0.5).int()
                else:
                    pred_prob = torch.softmax(pred, dim=1)
                    pred_y = pred_prob.argmax(1)

        if modelFile['output_dim'] == 1:
            pred_prob = pred_prob.reshape(-1)
        result = pd.DataFrame({
            'pred_prob': pred_prob.tolist(),
            'pred_y': pred_y.reshape(-1).tolist()
        })

        data_result = pd.concat([df, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])


class Plaintext_Fasttext_Client:

    def __init__(self, x, y, method, device,common_params,
                 server_channel, contribution_alg):
        self.contribution_alg = contribution_alg
        self.task = "classification"
        optimizer = common_params["optimizer"]
        learning_rate = common_params["learning_rate"]
        alpha = common_params["alpha"]
        vocab_size =  common_params["vocab_size"]
        embedding_dim =  common_params["embedding_dim"]
        # test_size =  common_params["test_size"]
        test_size =  common_params.get('test_size', 0.2)

        self.device = device
        self.server_channel = server_channel

        self.output_dim = None
        self.send_output_dim(y)

        self.model = create_model(method, vocab_size, embedding_dim, self.output_dim, device)
        self.loss_fn = choose_loss_fn(self.output_dim, self.task)
        self.optimizer = choose_optimizer(self.model, optimizer, learning_rate, alpha)

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_size, shuffle=True, random_state=42)
        self.train_set = ChineseTextDataset(x_train, y_train,self.output_dim)
        self.test_set = ChineseTextDataset(x_test, y_test,self.output_dim)

        self.send_vocab()
        self.lazy_module_init()

        self.num_examples = len(x)
        self.send_params()

    def recv_server_model(self):
        return self.server_channel.recv("server_model")

    def get_model(self):
        return self.model.state_dict()

    def set_model(self, model):
        self.model.load_state_dict(model)
        self.model.to(self.device)

    def send_output_dim(self, y):
        # 假设 labels 从 0 开始
        self.output_dim = max(y) + 1

        if self.output_dim == 2:
            # 二分类
            self.output_dim = 1

        self.server_channel.send('output_dim', self.output_dim)
        self.output_dim = self.server_channel.recv('output_dim')


    def send_vocab(self):
        # 发送统计结果
        try:
            counter = self.train_set.word_count()
        except Exception as e:
            logger.info(f"Error occurred while setting output dimension: {str(e)}")
            raise e
        self.server_channel.send('input_token_count', counter)
        # 接收词典
        vocab_list = self.server_channel.recv("vocab_list")
        self.train_set.set_vocab(vocab_list)
        self.test_set.set_vocab(vocab_list)

    def lazy_module_init(self):
        self.set_model(self.recv_server_model())

    def send_params(self):
        # send other params to compute aggregated metrics
        self.server_channel.send('num_examples', self.num_examples)

    def fit(self, dataloader):
        self.model.train()
        for x, y in dataloader:
            x, y = x.to(self.device), y.to(self.device)

            # Compute prediction error
            pred = self.model(x)
            loss = self.loss_fn(pred, y)

            # Backpropagation
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

    def train(self,dataloader):
        self.server_channel.send("client_model", self.get_model())
        # 确认接收次数
        if self.contribution_alg:
            self.valid(dataloader)
            mid_valid_data = self.server_channel.recv("valid_data")
            status = mid_valid_data['status']
            while status == 0:
                # 更新模型并评估
                self.set_model(mid_valid_data['valid_model'])
                self.valid(dataloader)

                mid_valid_data = self.server_channel.recv("valid_data")
                status = mid_valid_data['status']

        # 更新模型
        self.set_model(self.recv_server_model())

    def valid(self, dataloader):
        self.model.eval()
        y_true, y_pred = torch.tensor([]), torch.tensor([])

        with torch.no_grad():
            for x, y in dataloader:
                x, y = x.to(self.device), y.to(self.device)
                pred = self.model(x)

                y_true = torch.cat((y_true, y.cpu()))
                y_pred = torch.cat((y_pred, pred.cpu()))

        if self.output_dim == 1:
            y_score = torch.sigmoid(y_pred)
            metrics = classification_metrics(
                y_true,
                y_score,
                multiclass=False,
                metrics_name=["acc",],
            )
        else:
            y_score = torch.softmax(y_pred, dim=1)
            metrics = classification_metrics(
                y_true,
                y_score,
                multiclass=True,
                metrics_name=["acc",],
            )
        self.server_channel.send("acc", metrics["acc"])

    def send_metrics(self, dataloader):
        size = len(dataloader.dataset)
        self.model.eval()
        y_true, y_pred = torch.tensor([], dtype=torch.float64),\
                         torch.tensor([], dtype=torch.float64)
        loss = 0

        with torch.no_grad():
            for x, y in dataloader:
                x, y = x.to(self.device), y.to(self.device)
                pred = self.model(x)

                y_true = torch.cat((y_true, y.cpu()))
                y_pred = torch.cat((y_pred, pred.cpu()))

                loss += self.loss_fn(pred, y).item() * len(x)

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
                                "ks",
                                "confusion_matrix",
                                "bimodal",],
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
                                "auc",
                                "confusion_matrix",],
            )
        self.server_channel.send("acc", metrics["train_acc"])

        return metrics

    def print_metrics(self, dataloader):
        size = len(dataloader.dataset)
        self.model.eval()
        y_true, y_pred = torch.tensor([]), torch.tensor([])
        loss = 0

        with torch.no_grad():
            for x, y in dataloader:
                x, y = x.to(self.device), y.to(self.device)
                pred = self.model(x)

                y_true = torch.cat((y_true, y.cpu()))
                y_pred = torch.cat((y_pred, pred.cpu()))

                loss += self.loss_fn(pred, y).item() * len(x)

        loss /= size
        logger.info(f"loss: {loss}")
        self.server_channel.send("loss", loss)

        if self.output_dim == 1:
            y_score = torch.sigmoid(y_pred)
            metrics = classification_metrics(
                y_true,
                y_score,
                multiclass=False,
                metrics_name=["acc",],
            )
        else:
            y_score = torch.softmax(y_pred, dim=1)
            metrics = classification_metrics(
                y_true,
                y_score,
                multiclass=True,
                metrics_name=["acc",],
            )
        self.server_channel.send("acc", metrics["acc"])


class DPSGD_Client(Plaintext_Fasttext_Client):

    def __init__(self, x, y, method, device,
                 optimizer, learning_rate, alpha,
                 noise_multiplier, max_grad_norm,
                 server_channel, contribution_alg):
        super().__init__(x, y, method, device,
                         optimizer, learning_rate, alpha,
                         server_channel, contribution_alg)
        self.noise_multiplier = noise_multiplier
        self.max_grad_norm = max_grad_norm
        self.privacy_engine = PrivacyEngine(accountant='rdp')
        self.train_dataloader = None

    def lazy_module_init(self):
        # opacus lib needs to init lazy module first
        input_shape = list(self.vocab)
        # set batch size equals to 1 to initialize lazy module
        input_shape.insert(0, 1)
        self.model.forward(torch.ones(input_shape).to(self.device))
        super().lazy_module_init()

    def enable_DP_training(self, train_dataloader):
        self.model,\
        self.optimizer,\
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