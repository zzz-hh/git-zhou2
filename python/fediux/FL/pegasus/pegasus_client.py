import pandas as pd
import torch
from fediux.utils.logger_util import logger
from fediux.FL.utils.file import save_json_file,save_csv_file
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.net_work import GrpcClient
from .tokenizers_pegasus import PegasusTokenizer
from .data_utils import compute_rouge
from transformers import PegasusForConditionalGeneration
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader


class PegasusClient(BaseModel):

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
        remote_party = self.roles[self.role_params['others_role']]
        self.server_channel = GrpcClient(local_party=self.role_params['self_name'],
                                  remote_party=remote_party,
                                  node_info=self.node_info,
                                  task_info=self.task_info)
        # 加载数据 
        df = pd.read_csv(self.role_params['data']['data_path'])
        label = self.common_params['label']
        df.dropna(inplace=True)
        x = df['text'].tolist()
        y = df[label].tolist()

        self.num_examples = len(x)
        self.send_params()

        # 初始化模型
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = PegasusForConditionalGeneration.from_pretrained(self.role_params["pretrained_model"]).to(self.device)
        self.tokenizer = PegasusTokenizer.from_pretrained(self.role_params["pretrained_model"])
        # 检查CPU内存
        import psutil
        logger.info(f"Available CPU memory: {psutil.virtual_memory().available / 1024**3:.2f} GB")

        dataset = TextDataset(x, y, self.tokenizer, self.common_params["max_length"], self.common_params["max_target_length"])
        batch_size = min(len(x), self.common_params['batch_size'])
        data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        # 初始化优化器
        optimizer = AdamW(self.model.lm_head.parameters(), lr=self.common_params["learning_rate"])

        # 训练模型
        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i+1} / {global_epoch} --------")

            local_epoch = self.common_params['local_epoch']
            for j in range(local_epoch):
                logger.info(f"-------- local epoch {j+1} / {local_epoch} --------")
                self.model.train()
                total_loss = 0
                for batch in data_loader:
                    optimizer.zero_grad()
                    input_ids = batch["input_ids"].to(self.device)
                    attention_mask = batch["attention_mask"].to(self.device)
                    labels = batch["labels"].to(self.device)

                    outputs = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels
                    )
                    # 添加内存监控
                    logger.info(f"CPU memory usage: {psutil.Process().memory_info().rss / 1024**2:.2f} MB")

                    loss = outputs.loss
                    total_loss += loss.item()
                    loss.backward()
                    optimizer.step()

                logger.info(f"-------- local epoch {j+1} / {local_epoch} --------")
                
            if self.common_params['print_metrics']:
                self.print_metrics(data_loader)
            self.send_model()

        logger.info("-------- finish training --------")

        # send final metrics
        trainMetrics = self.send_metrics(data_loader)
        save_json_file(trainMetrics, self.role_params['metric_path'])

        # 保存模型    
        self.model.save_pretrained(self.role_params['model_path'])
        self.tokenizer.save_pretrained(self.role_params['model_path'])
        logger.info(f"model saved to {self.role_params['model_path']}")

    def predict(self):
        # 加载数据 
        df = pd.read_csv(self.role_params['data']['data_path'])
        df.dropna(inplace=True)
        x = df['text'].tolist()

        # 加载模型
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = PegasusForConditionalGeneration.from_pretrained(self.role_params["model_path"]).to(self.device)
        self.tokenizer = PegasusTokenizer.from_pretrained(self.role_params["model_path"])

        dataset = TextDataset(x, [""]*len(x), self.tokenizer, self.common_params["max_length"], self.common_params["max_target_length"])
        batch_size = min(len(x), self.common_params['batch_size'])
        data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        self.model.eval()
        y_pred = []
        with torch.no_grad():
            for batch in data_loader:
                input_ids = batch["input_ids"].to(self.device)

                summary_ids = self.model.generate(input_ids, max_new_tokens=self.common_params["max_target_length"])
                summaries = self.tokenizer.batch_decode(summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
                
                y_pred.extend(summaries)

        result = pd.DataFrame({'summary_pred': y_pred})
        logger.info(f"result: {result}")

        data_result = pd.concat([df, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])

    def print_metrics(self, dataloader):
        self.send_metrics(dataloader)

    def send_metrics(self, dataloader):
        self.model.eval()
        rouge_scores = []

        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                # 生成预测摘要
                summary_ids = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=self.common_params["max_target_length"]
                )
                pred_summaries = self.tokenizer.batch_decode(
                    summary_ids,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False
                )
                target_summaries = self.tokenizer.batch_decode(
                    labels,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False
                )
                
                # 计算ROUGE分数
                for pred, target in zip(pred_summaries, target_summaries):
                    logger.info(f"Predicted Summary: {pred}")
                    logger.info(f"Target Summary: {target}")
                    rouge = compute_rouge(target, pred)
                    logger.info(f"ROUGE Scores: {rouge}")
                    rouge_scores.append(rouge)

        # 计算平均ROUGE分数
        avg_rouge = {key: sum([score[key] for score in rouge_scores]) / len(rouge_scores) for key in rouge_scores[0]}
        
        logger.info(f"Average ROUGE Scores: {avg_rouge}")
        self.server_channel.send("avg_rouge", avg_rouge)
        return avg_rouge

    def send_model(self):
        self.server_channel.send("client_model", self.model.lm_head.state_dict())
        self.model.lm_head.load_state_dict(self.server_channel.recv("server_model"))
        self.model.to(self.device)

    def send_params(self):
        # send other params to compute aggregated metrics
        self.server_channel.send('num_examples', self.num_examples)

class TextDataset(Dataset):
    def __init__(self, texts, summaries, tokenizer, max_length, max_target_length):
        self.texts = texts
        self.summaries = summaries
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.max_target_length = max_target_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        summary = str(self.summaries[idx])
        
        inputs = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        targets = self.tokenizer(
            summary,
            max_length=self.max_target_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        return {
            "input_ids": inputs.input_ids.squeeze(),
            "attention_mask": inputs.attention_mask.squeeze(),
            "labels": targets.input_ids.squeeze()
        }
