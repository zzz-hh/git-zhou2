import pandas as pd
from sklearn.model_selection import train_test_split
import torch
from fediux.utils.logger_util import logger
from fediux.FL.utils.file import save_json_file,save_csv_file
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.metrics import classification_metrics  
from transformers import BertForSequenceClassification, BertTokenizer
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader


class BertClient(BaseModel):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        process = self.common_params['process']
        if process == 'train':
            self.train()
        elif process == 'predict':
            self.predict()
        else:
            error_msg = f"Unsupported process: {process}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def train(self):
        self.classifier_only = self.common_params["classifier_only"]
        remote_party = self.roles[self.role_params['others_role']]
        self.server_channel = GrpcClient(local_party=self.role_params['self_name'],
                                  remote_party=remote_party,
                                  node_info=self.node_info,
                                  task_info=self.task_info)
        # 加载数据 
        df = pd.read_csv(self.role_params['data']['data_path'])
        label = self.common_params['label']
        test_size =  self.common_params.get('test_size', 0.2)
        df.dropna(inplace=True)
        x = df['text'].tolist()
        y = df[label].tolist()

        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_size, shuffle=True, random_state=42)

        self.send_output_dim(y) # 确认并更新 self.output_dim
        self.num_examples = len(x_train)
        self.send_params()

        # 初始化模型
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = BertTokenizer.from_pretrained(self.role_params["pretrained_model"])
        self.model = BertForSequenceClassification.from_pretrained(
                    self.role_params["pretrained_model"],
                    num_labels=self.output_dim
                    ).to(self.device)
        self.init_model()
        # 检查CPU内存
        import psutil
        logger.info(f"Available CPU memory: {psutil.virtual_memory().available / 1024**3:.2f} GB")

        train_set = TextDataset(x_train, y_train, self.tokenizer, self.common_params["max_length"])
        batch_size = min(len(x_train), self.common_params['batch_size'])
        train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)

        test_set = TextDataset(x_test, y_test, self.tokenizer, self.common_params["max_length"])
        batch_size = min(len(x_test), self.common_params['batch_size'])
        test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=True)

        # 初始化优化器
        learning_rate = self.common_params["learning_rate"]
        if self.classifier_only:
            optimizer = AdamW(self.model.classifier.parameters(), lr=learning_rate)
        else:
            optimizer = AdamW(self.model.parameters(), lr=learning_rate)

        # 训练模型
        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i+1} / {global_epoch} --------")

            local_epoch = self.common_params['local_epoch']
            for j in range(local_epoch):
                logger.info(f"-------- local epoch {j+1} / {local_epoch} --------")
                self.model.train()
                for batch in train_loader:
                    optimizer.zero_grad()
                    input_ids = batch["input_ids"].to(self.device)
                    attention_mask = batch["attention_mask"].to(self.device)
                    labels = batch["labels"].to(self.device)

                    # 如果是二分类任务，将labels转换为Float类型
                    if self.output_dim == 1:
                        labels = labels.float()

                    outputs = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels
                    )
                    # 添加内存监控
                    logger.info(f"CPU memory usage: {psutil.Process().memory_info().rss / 1024**2:.2f} MB")

                    loss = outputs.loss
                    loss.backward()
                    optimizer.step()

                logger.info(f"-------- local epoch {j+1} / {local_epoch} --------")

            if self.common_params['print_metrics']:
                self.print_metrics(train_loader)
            self.send_model()

        logger.info("-------- finish training --------")

        # send final metrics
        trainMetrics = self.send_metrics(test_loader)
        save_json_file(trainMetrics, self.role_params['metric_path'])

        # 保存模型    
        self.model.save_pretrained(self.role_params['model_path'])
        self.tokenizer.save_pretrained(self.role_params['model_path'])

    def print_metrics(self, dataloader):
        size = len(dataloader.dataset)
        self.model.eval()
        y_true, y_pred = [], []
        loss = 0

        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                # 如果是二分类任务，将labels转换为Float类型
                if self.output_dim == 1:
                    labels = labels.float()

                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                loss += outputs.loss  # 从模型输出中获取loss
                y_true.extend(labels.cpu())
                y_pred.extend(outputs.logits.cpu())

        # 将列表转换为张量
        y_true = torch.tensor(y_true)
        y_pred = torch.tensor(y_pred)

        loss /= size
        logger.info(f"loss: {loss}")
        self.server_channel.send("loss", loss)

        if self.output_dim == 1:
            y_score = torch.sigmoid(y_pred)
            metrics = classification_metrics(
                y_true,
                y_score,
                multiclass=False,
                metrics_name=["acc"],
            )
        else:
            y_score = torch.softmax(y_pred, dim=1)
            metrics = classification_metrics(
                y_true,
                y_score,
                multiclass=True,
                metrics_name=["acc"],
            )
        logger.info(f"Accuracy: {metrics['acc']}")
        self.server_channel.send("acc", metrics["acc"])

    def predict(self):
        # 加载数据 
        df = pd.read_csv(self.role_params['data']['data_path'])
        df.dropna(inplace=True)
        x = df['text'].tolist()

        # 从保存的模型配置中获取output_dim
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(self.role_params["model_path"])
        self.output_dim = config.num_labels  # 获取模型的输出维度

        # 加载模型
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = BertTokenizer.from_pretrained(self.role_params["model_path"])
        self.model = BertForSequenceClassification.from_pretrained(
                    self.role_params["model_path"],
                    num_labels=self.output_dim
                    ).to(self.device)

        dataset = TextDataset(x, [0]*len(x), self.tokenizer, self.common_params["max_length"])
        batch_size = min(len(x), self.common_params['batch_size'])
        data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        self.model.eval()
        y_pred = []
        with torch.no_grad():
            for batch in data_loader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)

                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                y_pred.extend(outputs.logits.cpu())

        # 将列表转换为张量
        y_pred = torch.tensor(y_pred)

        if self.output_dim == 1:
            pred_prob = torch.sigmoid(y_pred)
            pred_y = (pred_prob > 0.5).int()
            pred_prob = pred_prob.reshape(-1)
        else:
            pred_prob = torch.softmax(y_pred, dim=1)
            pred_y = pred_prob.argmax(1)

        if self.output_dim == 1:
            pred_prob = pred_prob.reshape(-1)
        result = pd.DataFrame({
            'pred_prob': pred_prob.tolist(),
            'pred_y': pred_y.reshape(-1).tolist()
        })

        data_result = pd.concat([df, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])

    def get_model(self):
        if self.classifier_only:
            return self.model.classifier.state_dict()
        else:
            return self.model.state_dict()

    def set_model(self, model):
        if self.classifier_only:
            self.model.classifier.load_state_dict(model)
        else:
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

    def recv_server_model(self):
        return self.server_channel.recv("server_model")

    def init_model(self):
        classifier_dict = self.model.classifier.state_dict()
        self.server_channel.send("client_model", classifier_dict)
        self.set_model(self.recv_server_model())

    def send_model(self):
        self.server_channel.send("client_model", self.get_model())
        if self.classifier_only:
            self.model.classifier.load_state_dict(self.recv_server_model())
        else:
            self.model.load_state_dict(self.recv_server_model())

    def send_metrics(self, dataloader):
        size = len(dataloader.dataset)
        self.model.eval()
        y_true, y_pred = [], []
        loss = 0

        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                # 如果是二分类任务，将labels转换为Float类型
                if self.output_dim == 1:
                    labels = labels.float()

                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )

                loss += outputs.loss  # 从模型输出中获取loss
                y_true.extend(labels.cpu())
                y_pred.extend(outputs.logits.cpu())

        # 将列表转换为张量
        y_true = torch.tensor(y_true)
        y_pred = torch.tensor(y_pred)

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
        logger.info("acc: {}".format(metrics["train_acc"]))
        self.server_channel.send("acc", metrics["train_acc"])

        return metrics

    def send_params(self):
        # send other params to compute aggregated metrics
        self.server_channel.send('num_examples', self.num_examples)

class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].flatten(),
            "attention_mask": encoding["attention_mask"].flatten(),
            "labels": torch.tensor(label, dtype=torch.long)
        }
