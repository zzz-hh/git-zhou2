from fediux.FL.utils.net_work import MultiGrpcClients
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_json_file,\
                                   save_pickle_file,\
                                   load_pickle_file,\
                                   save_csv_file
from fediux.FL.utils.dataset import read_data
from fediux.utils.logger_util import logger
from fediux.FL.psi import sample_alignment

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_array

from .vfl_base import KmeansHost_Plaintext


class KmeansHost(BaseModel):
    
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
        guest_channel = MultiGrpcClients(local_party=self.role_params['self_name'],
                                         remote_parties=self.roles['guest'],
                                         node_info=self.node_info,
                                         task_info=self.task_info)
        method = self.common_params['method']
        
        # load dataset
        selected_column = self.role_params['selected_column']
        if selected_column is None:
            selected_column = self.role_params.get('selected_column')
        x = read_data(data_info=self.role_params['data'],
                      selected_column=selected_column)
        logger.info(f"x.shape: {x.shape}")

        # psi
        id = self.role_params.get("id")
        psi_protocol = self.common_params.get("psi")
        if isinstance(psi_protocol, str):
            x = sample_alignment(x, id, self.roles, psi_protocol)
        logger.info(f"x.shape: {x.shape}")
        if id in x.columns:
            x = x.drop(id, axis=1)
        logger.info(f"x.columns: {x.columns.values}")
        selected_column = x.columns.values.tolist()
        x = check_array(x, dtype='numeric')
        logger.info(f"x.shape: {x.shape}")

        # 数据标准化
        scaler = StandardScaler()
        x = scaler.fit_transform(x)

        # 获取Kmeans参数
        n_clusters = self.common_params.get('k', 3)
        max_iter = self.common_params.get('max_iter', 100)
        tol = self.common_params.get('tol', 1e-4)

        # 初始化host模型
        if method == 'Plaintext':
            host = Plaintext_Host(x, n_clusters, max_iter, tol, guest_channel)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info("-------- start training --------")
        host.train()
        logger.info("-------- finish training --------")

        save_json_file({"silhouette":host.silhouette_score}, self.role_params['metric_path'])

        # 保存模型
        modelFile = {
            "selected_column": selected_column,
            "id": id,
            "transformer": scaler,
            "model": host.model
        }
        save_pickle_file(modelFile, self.role_params['model_path'])

    def predict(self):
        # setup communication channels
        remote_parties = self.roles[self.role_params['others_role']]
        guest_channel = MultiGrpcClients(local_party=self.role_params['self_name'],
                                         remote_parties=remote_parties,
                                         node_info=self.node_info,
                                         task_info=self.task_info)
        
        # load model
        modelFile = load_pickle_file(self.role_params['model_path'])
        model = modelFile['model']

        # load dataset
        origin_data = read_data(data_info=self.role_params['data'])
        
        x = origin_data.copy()
        selected_column = modelFile['selected_column']
        id = modelFile['id']
        psi_protocol = self.common_params.get("psi","KKRT")
        psi_protocol = "KKRT" if psi_protocol is None else psi_protocol
        logger.info(f"x.shape: {x.shape}")
        if isinstance(psi_protocol, str):
            x = sample_alignment(x, id, self.roles, psi_protocol)
        x1 = x[selected_column]
        x1 = check_array(x1, dtype='numeric')
        
        # 标准化
        transformer = modelFile['transformer']
        x1 = transformer.transform(x1)

        # 计算距离
        host_distances = model._compute_distances(x1)
        logger.info(f"host_distances.shape: {host_distances.shape}")
        guest_distances = guest_channel.recv_all('guest_distances')
        total_distances = host_distances
        for i in range(len(guest_distances)):
            total_distances = total_distances + np.array(guest_distances[i].tolist())
        
        # 预测标签
        pred_labels = model._assign_labels(total_distances)

        # 保存结果
        result = pd.DataFrame({'pred_labels': pred_labels})
        data_result = pd.concat([x, result], axis=1)
        save_csv_file(data_result, self.role_params['predict_path'])

class Plaintext_Host:
    def __init__(self, x, n_clusters, max_iter, tol, guest_channel):
        self.model = KmeansHost_Plaintext(n_clusters, max_iter, tol)
        self.guest_channel = guest_channel
        self.x = x
        # 初始化中心点 
        self.model._init_centers(self.x)

    def train(self):
        for _ in range(self.model.max_iter):
            # 计算本地距离
            host_distances = self.model._compute_distances(self.x)
            
            # 获取guest端距离
            guest_distances = self.guest_channel.recv_all('guest_distances')
            
            # 合并距离
            self.total_distances = host_distances
            for i in range(len(guest_distances)):
                self.total_distances = self.total_distances + np.array(guest_distances[i].tolist())
            
            # 分配标签
            self.labels = self.model._assign_labels(self.total_distances)
            # 分配标签后，将标签发送给guest端
            self.guest_channel.send_all('labels', self.labels)
            
            # 更新中心点
            new_centers = self.model._update_centers(self.x, self.labels)
            
            # 更新中心点后
            center_shift = np.sum((new_centers - self.model.centers) ** 2)
            
            # 获取guest端中心点偏移量
            guest_shift = self.guest_channel.recv_all('center_shift')
            total_shift = center_shift + sum(guest_shift)

            # 检查收敛 (同时考虑host和guest端的变化)
            if total_shift < self.model.tol:
                self.guest_channel.send_all('break_flag', True)
                break
            else:
                self.guest_channel.send_all('break_flag', False)
                
            self.model.centers = new_centers

            self.silhouette_score = self.silhouette()
            logger.info(f"silhouette_score: {self.silhouette_score}")
    
    def silhouette(self):        
        # 计算轮廓系数
        silhouette_scores = []
        for i in range(len(self.x)):
            # 获取当前样本所属的簇
            cluster_idx = self.labels[i]
            
            # 计算a(i): 样本i到同簇其他样本的平均距离
            a_i = self.total_distances[i, cluster_idx]
            
            # 计算b(i): 样本i到其他簇的最小平均距离
            other_clusters = [c for c in range(self.model.n_clusters) if c != cluster_idx]
            b_i = min([self.total_distances[i, c] for c in other_clusters])
            
            # 计算样本i的轮廓系数
            s_i = (b_i - a_i) / max(a_i, b_i)
            silhouette_scores.append(s_i)
        
        return np.mean(silhouette_scores)
