import numpy as np
from scipy import stats
from sklearn.preprocessing import MaxAbsScaler as SKL_MaxAbsScaler
from sklearn.preprocessing import MinMaxScaler as SKL_MinMaxScaler
from sklearn.preprocessing import Normalizer as SKL_Normalizer
from sklearn.preprocessing import RobustScaler as SKL_RobustScaler
from sklearn.preprocessing import StandardScaler as SKL_StandardScaler
from sklearn.preprocessing._data import _handle_zeros_in_scale, _is_constant_feature
from sklearn.utils.validation import check_array, FLOAT_DTYPES
from .base import _PreprocessBase
from .util import validate_quantile_sketch_params
from ..stats import col_norm, row_norm, col_min_max
from ..sketch import (
    send_local_quantile_sketch,
    merge_local_quantile_sketch,
    get_quantiles,
)
import pandas as pd


class MaxAbsScaler(_PreprocessBase):
    def __init__(self, copy=True, FL_type=None, role=None, channel=None):
        super().__init__(FL_type, role, channel)
        if self.FL_type == "H":
            self.check_channel()
        self.module = SKL_MaxAbsScaler(copy=copy)

    def Hfit(self, X):
        self.module._validate_params()
        if self.role == "client":
            X = self.module._validate_data(
                X,
                dtype=FLOAT_DTYPES,
                force_all_finite="allow-nan",
            )
            self.module.n_samples_seen_ = X.shape[0]

        elif self.role == "server":
            self.module.n_samples_seen_ = None

        max_abs = col_norm(
            role=self.role,
            X=X if self.role == "client" else None,
            norm="max",
            channel=self.channel,
        )

        self.module.max_abs_ = max_abs
        self.module.scale_ = _handle_zeros_in_scale(max_abs)
        return self


class MinMaxScaler(_PreprocessBase):
    def __init__(
        self,
        feature_range=(0, 1),
        copy=True,
        clip=False,
        FL_type=None,
        role=None,
        channel=None,
    ):
        super().__init__(FL_type, role, channel)
        if self.FL_type == "H":
            self.check_channel()
        self.module = SKL_MinMaxScaler(
            feature_range=feature_range, copy=copy, clip=clip
        )

    def Hfit(self, X):
        self.module._validate_params()
        feature_range = self.module.feature_range
        if feature_range[0] >= feature_range[1]:
            raise ValueError(
                "Minimum of desired feature range must be smaller than maximum. Got %s."
                % str(feature_range)
            )

        if self.role == "client":
            X = self.module._validate_data(
                X,
                dtype=FLOAT_DTYPES,
                force_all_finite="allow-nan",
            )
            self.module.n_samples_seen_ = X.shape[0]

        elif self.role == "server":
            self.module.n_samples_seen_ = None

        data_min, data_max = col_min_max(
            role=self.role,
            X=X if self.role == "client" else None,
            channel=self.channel,
        )

        self.module.data_max_ = data_max
        self.module.data_min_ = data_min
        self.module.data_range_ = data_max - data_min
        self.module.scale_ = (
            feature_range[1] - feature_range[0]
        ) / _handle_zeros_in_scale(self.module.data_range_)
        self.module.min_ = feature_range[0] - data_min * self.module.scale_
        return self


class Normalizer(_PreprocessBase):
    def __init__(self, norm="l2", copy=True, FL_type=None, role=None, channel=None):
        super().__init__(FL_type, role, channel)
        if self.FL_type == "V":
            self.check_channel()
        self.module = SKL_Normalizer(norm=norm, copy=copy)

    def fit(self, X):
        self.module.fit(X)
        return self

    def transform(self, X, copy=None):
        if self.FL_type == "H":
            return self.module.transform(X, copy)
        else:
            copy = copy if copy is not None else self.module.copy
            X = self.module._validate_data(X, reset=False)
            X = check_array(
                X,
                copy=copy,
                estimator="the normalize function",
                dtype=FLOAT_DTYPES,
            )

            norms = row_norm(
                role=self.role,
                X=X,
                norm=self.module.norm,
                ignore_nan=False,
                channel=self.channel,
            )

            norms = _handle_zeros_in_scale(norms, copy=False)
            X /= norms[:, np.newaxis]
            return X


class RobustScaler(_PreprocessBase):
    def __init__(
        self,
        with_centering=True,
        with_scaling=True,
        quantile_range=(25.0, 75.0),
        copy=True,
        unit_variance=False,
        sketch_name="KLL",
        k=200,
        is_hra=True,
        FL_type=None,
        role=None,
        channel=None,
    ):
        super().__init__(FL_type, role, channel)
        if self.FL_type == "H":
            self.check_channel()
        self.sketch_name = sketch_name
        self.k = k
        self.is_hra = is_hra
        self.module = SKL_RobustScaler(
            with_centering=with_centering,
            with_scaling=with_scaling,
            quantile_range=quantile_range,
            copy=copy,
            unit_variance=unit_variance,
        )

    def Hfit(self, X):
        self.module._validate_params()
        validate_quantile_sketch_params(self)

        q_min, q_max = self.module.quantile_range
        if not 0 <= q_min <= q_max <= 100:
            raise ValueError(
                "Invalid quantile range: %s" % str(self.module.quantile_range)
            )

        with_centering = self.module.with_centering
        with_scaling = self.module.with_scaling

        if not with_centering:
            center = None

        if not with_scaling:
            scale = None

        if self.role == "client":
            X = self.module._validate_data(
                X,
                dtype=FLOAT_DTYPES,
                force_all_finite="allow-nan",
            )

            if with_centering or with_scaling:
                send_local_quantile_sketch(
                    X,
                    self.channel,
                    sketch_name=self.sketch_name,
                    k=self.k,
                    is_hra=self.is_hra,
                )

                if with_centering and not with_scaling:
                    center = self.channel.recv("center")

                if with_scaling and not with_centering:
                    scale = self.channel.recv("scale")

                if with_centering and with_scaling:
                    center, scale = self.channel.recv("center_scale")

        elif self.role == "server":
            if self.module.with_centering or self.module.with_scaling:
                sketch = merge_local_quantile_sketch(
                    channel=self.channel,
                    sketch_name=self.sketch_name,
                    k=self.k,
                    is_hra=self.is_hra,
                )

                if with_centering:
                    center = get_quantiles(
                        quantiles=0.5,
                        sketch=sketch,
                        sketch_name=self.sketch_name,
                    )

                if with_scaling:
                    quantiles = get_quantiles(
                        quantiles=[q_min / 100.0, q_max / 100.0],
                        sketch=sketch,
                        sketch_name=self.sketch_name,
                    )

                    scale = quantiles[1] - quantiles[0]
                    scale = _handle_zeros_in_scale(scale, copy=False)
                    if self.module.unit_variance:
                        adjust = stats.norm.ppf(q_max / 100.0) - stats.norm.ppf(
                            q_min / 100.0
                        )
                        scale = scale / adjust

                if with_centering and not with_scaling:
                    self.channel.send_all("center", center)

                if with_scaling and not with_centering:
                    self.channel.send_all("scale", scale)

                if with_centering and with_scaling:
                    self.channel.send_all("center_scale", (center, scale))

        self.module.center_ = center
        self.module.scale_ = scale
        return self


class StandardScaler(_PreprocessBase):
    def __init__(
        self,
        copy=True,
        with_mean=True,
        with_std=True,
        FL_type=None,
        role=None,
        channel=None,
    ):
        super().__init__(FL_type, role, channel)
        if self.FL_type == "H":
            self.check_channel()
        self.module = SKL_StandardScaler(
            copy=copy, with_mean=with_mean, with_std=with_std
        )

    def Hfit(self, X):
        self.module._validate_params()
        with_mean = self.module.with_mean
        with_std = self.module.with_std

        if not with_mean:
            mean = None

        var = None
        if not with_std:
            scale = None

        if self.role == "client":
            X = self.module._validate_data(
                X,
                dtype=FLOAT_DTYPES,
                force_all_finite="allow-nan",
            )

            self.module.n_samples_seen_ = np.repeat(X.shape[0], X.shape[1])
            n_nan = np.isnan(X).sum(axis=0)
            self.module.n_samples_seen_ -= n_nan
            # for backward-compatibility, reduce n_samples_seen_ to an integer
            # if the number of samples is the same for each feature (i.e. no
            # missing values)
            if np.ptp(self.module.n_samples_seen_) == 0:
                self.module.n_samples_seen_ = self.module.n_samples_seen_[0]

            if with_mean or with_std:
                self.channel.send("n_samples", self.module.n_samples_seen_)

                X_sum = np.nansum(X, axis=0)
                if with_mean and not with_std:
                    self.channel.send("X_sum", X_sum)
                    mean = self.channel.recv("mean")

                else:  # with_std or (with_mean and with_std)
                    X_sum_square = np.nansum(np.square(X), axis=0)
                    self.channel.send("X_sum_sum_square", [X_sum, X_sum_square])
                    if not with_mean:
                        scale = self.channel.recv("scale")
                    else:
                        mean, scale = self.channel.recv("mean_scale")

        elif self.role == "server":
            self.module.n_samples_seen_ = None

            if with_mean or with_std:
                n_samples = self.channel.recv_all("n_samples")
                # n_samples could be np.int or np.ndarray
                n_sum = 0
                for n in n_samples:
                    n_sum += n
                if isinstance(n_sum, np.ndarray) and np.ptp(n_sum) == 0:
                    n_sum = n_sum[0]
                self.module.n_samples_seen_ = n_sum

                if with_mean and not with_std:
                    X_sum = self.channel.recv_all("X_sum")
                    mean = np.nansum(X_sum, axis=0) / n_sum
                    self.channel.send_all("mean", mean)

                else:  # with_std or (with_mean and with_std)
                    X_sum_sum_square = self.channel.recv_all("X_sum_sum_square")
                    X_sum_sum_square = np.nansum(X_sum_sum_square, axis=0)
                    mean = X_sum_sum_square[0] / n_sum
                    var = (
                        X_sum_sum_square[1] / n_sum - (X_sum_sum_square[0] / n_sum) ** 2
                    )

                    # Extract the list of near constant features on the raw variances,
                    # before taking the square root.
                    constant_mask = _is_constant_feature(var, mean, n_sum)

                    scale = _handle_zeros_in_scale(
                        np.sqrt(var), copy=False, constant_mask=constant_mask
                    )

                    if not with_mean:
                        self.channel.send_all("scale", scale)
                    else:
                        self.channel.send_all("mean_scale", (mean, scale))

        self.module.mean_ = mean
        self.module.var_ = var
        self.module.scale_ = scale
        return self


class OutlierHandler(_PreprocessBase):
    def __init__(
            self,
            FL_type=None,
            role=None,
            channel=None,
            strategy='zscore',  # 异常值检测方法
            threshold=3.0,  # 阈值（zscore的标准差倍数或IQR的倍数）
            method='clip'   # 异常值处理方法
    ):
        super().__init__(FL_type, role, channel)
        self.module = None  # 存储全局异常值边界信息
        self.strategy = strategy  # 异常值检测方法
        self.threshold = threshold  # 异常值判断阈值
        self.numeric_cols = []  # 数值列列表
        self.method = method


    def _validate_data(self, X: pd.DataFrame) -> pd.DataFrame:
        """验证数据有效性，确保为数值型且无缺失值"""
        # 检查是否所有列都是数值型
        if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in X.dtypes):
            non_numeric_cols = [col for col, dtype in X.dtypes.items()
                                if not pd.api.types.is_numeric_dtype(dtype)]
            raise ValueError(f"异常值处理仅支持数值型数据，发现非数值列: {non_numeric_cols}")

        # 检查是否有缺失值
        if X.isnull().any().any():
            missing_cols = [col for col in X.columns if X[col].isnull().any()]
            raise ValueError(f"异常值处理前请先处理缺失值，包含缺失值的列: {missing_cols}")

        self.numeric_cols = X.columns.tolist()
        return X

    def Hfit(self, X):
        self.check_channel()

        if self.role == "client":
            X = pd.DataFrame(X)
            X = self._validate_data(X)
            # 计算本地异常值检测所需的统计量
            local_stats = {
                'column_stats': {}
            }

            for col in self.numeric_cols:
                col_data = X[col].values
                mean = np.mean(col_data)
                std = np.std(col_data)
                q1 = np.percentile(col_data, 25)
                q3 = np.percentile(col_data, 75)
                iqr = q3 - q1

                local_stats['column_stats'][col] = {
                    'mean': mean,
                    'std': std,
                    'q1': q1,
                    'q3': q3,
                    'iqr': iqr,
                    'count': len(col_data)
                }

            self.channel.send("local_stats", local_stats)
            self.module = self.channel.recv("global_outlier_params")

        elif self.role == "server":
            # 接收所有客户端的统计信息
            all_local_stats = self.channel.recv_all("local_stats")

            if not all_local_stats:
                raise ValueError("没有收到任何客户端的统计信息")

            # 聚合全局统计信息，确定异常值边界
            global_params = {
                'column_params': {}
            }

            # 获取所有列名
            all_cols = set()
            for s in all_local_stats:
                all_cols.update(s['column_stats'].keys())
            all_cols = list(all_cols)

            for col in all_cols:
                # 收集所有客户端该列的统计
                col_stats = []
                for client_stats in all_local_stats:
                    if col in client_stats['column_stats']:
                        col_stats.append(client_stats['column_stats'][col])

                if not col_stats:
                    continue

                # 加权聚合均值和标准差（按样本量加权）
                total_count = sum(s['count'] for s in col_stats)
                weighted_mean = sum(s['mean'] * s['count'] for s in col_stats) / total_count
                weighted_std = np.sqrt(sum(
                    (s['std'] ** 2 * (s['count'] - 1) + s['count'] * (s['mean'] - weighted_mean) ** 2)
                    for s in col_stats
                ) / (total_count - 1))

                # 聚合IQR相关统计
                global_q1 = np.median([s['q1'] for s in col_stats])
                global_q3 = np.median([s['q3'] for s in col_stats])
                global_iqr = global_q3 - global_q1

                # 计算异常值边界
                if self.strategy == 'zscore':
                    lower_bound = weighted_mean - self.threshold * weighted_std
                    upper_bound = weighted_mean + self.threshold * weighted_std
                else:  # iqr方法
                    lower_bound = global_q1 - self.threshold * global_iqr
                    upper_bound = global_q3 + self.threshold * global_iqr

                global_params['column_params'][col] = {
                    'mean': weighted_mean,
                    'std': weighted_std,
                    'q1': global_q1,
                    'q3': global_q3,
                    'iqr': global_iqr,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound
                }

            self.channel.send_all("global_outlier_params", global_params)
            self.module = global_params

    def fit_transform(self, X):
        self.Hfit(X)
        return self.transform(X)

    def transform(self, X):
        if self.module is None:
            raise RuntimeError("请先调用fit进行训练")

        for col in self.numeric_cols:
            if col not in self.module['column_params']:
                continue

            col_data = X[col].copy()
            params = self.module['column_params'][col]
            lower = params['lower_bound']
            upper = params['upper_bound']

            # 检测异常值
            is_outlier = (col_data < lower) | (col_data > upper)

            # 处理异常值
            if self.method == 'clip':
                # 截断：将异常值限制在边界上
                col_data = np.clip(col_data, lower, upper)
            elif self.method == 'remove':
                # 移除：将异常值设为NaN（后续需处理）
                col_data[is_outlier] = np.nan
            elif self.method == 'replace':
                # 替换：用边界值或均值替换
                col_data[col_data < lower] = lower
                col_data[col_data > upper] = upper
                # 也可选择用均值替换：col_data[is_outlier] = params['mean']

            X[col] = col_data

        return X


class ValueReplacer(_PreprocessBase):
    """
    联邦学习值替换模块，支持两种替换策略：
    - 特定值替换（replace_specific）：将指定值替换为目标值
    - 范围替换（replace_range）：将指定范围内的值替换为目标值
    """

    def __init__(
            self,
            FL_type=None,
            role=None,
            channel=None,
            strategy='replace_specific',
            replace_map=None,  # 特定值替换映射 {col: {old_val: new_val}}

    ):
        super().__init__(FL_type, role, channel)
        self.module = None  # 存储全局验证信息
        self.strategy = strategy  # 替换策略
        self.replace_map = replace_map if replace_map is not None else {}
        self.numeric_cols = []  # 数值列列表
        self.categorical_cols = []  # 分类列列表

    def _validate_data(self, X: pd.DataFrame) -> pd.DataFrame:
        """验证数据有效性并区分数值/分类列"""
        # 区分数值列和分类列
        self.numeric_cols = [col for col, dtype in X.dtypes.items() if pd.api.types.is_numeric_dtype(dtype)]
        self.categorical_cols = [col for col in X.columns if col not in self.numeric_cols]

        # 策略特定的验证
        if self.strategy == 'replace_specific':
            # 检查替换映射中的列是否存在
            invalid_cols = [col for col in self.replace_map.keys() if col not in X.columns.tolist()]
            if invalid_cols:
                raise ValueError(f"替换映射中包含不存在的列: {invalid_cols}, 列名应属于{X.columns.tolist()}")

        elif self.strategy == 'replace_range':
            # 范围替换仅支持数值列
            invalid_cols = [col for col in self.replace_map.keys() if col not in self.numeric_cols]
            if invalid_cols:
                raise ValueError(f"范围替换仅支持数值列，发现非数值列: {invalid_cols}")

            # 检查范围映射格式是否正确
            for col, range_info in self.replace_map.items():
                if not isinstance(range_info, tuple) or len(range_info) != 3:
                    raise ValueError(f"列 {col} 的范围映射格式错误，应为 (min_val, max_val, new_val)")

        return X

    def Hfit(self, X):
        """联邦学习模式下的训练方法（验证替换规则一致性）"""
        self.check_channel()

        if self.role == "client":
            X = pd.DataFrame(X)
            X = self._validate_data(X)
            # 发送本地替换规则元信息
            local_info = {
                'strategy': self.strategy,
                'columns': X.columns.tolist(),
                'rule_keys': list(self.replace_map.keys())
            }

            self.channel.send("local_info", local_info)
            self.module = self.channel.recv("global_validation")

        elif self.role == "server":
            # 接收所有客户端信息并验证一致性
            all_local_info = self.channel.recv_all("local_info")
            if not all_local_info:
                raise ValueError("没有收到任何客户端的信息")

            # 验证所有客户端策略是否一致
            strategies = {s['strategy'] for s in all_local_info}
            if len(strategies) > 1:
                raise ValueError(f"所有客户端必须使用相同的替换策略，发现策略: {strategies}")

            # 验证替换规则涉及的列是否一致（可选，根据实际需求调整）
            rule_keys_sets = [set(s['rule_keys']) for s in all_local_info]
            if len(set(frozenset(ks) for ks in rule_keys_sets)) > 1:
                raise ValueError(f"所有客户端的替换规则列必须一致，发现差异: {rule_keys_sets}")

            # 发送全局验证结果
            global_validation = {
                'strategy': strategies.pop(),
                'validated': True,
                'message': "所有客户端替换规则验证通过"
            }

            self.channel.send_all("global_validation", global_validation)
            self.module = global_validation

    def fit_transform(self, X):
        self.Hfit(X)
        return self.transform(X)

    def transform(self, X):
        """应用值替换转换"""
        if self.module is None or not self.module.get('validated'):
            raise RuntimeError("请先调用fit_transform完成验证")

        # 根据不同策略执行替换
        if self.strategy == 'replace_specific':
            # 特定值替换
            for col, replace_dict in self.replace_map.items():
                if col not in X.columns:
                    continue
                # 应用替换映射（支持分类和数值列）
                X[col] = X[col].replace(replace_dict)

        elif self.strategy == 'replace_range':
            # 范围替换
            for col, (min_val, max_val, new_val) in self.replace_map.items():
                if col not in X.columns:
                    continue
                # 替换范围内的值（仅数值列）
                mask = (X[col] >= min_val) & (X[col] <= max_val)
                X.loc[mask, col] = new_val

        return X
