import logging
from collections import Counter
import jieba
import numpy as np
from numpy.random import default_rng
import pandas as pd
import os
import imghdr
import zipfile
from sqlalchemy import create_engine
from PIL import Image
import torch
from torch.utils.data import Dataset as TorchDataset
from torchtext.vocab import build_vocab_from_iterator
from fediux.utils.logger_util import logger
import pyarrow.parquet as pq


def read_data(data_info,
              selected_column=None,
              droped_column=None,
              transform=None,
              target_transform=None,
              test_size=None):
    data_type = data_info['type'].lower()

    if data_type == 'csv':
        return read_csv(data_info['data_path'],
                        selected_column,
                        droped_column)
    elif data_type == 'image':

        return TorchImageDataset(data_info['image_dir'],
                                 data_info['annotations_file'],
                                 transform,
                                 target_transform, test_size)
    elif data_type == 'mysql':
        return read_mysql(data_info['username'],
                          data_info['password'],
                          data_info['host'],
                          data_info['port'],
                          data_info['dbName'],
                          data_info['tableName'],
                          selected_column,
                          droped_column)
    elif data_type == 'parquet':
        return read_parquet(data_info['data_path'],
                            selected_column,
                            droped_column)
    else:
        error_msg = f'Unsupported data type: {data_type}'
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def read_csv(data_path, selected_column=None, droped_column=None):
    data = pd.read_csv(data_path)
    if selected_column:
        data = data[selected_column]
    if droped_column in data.columns:
        data.pop(droped_column)
    return data


def read_parquet(data_path, selected_column=None, droped_column=None):
    parquet_file = pq.ParquetFile(data_path)
    data = parquet_file.read().to_pandas()
    if selected_column:
        data = data[selected_column]
    if droped_column in data.columns:
        data.pop(droped_column)
    return data


def read_mysql(user,
               password,
               host,
               port,
               database,
               table_name,
               selected_column=None,
               droped_column=None):
    engine_str = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(engine_str)
    with engine.connect() as conn:
        df = pd.read_sql_table(table_name, conn, columns=selected_column)
        if droped_column in df.columns:
            df.pop(droped_column)
        return df


class TorchImageDataset(TorchDataset):

    def __init__(self,
                 img_dir,
                 annotations_file=None,
                 transform=None,
                 target_transform=None,
                 test_size=None):
        if zipfile.is_zipfile(img_dir):
            with zipfile.ZipFile(img_dir, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(img_dir))
                self.img_dir = os.path.join(os.path.dirname(img_dir),
                                            zip_ref.namelist()[0])
        else:
            self.img_dir = img_dir

        self.transform = transform
        self.target_transform = target_transform

        img_type = ['jpeg', 'png']

        if annotations_file:
            self.img_labels = pd.read_csv(annotations_file)
        else:
            file_name = [
                f for f in os.listdir(self.img_dir)
                if imghdr.what(os.path.join(self.img_dir, f)) in img_type
            ]
            self.img_labels = pd.DataFrame(file_name,
                                           columns=['file_name'])
        labels_ = self.img_labels.copy()
        self.begin_idx=0
        logger.info("data_lenth0={}".format(len(self.img_labels)))
        if test_size is not None:
            len_labels = len(labels_)

            if test_size > 0.5:
                self.img_labels = labels_[0:int(len_labels * test_size)]
            else:
                self.img_labels = labels_[int(len_labels * (1 - test_size)):]
                self.begin_idx=int(len_labels * (1 - test_size))
        logger.info("data_lenth={}".format(len(self.img_labels)))
        logger.info("data = {}".format(self.img_labels))

    def __len__(self):
        return len(self.img_labels)

    def __getitem__(self, idx):
        idx=idx+self.begin_idx
        img_path = os.path.join(self.img_dir,
                                self.img_labels.loc[idx, 'file_name'])
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)

        if 'y' in self.img_labels.columns:
            label = self.img_labels.loc[idx, 'y']
            if self.target_transform:
                label = self.target_transform(label)
            return image, label
        else:
            return image


class ChineseTextDataset(TorchDataset):
    def __init__(self, X, Y, output_dim, max_seq_len=512):
        self.texts = X
        self.labels = np.array(Y)
        # 加载停用词表
        stopwords_file = 'stopwords.txt'

        try:
            with open(stopwords_file, 'r', encoding='utf-8') as f:
                self.stopwords = set(line.strip() for line in f)
        except FileNotFoundError:
            self.stopwords = set()
            logger.warning(f"停用词文件 {stopwords_file} 不存在，已初始化为空集合")
        # 分词和词汇表
        self.vocab = None
        self.max_seq_len = max_seq_len
        self.output_dim = output_dim

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]

        # 分词并转换为索引
        tokens = self.chinese_tokenizer(text)[:self.max_seq_len]
        indices = [self.vocab[token] for token in tokens]

        # 填充到固定长度
        padded = indices + [self.vocab["<pad>"]] * (self.max_seq_len - len(indices))
        if self.output_dim == 1:
            tmp_y = torch.tensor([label], dtype=torch.float32)
        else:
            tmp_y = torch.tensor(label)
        return torch.tensor(padded), tmp_y

    def word_count(self):
        # 构建词汇表
        def yield_tokens(texts):
            for text in texts:
                yield self.chinese_tokenizer(text)

        # 统计词频
        self.counter = Counter()
        for tokens in yield_tokens(self.texts):
            self.counter.update(tokens)
        return self.counter
    def chinese_tokenizer(self, text):
        try:
            # 使用 jieba 进行分词
            words = list(jieba.cut(text))
        except Exception as e:
            # print(f"Error in jieba.cut: {e}")
            words = []
        # 如果有停用词表，则过滤停用词
        if self.stopwords:
            words = [word for word in words if word not in self.stopwords]
        return words

    def set_vocab(self, vocab_list):
        self.vocab = build_vocab_from_iterator(
            [vocab_list],
            specials=["<unk>", "<pad>"]
        )
        self.vocab.set_default_index(self.vocab["<unk>"])

    def load_vocab(self, vocab):
        self.vocab = vocab


class DataLoader:

    def __init__(self, dataset, label=None, batch_size=1, shuffle=True, seed=None):
        self.dataset = dataset
        self.label = label
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.n_samples = self.__len__()
        self.indices = np.arange(self.n_samples)
        self.start = 0
        if seed:
            np.random.seed(seed)

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        return self.dataset[idx]

    def __iter__(self):
        return self

    def __next__(self):
        if self.start == 0:
            if self.shuffle:
                np.random.shuffle(self.indices)

        start = self.start
        end = start + self.batch_size
        if end > self.n_samples:
            end = self.n_samples
        self.start += self.batch_size

        if start < self.n_samples:
            batch_idx = self.indices[start:end]
            if self.label is not None:
                return self.dataset[batch_idx], self.label[batch_idx]
            else:
                return self.dataset[batch_idx]
        else:
            self.start = 0
            raise StopIteration


class DPDataLoader(DataLoader):

    def __init__(self, dataset, label=None, batch_size=1):
        self.dataset = dataset
        self.label = label
        self.batch_size = batch_size
        self.n_samples = self.__len__()
        self.rng = default_rng(seed=self.n_samples)
        self.max_iter = self.n_samples // self.batch_size
        self.num_iter = 0

    def __next__(self):
        self.num_iter += 1
        if self.num_iter <= self.max_iter:
            batch_idx = self.rng.choice(self.n_samples,
                                        self.batch_size,
                                        replace=False,
                                        shuffle=False)
            if self.label is not None:
                return self.dataset[batch_idx], self.label[batch_idx]
            else:
                return self.dataset[batch_idx]
        else:
            self.num_iter = 0
            raise StopIteration