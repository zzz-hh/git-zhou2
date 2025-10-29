# _*_ coding: utf-8 _*_
import numpy as np
from sklearn.cluster import KMeans
from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file,\
                                   save_pickle_file,\
                                   load_pickle_file,\
                                   save_csv_file
from fediux.FL.utils.dataset import read_data
from fediux.FL.preprocessing import StandardScaler
from fediux.utils.logger_util import logger
import pandas as pd
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score


class KmeansClient(BaseModel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        process = self.common_params['process']
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
        if id in df.columns:
            df.pop(id)
        df.dropna(inplace=True)
        x = df.values  # 转换为numpy数组

        # data preprocessing
        scaler = StandardScaler(FL_type='H',
                                role=self.role_params['self_role'],
                                channel=server_channel)
        x = scaler.fit_transform(x)

        # client 初始化
        method = self.common_params['method']
        if method == 'Plaintext':
            client = Plaintext_Kmeans_Client(x, self.common_params, server_channel)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # client training
        logger.info("-------- start training --------")
        global_epoch = self.common_params['global_epoch']
        for i in range(global_epoch):
            logger.info(f"-------- global epoch {i+1} / {global_epoch} --------")
            client.fit()
            client.train()

            # print metrics
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
            "preprocess": scaler.module,
            "model": client.k_points
        }
        save_pickle_file(modelFile, self.role_params['model_path'])

    def predict(self):
        # load model for prediction
        modelFile = load_pickle_file(self.role_params['model_path'])

        # load dataset
        selected_column = modelFile['selected_column']
        df = read_data(data_info=self.role_params['data'])
        df.dropna(inplace=True)
        x = df[selected_column].values  # 转换为numpy数组

        # data preprocessing
        scaler = modelFile['preprocess']
        x = scaler.transform(x)
        
        k_points = modelFile['model']
        
        distances = np.linalg.norm(x[:, np.newaxis] - k_points, axis=2)
        
        # 获取每个样本的最近簇索引
        cluster_assignments = np.argmin(distances, axis=1)
        
        # 计算到最近中心的距离
        min_distances = np.min(distances, axis=1)
        
        # 保存预测结果
        result = pd.DataFrame({
            'cluster': cluster_assignments,
            'distance': min_distances
        })
        
        data_result = pd.concat([df, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])


class Plaintext_Kmeans_Client:

    def __init__(self, x, common_params, server_channel):
        self.k = common_params['k']
        self.data = x
        self.max_iter = common_params['max_iter']
        self.server_channel = server_channel
        self.num_examples = self.data.shape[0]

        if self.k > self.num_examples:
            logger.error(f"k cannot be greater than the number of examples: {self.num_examples}")
            raise ValueError("k cannot be greater than the number of examples")
        self.init_k_points()
        self.send_params()

    def init_k_points(self):
        # 随机选择k个初始中心点
        indices = np.random.choice(self.num_examples, self.k, replace=False)
        self.k_points = self.data[indices]

    def fit(self):
        kmeans = KMeans(
            n_clusters=self.k,
            init=self.k_points,  # 使用当前中心点作为初始值
            n_init=1,  # 只运行一次初始化
            random_state=self.num_examples,
            max_iter=self.max_iter, 
        )
        
        # 执行聚类
        kmeans.fit(self.data)
        
        # 更新中心点
        self.k_points = kmeans.cluster_centers_
        
        # 计算总距离并记录日志
        total_distance = np.sum(kmeans.transform(self.data).min(axis=1))
        logger.info(f"Total distance to centroids: {total_distance}")

    def recv_server_model(self):
        return self.server_channel.recv("server_model")

    def get_model(self):
        return self.k_points

    def set_model(self, model):
        self.k_points = model.copy()

    def send_params(self):
        # send other params to compute aggregated metrics
        self.server_channel.send('num_examples', self.num_examples)

    def train(self):
        self.server_channel.send("client_model", self.get_model())
        self.set_model(self.recv_server_model())

    def silhouette(self):
        # 计算每个样本到所有中心的距离
        distances = np.linalg.norm(self.data[:, np.newaxis] - self.k_points, axis=2)
        
        # 获取每个样本的簇分配
        cluster_assignments = np.argmin(distances, axis=1)
        
        # 计算轮廓系数
        silhouette_scores = []
        for i, point in enumerate(self.data):
            # 获取当前样本所属的簇
            cluster_idx = cluster_assignments[i]
            
            # 计算a(i): 样本i到同簇其他样本的平均距离
            same_cluster = self.data[cluster_assignments == cluster_idx]
            a_i = np.mean(np.linalg.norm(same_cluster - point, axis=1))
            
            # 计算b(i): 样本i到其他簇的最小平均距离
            other_clusters = [c for c in range(self.k) if c != cluster_idx]
            b_i = min([
                np.mean(np.linalg.norm(self.data[cluster_assignments == c] - point, axis=1))
                for c in other_clusters
            ])
            
            # 计算样本i的轮廓系数
            s_i = (b_i - a_i) / max(a_i, b_i)
            # logger.info(f"silhouette_score: {s_i}")
            silhouette_scores.append(s_i)
            
        return np.mean(silhouette_scores)

    def send_metrics(self):
        silhouette_score = self.silhouette()
        self.server_channel.send("silhouette", silhouette_score)
        return {"silhouette": silhouette_score}

    def print_metrics(self):
        silhouette_score = self.silhouette()
        self.server_channel.send("silhouette", silhouette_score)
        logger.info(f"silhouette: {silhouette_score}")

