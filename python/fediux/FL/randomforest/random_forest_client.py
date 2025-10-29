import numpy as np
import random
from collections import Counter

import pandas as pd
from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file,\
                                   save_pickle_file,\
                                   load_pickle_file,\
                                   save_csv_file
from fediux.FL.utils.dataset import read_data
from fediux.utils.logger_util import logger
from sklearn.model_selection import train_test_split
from sklearn.utils.validation import check_array
from fediux.FL.metrics import classification_metrics


class RandomForestClient(BaseModel):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        logger.info(f"start run")
        process = self.common_params['process']
        logger.info(f"process: {process}")
        test_size = self.common_params.get('test_size',0.2)
        n_trees = self.common_params.get('n_trees')
        if process == 'train':
            self.train(n_trees,test_size)
        elif process == 'predict':
            self.predict()
        else:
            error_msg = f"Unsupported process: {process}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def train(self,n_trees,test_size):
        # setup communication channels
        logger.info(f"start train")
        print("setup communication channels")
        remote_party = self.roles[self.role_params['others_role']]
        server_channel = GrpcClient(local_party=self.role_params['self_name'],
                                    remote_party=remote_party,
                                    node_info=self.node_info,
                                    task_info=self.task_info)
        print(remote_party)

        # 加载数据
        selected_column = self.common_params.get('selected_column')
        if selected_column is None:
            selected_column = self.role_params.get('selected_column')
        id = self.common_params['id']
        df = read_data(data_info=self.role_params['data'],
                       selected_column=selected_column,
                       droped_column=id)
        if id in df.columns:
            df.pop(id)
        df.dropna(inplace=True)
        label = self.common_params['label']
        y = df.pop(label).values
        x=df

        # client 初始化
        method = self.common_params['method']
        if method == 'Plaintext':
            client = Plaintext_RF_Client(x, y, 
                                         self.common_params, 
                                         server_channel, 
                                         test_size=test_size,
                                         n_trees=n_trees, 
                                         max_depth=10, 
                                         min_samples_split=2, 
                                         n_features=None)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # client training
        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i + 1} / {global_epoch} --------")
            client.fit()
            client.train()

            if self.common_params['print_metrics']:
                client.print_metrics()
        logger.info("-------- finish training --------")

        # send final metrics
        trainMetrics = client.send_metrics()
        save_json_file(trainMetrics, self.role_params['metric_path'])

        # save model for prediction
        modelFile = {
            "selected_column": selected_column,
            "id": id,
            "label": label,
            "multiclass": client.multiclass,
            "model": client.rf
        }
        save_pickle_file(modelFile, self.role_params['model_path'])

    def predict(self):
        # load model for prediction
        modelFile = load_pickle_file(self.role_params['model_path'])
        logger.info(modelFile)

        # load dataset
        origin_data = read_data(data_info=self.role_params['data'])

        x = origin_data.copy()
        selected_column = modelFile['selected_column']
        if selected_column:
            x = x[selected_column]
        id = modelFile['id']
        if id in x.columns:
            x.pop(id)
        label = modelFile['label']
        if label in x.columns:
            y = x.pop(label).values
        x = check_array(x, dtype='numeric')

        model = modelFile['model']
        pred_prob = model.predict_prob(x)

        multiclass = modelFile['multiclass']
        if multiclass:
            pred_y = np.argmax(pred_prob, axis=1)
            pred_prob = pred_prob.tolist()
        else:
            pred_y = np.array(pred_prob > 0.5, dtype='int')

        result = pd.DataFrame({
            'pred_prob': pred_prob,
            'pred_y': pred_y
        })
        
        data_result = pd.concat([origin_data, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])


class Plaintext_RF_Client:

    def __init__(self, x, y,common_params, server_channel,test_size,n_trees, max_depth=10, min_samples_split=2, n_features=None):
        self.n_trees = common_params['n_trees']
        self.server_channel = server_channel
        self.fe = x.columns.values.tolist()
        self.send_output_dim(y)
        self.num_examples = x.shape[0]
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(x.values, y, test_size=test_size, random_state=42)
        self.rf=RandomForest(n_trees=n_trees, max_depth=max_depth, min_samples_split=min_samples_split, n_features=n_features)
        self.send_params()
        
    def send_params(self):
        self.server_channel.send('num_examples', self.num_examples)

    def send_output_dim(self, y):
        output_dim = y.max() + 1

        if output_dim == 2:
            output_dim = 1

        self.server_channel.send('output_dim', output_dim)
        output_dim = self.server_channel.recv('output_dim')
        self.multiclass = output_dim > 1

    def fit(self):
        self.rf.fit(self.X_train, self.y_train)

    def recv_server_model(self):
        return self.server_channel.recv("server_trees")

    def set_model(self, model):
        self.rf.trees=model[0]

    def train(self):
        self.server_channel.send("client_trees", self.rf.trees)
        self.set_model(self.recv_server_model())

    def send_metrics(self):
        y_score = self.rf.predict_prob(self.X_test)
        if self.multiclass:
            metrics = classification_metrics(
                self.y_test,
                y_score,
                multiclass=self.multiclass,
                prefix="train_",
                metrics_name=["acc",
                              "f1",
                              "precision",
                              "recall",
                              "auc",
                              "confusion_matrix",],
            )
        else:
            metrics = classification_metrics(
                self.y_test,
                y_score,
                multiclass=self.multiclass,
                prefix="train_",
                metrics_name=["acc",
                              "f1",
                              "precision",
                              "recall",
                              "auc",
                              "roc",
                              "ks",
                              "confusion_matrix",
                              "bimodal"],
            )

        self.server_channel.send("acc", metrics["train_acc"])
        return metrics

    def print_metrics(self):
        y_score = self.rf.predict_prob(self.X_test)
        metrics = classification_metrics(
            self.y_test,
            y_score,
            multiclass=self.multiclass,
            metrics_name=["acc",],
        )

        self.server_channel.send("acc", metrics["acc"])


class DecisionTree:
    def __init__(self, max_depth=None, min_samples_split=2, n_features=None):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.n_features = n_features
        self.root = None

    def fit(self, X, y):
        self.n_features = X.shape[1] if not self.n_features else min(self.n_features, X.shape[1])
        self.root = self._grow_tree(X, y)

    def _grow_tree(self, X, y, depth=0):
        n_samples, n_feats = X.shape
        n_labels = len(np.unique(y))

        # 停止条件
        if (self.max_depth is not None and depth >= self.max_depth) or n_labels == 1 or n_samples < self.min_samples_split:
            leaf_value = self._most_common_label(y)
            return Node(value=leaf_value)

        # 随机选择特征
        feat_idxs = random.sample(range(n_feats), self.n_features)

        # 找到最佳分割
        best_feat, best_thresh = self._best_split(X, y, feat_idxs)

        # 创建子节点
        left_idxs, right_idxs = self._split(X[:, best_feat], best_thresh)
        left = self._grow_tree(X[left_idxs, :], y[left_idxs], depth+1)
        right = self._grow_tree(X[right_idxs, :], y[right_idxs], depth+1)
        return Node(best_feat, best_thresh, left, right)

    def _best_split(self, X, y, feat_idxs):
        best_gain = -1
        split_idx, split_thresh = None, None

        for feat_idx in feat_idxs:
            X_column = X[:, feat_idx]
            thresholds = np.unique(X_column)

            for thresh in thresholds:
                # 计算信息增益
                gain = self._information_gain(y, X_column, thresh)

                if gain > best_gain:
                    best_gain = gain
                    split_idx = feat_idx
                    split_thresh = thresh

        return split_idx, split_thresh

    def _information_gain(self, y, X_column, threshold):
        # 父熵
        parent_entropy = self._entropy(y)

        # 创建子节点
        left_idxs, right_idxs = self._split(X_column, threshold)
        if len(left_idxs) == 0 or len(right_idxs) == 0:
            return 0

        # 计算子节点的加权平均熵
        n = len(y)
        n_l, n_r = len(left_idxs), len(right_idxs)
        e_l, e_r = self._entropy(y[left_idxs]), self._entropy(y[right_idxs])
        child_entropy = (n_l / n) * e_l + (n_r / n) * e_r

        # 计算信息增益
        information_gain = parent_entropy - child_entropy
        return information_gain

    def _split(self, X_column, split_thresh):
        left_idxs = np.argwhere(X_column <= split_thresh).flatten()
        right_idxs = np.argwhere(X_column > split_thresh).flatten()
        return left_idxs, right_idxs

    def _entropy(self, y):
        hist = np.bincount(y)
        ps = hist / len(y)
        return -np.sum([p * np.log(p) for p in ps if p > 0])

    def _most_common_label(self, y):
        counter = Counter(y)
        return counter.most_common(1)[0][0]

    def predict(self, X):
        return np.array([self._traverse_tree(x, self.root) for x in X])

    def _traverse_tree(self, x, node):
        if node.is_leaf():
            return node.value

        if x[node.feature] <= node.threshold:
            return self._traverse_tree(x, node.left)
        return self._traverse_tree(x, node.right)


class Node:
    def __init__(self, feature=None, threshold=None, left=None, right=None, value=None):
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value

    def is_leaf(self):
        return self.value is not None


class RandomForest:
    def __init__(self, n_trees=100, max_depth=10, min_samples_split=2, n_features=None):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.n_features = n_features
        self.trees = []

    def fit(self, X, y):
        self.trees = []
        for _ in range(self.n_trees):
            tree = DecisionTree(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                n_features=self.n_features
            )
            # 自助采样(bootstrap)
            X_sample, y_sample = self._bootstrap_samples(X, y)
            tree.fit(X_sample, y_sample)
            self.trees.append(tree)

    def _bootstrap_samples(self, X, y):
        n_samples = X.shape[0]
        idxs = np.random.choice(n_samples, size=n_samples, replace=True)
        return X[idxs], y[idxs]

    def predict(self, X):
        tree_preds = np.array([tree.predict(X) for tree in self.trees])
        # 多数投票
        return np.array([self._most_common_label(pred) for pred in tree_preds.T])

    def _most_common_label(self, y):
        counter = Counter(y)
        return counter.most_common(1)[0][0]

    def predict_prob(self, X):
        tree_preds = np.array([tree.predict(X) for tree in self.trees])
        # 计算每个类别的概率
        unique_classes = np.unique(np.concatenate(tree_preds))
        proba = np.zeros((X.shape[0], len(np.unique(np.concatenate(tree_preds)))))
        for i in range(X.shape[0]):
            counts = np.bincount(tree_preds[:, i])
            proba[i, :len(counts)] = counts / self.n_trees
        
        # 二分类时只返回类别1的概率
        if len(unique_classes) == 2:
            return proba[:, 1]  # 返回类别1的概率
        return proba