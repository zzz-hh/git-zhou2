import numpy as np
from fediux.FL.utils.net_work import GrpcClient
from fediux.FL.utils.base import BaseModel
from fediux.FL.utils.file import save_pickle_file, load_pickle_file
from fediux.FL.utils.dataset import read_data
from fediux.utils.logger_util import logger
from fediux.FL.psi import sample_alignment

from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_array

from .vfl_base import KmeansGuest_Plaintext


class KmeansGuest(BaseModel):
    
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
        host_channel = GrpcClient(local_party=self.role_params['self_name'],
                                  remote_party=self.roles['host'],
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

        # 初始化guest模型
        n_clusters = self.common_params.get('k', 3)
        max_iter = self.common_params.get('max_iter', 100)
        if method == 'Plaintext':
            guest = Plaintext_Guest(x, n_clusters, max_iter, host_channel)
        else:
            error_msg = f"Unsupported method: {method}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info("-------- start training --------")
        guest.train()
        logger.info("-------- finish training --------")

        # 保存模型
        modelFile = {
            "selected_column": selected_column,
            "id": id,
            "transformer": scaler,
            "model": guest.model
        }
        save_pickle_file(modelFile, self.role_params['model_path'])

    def predict(self):
        # setup communication channels
        remote_party = self.roles[self.role_params['others_role']]
        host_channel = GrpcClient(local_party=self.role_params['self_name'],
                                  remote_party=remote_party,
                                  node_info=self.node_info,
                                  task_info=self.task_info)
        
        # load model
        modelFile = load_pickle_file(self.role_params['model_path'])
        model = modelFile['model']
        selected_column = modelFile['selected_column']

        # load dataset
        origin_data = read_data(data_info=self.role_params['data'])
        
        x = origin_data.copy()
        # 数据预处理
        selected_column = modelFile['selected_column']
        id = modelFile['id']
        psi_protocol = self.common_params.get("psi","KKRT")
        psi_protocol = "KKRT" if psi_protocol is None else psi_protocol
        if isinstance(psi_protocol, str):
            x = sample_alignment(x, id, self.roles, psi_protocol)
        x = x[selected_column]
        x = check_array(x, dtype='numeric')
        
        # 标准化
        transformer = modelFile['transformer']
        x = transformer.transform(x)

        # 计算并发送距离
        distances = model._compute_distances(x)
        host_channel.send('guest_distances', distances)


class Plaintext_Guest:
    def __init__(self, x, n_clusters, max_iter, host_channel):
        self.host_channel = host_channel
        self.x = x  # 保存训练数据
        self.model = KmeansGuest_Plaintext(n_clusters, max_iter)
        # 初始化中心点
        self.model._init_centers(self.x)
        logger.info(f"centers: {self.model.centers}")

    def compute_distances(self):
        # 计算本地距离并发送给host
        distances = self.model._compute_distances(self.x)
        self.host_channel.send('guest_distances', distances)

    def train(self):
        for _ in range(self.model.max_iter):
            # 只需要计算并发送距离，中心点更新由host负责
            self.compute_distances()

            labels = self.host_channel.recv('labels')
            # 更新中心点
            new_centers = self.model._update_centers(self.x, labels)
            center_shift = np.sum((new_centers - self.model.centers) ** 2)

            self.host_channel.send('center_shift', center_shift)
            logger.info(f"new_centers: {new_centers}")
            self.model.centers = new_centers

            break_flag = self.host_channel.recv('break_flag')
            if break_flag:
                break

