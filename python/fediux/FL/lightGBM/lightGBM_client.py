import numpy as np
import pandas as pd
from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file,\
                                   save_pickle_file,\
                                   load_pickle_file,\
                                   save_csv_file
from fediux.FL.utils.dataset import read_data
from fediux.FL.metrics import classification_metrics
from fediux.utils.logger_util import logger
from sklearn.utils.validation import check_array
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss

class LightGBMClient(BaseModel):

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
        # setup communication channels
        test_size = self.common_params.get('test_size',0.2)
        n_estimators = self.common_params.get('n_estimators')
        learning_rate = self.common_params.get('learning_rate')
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
        if id in df.columns:
            df.pop(id)
        df.dropna(inplace=True)
        label = self.common_params['label']
        y = df.pop(label).values
        x=df

        # client 初始化
        method = self.common_params['method']
        if method == 'Plaintext':
            client = Plaintext_LightGBM_Client(x,y, self.common_params, server_channel,test_size=test_size,n_estimators=n_estimators, learning_rate=learning_rate)
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

        modelFile = {
            "selected_column": selected_column,
            "id": id,
            "label": label,
            "multiclass": client.multiclass,
            "model": client.lgb
        }
        save_pickle_file(modelFile, self.role_params['model_path'])

    def predict(self):
        # load model for prediction
        modelFile = load_pickle_file(self.role_params['model_path'])

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


class Plaintext_LightGBM_Client:

    def __init__(self, x, y,common_params, server_channel,test_size,n_estimators=100, learning_rate=0.01,):
        self.n_estimators = common_params['n_estimators']
        self.learning_rate = common_params['learning_rate']
        self.server_channel = server_channel
        self.test_size=test_size
        self.x = x.values  # 将DataFrame转为numpy数组
        self.send_output_dim(y)
        self.num_examples = x.shape[0]
        self.y=y
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(self.x, self.y, test_size=self.test_size, random_state=42)
        self.lgb=HistGradientBoostingClassifier(n_estimators=self.n_estimators, learning_rate= self.learning_rate)
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
        self.lgb.fit(self.X_train, self.y_train)

    def recv_server_model(self):
        return self.server_channel.recv("server_trees")

    def set_model(self, model):
        self.lgb.trees=model[0]

    def train(self):
        self.server_channel.send("client_trees", self.lgb.trees)
        self.set_model(self.recv_server_model())

    def print_metrics(self):
        y_score = self.lgb.predict_prob(self.X_test)
        metrics = classification_metrics(
            self.y_test,
            y_score,
            multiclass=self.multiclass,
            metrics_name=["acc",],
        )

        self.server_channel.send("acc", metrics["acc"])

    def send_metrics(self):
        y_score = self.lgb.predict_prob(self.X_test)
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

class TreeNode:
    def __init__(self, depth=0, max_depth=7):
        self.is_leaf = False
        self.split_feature = None
        self.split_threshold = None
        self.left_child = None
        self.right_child = None
        self.value = 0  # 叶子节点预测值
        self.depth = depth
        self.max_depth = max_depth
        self.sample_indices = []
        self.grad_sum = 0.0
        self.hess_sum = 0.0


class HistGradientBoostingClassifier:
    def __init__(self, n_estimators=100, learning_rate=0.1, max_depth=7,
                 min_samples_leaf=20, max_bins=64, reg_lambda=1.0,
                 subsample=1.0, top_rate=0.2, other_rate=0.1,
                 cat_features=None, random_state=None):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.max_bins = max_bins
        self.reg_lambda = reg_lambda
        self.subsample = subsample
        self.top_rate = top_rate  # GOSS中保留大梯度样本的比例
        self.other_rate = other_rate  # GOSS中随机采样小梯度样本的比例
        self.cat_features = cat_features if cat_features else []
        self.random_state = random_state
        self.trees = []
        self.bin_mappers = []
        self.bin_boundaries = []
        self.classes_ = None
        self.base_value = None
        self.feature_importances_ = None
        self.loss_history = []

        if random_state is not None:
            np.random.seed(random_state)

    def fit(self, X, y, eval_set=None, early_stopping_rounds=None, verbose=False):
        # 初始化类别信息
        self.classes_ = np.unique(y)
        if len(self.classes_) > 2:
            raise ValueError("只支持二分类")

        # 将y转换为0/1
        y = np.where(y == self.classes_[1], 1, 0)

        # 初始化预测值为对数几率
        pos_ratio = np.mean(y)
        self.base_value = np.log(pos_ratio / (1 - pos_ratio)) if pos_ratio > 0 else 0
        current_pred = np.full_like(y, self.base_value, dtype=float)

        # 为每个特征创建分桶映射
        self._create_bin_mappers(X)

        # 初始化特征重要性
        self.feature_importances_ = np.zeros(X.shape[1])

        best_loss = float('inf')
        no_improve_count = 0

        for i in range(self.n_estimators):
            # 计算当前概率和梯度
            probs = self._sigmoid(current_pred)
            gradients = probs - y
            hessians = probs * (1 - probs)

            # 梯度单边采样 (GOSS)
            sample_indices = self._goss_sampling(gradients)

            # 构建新树
            tree = self._build_tree(X, gradients, hessians, sample_indices)
            self.trees.append(tree)

            # 更新预测
            leaf_preds = self._predict_tree(X, tree)
            current_pred += self.learning_rate * leaf_preds

            # 计算并记录损失
            train_loss = log_loss(y, self._sigmoid(current_pred))
            self.loss_history.append(train_loss)

            # 验证集评估
            val_loss = None
            if eval_set:
                X_val, y_val = eval_set
                y_val_bin = np.where(y_val == self.classes_[1], 1, 0)
                y_pred_val = self.predict_prob(X_val)[:, 1]
                val_loss = log_loss(y_val_bin, y_pred_val)

                if verbose:
                    logger.info(f"Iter {i + 1}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

                # 早停机制
                if early_stopping_rounds:
                    if val_loss < best_loss:
                        best_loss = val_loss
                        no_improve_count = 0
                    else:
                        no_improve_count += 1
                        if no_improve_count >= early_stopping_rounds:
                            if verbose:
                                logger.info(f"Early stopping at iteration {i + 1}")
                            break
            elif verbose:
                logger.info(f"Iter {i + 1}, Train Loss: {train_loss:.4f}")

        return self

    def _create_bin_mappers(self, X):
        n_features = X.shape[1]
        self.bin_mappers = []
        self.bin_boundaries = []

        for i in range(n_features):
            if i in self.cat_features:
                # 类别特征 - 直接使用所有类别
                unique_vals = np.unique(X[:, i])
                self.bin_mappers.append(unique_vals)
                self.bin_boundaries.append(None)
            else:
                # 连续特征 - 等频分桶
                feature_vals = X[:, i]
                percentiles = np.linspace(0, 100, self.max_bins + 1)
                bins = np.percentile(feature_vals.astype(float), percentiles)
                bins = np.unique(bins)  # 确保唯一值
                self.bin_mappers.append(bins)
                self.bin_boundaries.append(bins)

    def _map_to_bins(self, X):
        binned_X = np.zeros_like(X, dtype=float)
        for i in range(X.shape[1]):
            if i in self.cat_features:
                # 类别特征直接映射
                mapper = dict(zip(self.bin_mappers[i], range(len(self.bin_mappers[i]))))
                binned_X[:, i] = [mapper.get(x, -1) for x in X[:, i]]
            else:
                # 连续特征分桶
                binned_X[:, i] = np.digitize(X[:, i], self.bin_mappers[i]) - 1
        return binned_X

    def _goss_sampling(self, gradients):
        """梯度单边采样 (Gradient-based One-Side Sampling)"""
        n_samples = len(gradients)
        n_top = int(self.top_rate * n_samples)
        n_other = int(self.other_rate * n_samples)

        # 按梯度绝对值排序
        sorted_indices = np.argsort(np.abs(gradients))[::-1]

        # 选择梯度绝对值最大的样本
        top_indices = sorted_indices[:n_top]

        # 随机选择剩余样本中的一部分
        other_indices = np.random.choice(
            sorted_indices[n_top:],
            size=min(n_other, n_samples - n_top),
            replace=False
        )

        # 合并并返回采样索引
        return np.concatenate([top_indices, other_indices])

    def _build_tree(self, X, gradients, hessians, sample_indices):
        binned_X = self._map_to_bins(X)
        root = TreeNode(max_depth=self.max_depth)
        root.sample_indices = sample_indices
        root.grad_sum = np.sum(gradients[sample_indices])
        root.hess_sum = np.sum(hessians[sample_indices])
        stack = [root]

        while stack:
            node = stack.pop()
            n_samples = len(node.sample_indices)

            # 终止条件检查
            if (node.depth >= self.max_depth or
                    n_samples < 2 * self.min_samples_leaf or
                    np.all(np.abs(gradients[node.sample_indices]) < 1e-8)):
                self._make_leaf_node(node)
                continue

            # 寻找最佳分割
            best_gain = -float('inf')
            best_feature = None
            best_threshold = None
            best_left_indices = []
            best_right_indices = []

            # 遍历所有特征
            for feature_idx in range(X.shape[1]):
                # 对于类别特征使用特殊的分割方式
                if feature_idx in self.cat_features:
                    gain, threshold, left_indices, right_indices = self._find_best_categorical_split(
                        node.sample_indices,
                        binned_X[:, feature_idx],
                        gradients,
                        hessians
                    )
                else:
                    # 构建特征直方图
                    hist = self._build_histogram(
                        binned_X[node.sample_indices, feature_idx],
                        gradients[node.sample_indices],
                        hessians[node.sample_indices],
                        self.max_bins
                    )

                    # 寻找当前特征的最佳分割
                    gain, threshold, left_indices, right_indices = self._find_best_split(
                        node.sample_indices,
                        binned_X[:, feature_idx],
                        hist,
                        gradients,
                        hessians
                    )

                if gain > best_gain:
                    best_gain = gain
                    best_feature = feature_idx
                    best_threshold = threshold
                    best_left_indices = left_indices
                    best_right_indices = right_indices

            # 如果未找到有效分割
            if best_gain <= 0:
                self._make_leaf_node(node)
                continue

            # 更新特征重要性
            self.feature_importances_[best_feature] += best_gain

            # 创建子节点
            node.split_feature = best_feature
            node.split_threshold = best_threshold

            left_node = TreeNode(depth=node.depth + 1, max_depth=self.max_depth)
            left_node.sample_indices = best_left_indices
            left_node.grad_sum = np.sum(gradients[best_left_indices])
            left_node.hess_sum = np.sum(hessians[best_left_indices])
            node.left_child = left_node

            right_node = TreeNode(depth=node.depth + 1, max_depth=self.max_depth)
            right_node.sample_indices = best_right_indices
            right_node.grad_sum = np.sum(gradients[best_right_indices])
            right_node.hess_sum = np.sum(hessians[best_right_indices])
            node.right_child = right_node

            stack.append(right_node)
            stack.append(left_node)

        return root

    def _build_histogram(self, binned_feature, gradients, hessians, n_bins):
        """构建直方图: [bin_index] -> (sum_grad, sum_hess, count)"""
        hist = np.zeros((n_bins, 3))  # [sum_grad, sum_hess, count]

        for bin_val, grad, hess in zip(binned_feature, gradients, hessians):
            if not np.isnan(bin_val) and bin_val < n_bins:
                bin_idx = int(bin_val)
                hist[bin_idx, 0] += grad
                hist[bin_idx, 1] += hess
                hist[bin_idx, 2] += 1
        return hist

    def _find_best_categorical_split(self, sample_indices, binned_feature, gradients, hessians):
        """针对类别特征寻找最佳分割"""
        unique_vals = np.unique(binned_feature[sample_indices])
        if len(unique_vals) < 2:
            return -1, None, [], []

        best_gain = -1
        best_threshold = None
        best_left_indices = []
        best_right_indices = []

        # 尝试所有可能的二分分割
        for i in range(1, 2 ** (len(unique_vals) - 1)):
            # 创建二进制掩码表示哪些类别在左边
            mask = np.array([int(bit) for bit in format(i, f'0{len(unique_vals)}b')])
            left_cats = unique_vals[mask == 1]

            # 分割样本
            left_mask = np.isin(binned_feature[sample_indices], left_cats)
            left_indices = sample_indices[left_mask]
            right_indices = sample_indices[~left_mask]

            # 检查叶子节点最小样本数
            if len(left_indices) < self.min_samples_leaf or len(right_indices) < self.min_samples_leaf:
                continue

            # 计算增益
            left_grad_sum = np.sum(gradients[left_indices])
            left_hess_sum = np.sum(hessians[left_indices])
            right_grad_sum = np.sum(gradients[right_indices])
            right_hess_sum = np.sum(hessians[right_indices])

            gain = self._calculate_gain(
                left_grad_sum, left_hess_sum,
                right_grad_sum, right_hess_sum
            )

            if gain > best_gain:
                best_gain = gain
                best_threshold = left_cats
                best_left_indices = left_indices
                best_right_indices = right_indices

        return best_gain, best_threshold, best_left_indices, best_right_indices

    def _find_best_split(self, sample_indices, binned_feature, hist, gradients, hessians):
        total_grad_sum = np.sum(gradients[sample_indices])
        total_hess_sum = np.sum(hessians[sample_indices])
        n_samples = len(sample_indices)

        best_gain = -1
        best_threshold = None
        best_left_indices = []
        best_right_indices = []

        left_grad_sum = 0.0
        left_hess_sum = 0.0
        left_count = 0

        # 遍历所有可能的分割点
        for bin_idx in range(len(hist)):
            # 累加当前桶的统计量
            bin_grad_sum, bin_hess_sum, bin_count = hist[bin_idx]
            left_grad_sum += bin_grad_sum
            left_hess_sum += bin_hess_sum
            left_count += bin_count

            right_grad_sum = total_grad_sum - left_grad_sum
            right_hess_sum = total_hess_sum - left_hess_sum
            right_count = n_samples - left_count

            # 检查叶子节点最小样本数
            if left_count < self.min_samples_leaf or right_count < self.min_samples_leaf:
                continue

            # 计算增益
            gain = self._calculate_gain(
                left_grad_sum, left_hess_sum,
                right_grad_sum, right_hess_sum
            )

            if gain > best_gain:
                best_gain = gain
                # 使用桶边界作为分割阈值
                best_threshold = bin_idx
                # 记录样本索引
                mask = binned_feature[sample_indices] <= bin_idx
                best_left_indices = sample_indices[mask]
                best_right_indices = sample_indices[~mask]

        return best_gain, best_threshold, best_left_indices, best_right_indices

    def _calculate_gain(self, left_grad_sum, left_hess_sum, right_grad_sum, right_hess_sum):
        """计算增益 (使用二阶导数)"""
        left_gain = left_grad_sum ** 2 / (left_hess_sum + self.reg_lambda)
        right_gain = right_grad_sum ** 2 / (right_hess_sum + self.reg_lambda)
        total_gain = (left_grad_sum + right_grad_sum) ** 2 / (left_hess_sum + right_hess_sum + self.reg_lambda)
        return 0.5 * (left_gain + right_gain - total_gain)

    def _make_leaf_node(self, node):
        node.is_leaf = True
        # 叶子值计算 = -G/(H+lambda)
        node.value = -node.grad_sum / (node.hess_sum + self.reg_lambda)

    def _sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def _predict_tree(self, X, tree):
        return np.array([self._predict_single(x, tree) for x in X])

    def _predict_single(self, x, node):
        while not node.is_leaf:
            if node.split_feature in self.cat_features:
                # 类别特征分割
                if x[node.split_feature] in node.split_threshold:
                    node = node.left_child
                else:
                    node = node.right_child
            else:
                # 连续特征分割
                if float(x[node.split_feature]) <= node.split_threshold:
                    node = node.left_child
                else:
                    node = node.right_child
        return node.value

    def predict_prob(self, X):
        # 初始预测
        pred = np.full(X.shape[0], self.base_value, dtype=float)

        # 累加所有树的预测
        for tree in self.trees:
            pred += self.learning_rate * self._predict_tree(X, tree)

        # 应用sigmoid函数得到概率
        proba = self._sigmoid(pred)

        # 返回两个类别的概率
        res = np.vstack([1 - proba, proba]).T
        return res[:, 1]

    # def predict(self, X):
    #     proba = self.predict_prob(X)[:, 1]
    #     return np.where(proba >= 0.5, self.classes_[1], self.classes_[0])
