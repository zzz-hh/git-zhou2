import numbers
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer as SKL_SimpleImputer
from sklearn.impute._base import _BaseImputer
from sklearn.utils._encode import _unique
from sklearn.utils._mask import _get_mask
from .base import _PreprocessBase
from .util import validate_quantile_sketch_params
from ..sketch import (
    send_local_quantile_sketch,
    merge_local_quantile_sketch,
    get_quantiles,
    send_local_fi_sketch,
    merge_local_fi_sketch,
    get_frequent_items,
)


class SimpleImputer(_PreprocessBase, _BaseImputer):
    def __init__(
        self,
        missing_values=np.nan,
        strategy="mean",
        fill_value=None,
        copy=True,
        add_indicator=False,
        keep_empty_features=False,
        sketch_name="KLL",
        k=200,
        is_hra=True,
        FL_type=None,
        role=None,
        channel=None,
    ):
        super().__init__(FL_type, role, channel)
        if self.FL_type == "H" and strategy != "constant":
            self.check_channel()
        self.sketch_name = sketch_name
        self.k = k
        self.is_hra = is_hra
        self.module = SKL_SimpleImputer(
            missing_values=missing_values,
            strategy=strategy,
            fill_value=fill_value,
            copy=copy,
            add_indicator=add_indicator,
            keep_empty_features=keep_empty_features,
        )
        if FL_type == "H":
            self.missing_values = missing_values
            self.strategy = strategy
            self.copy = copy
            self.add_indicator = add_indicator

    def Hfit(self, X):
        self.module._validate_params()
        validate_quantile_sketch_params(self)

        if self.role == "client":
            X = self.module._validate_input(X, in_fit=True)

            # default fill_value is 0 for numerical input and "missing_value"
            # otherwise
            if self.module.fill_value is None:
                if X.dtype.kind in ("i", "u", "f"):
                    fill_value = 0
                else:
                    fill_value = "missing_value"
            else:
                fill_value = self.module.fill_value

            # fill_value should be numerical in case of numerical input
            if (
                self.module.strategy == "constant"
                and X.dtype.kind in ("i", "u", "f")
                and not isinstance(fill_value, numbers.Real)
            ):
                raise ValueError(
                    "'fill_value'={0} is invalid. Expected a "
                    "numerical value when imputing numerical "
                    "data".format(fill_value)
                )

        elif self.role == "server":
            fill_value = self.module.fill_value

        self.module.statistics_ = self._dense_fit(X, self.module.strategy, fill_value)
        return self

    def _dense_fit(self, X, strategy, fill_value):
        """Fit the transformer on dense data."""
        if self.role == "client":
            missing_mask = _get_mask(X, self.missing_values)
            masked_X = np.ma.masked_array(X, mask=missing_mask)

            super()._fit_indicator(missing_mask)
            self.module.indicator_ = self.indicator_

        # Mean
        if strategy == "mean":
            if self.role == "client":
                sum_masked = np.ma.sum(masked_X, axis=0)
                self.channel.send("sum_masked", sum_masked)

                n_samples = X.shape[0] - np.sum(missing_mask, axis=0)
                # for backward-compatibility, reduce n_samples to an integer
                # if the number of samples is the same for each feature (i.e. no
                # missing values)
                if np.ptp(n_samples) == 0:
                    n_samples = n_samples[0]
                self.channel.send("n_samples", n_samples)
                mean = self.channel.recv("mean")

            elif self.role == "server":
                sum_masked = self.channel.recv_all("sum_masked")
                sum_masked = np.ma.sum(sum_masked, axis=0)

                n_samples = self.channel.recv_all("n_samples")
                # n_samples could be np.int or np.ndarray
                n_sum = 0
                for n in n_samples:
                    n_sum += n
                if isinstance(n_sum, np.ndarray) and np.ptp(n_sum) == 0:
                    n_sum = n_sum[0]

                mean_masked = sum_masked / n_sum
                # Avoid the warning "Warning: converting a masked element to nan."
                mean = np.ma.getdata(mean_masked)
                mean[np.ma.getmask(mean_masked)] = (
                    0 if self.module.keep_empty_features else np.nan
                )
                self.channel.send_all("mean", mean)
            return mean

        # Median
        elif strategy == "median":
            if self.role == "client":
                send_local_quantile_sketch(
                    masked_X,
                    self.channel,
                    sketch_name=self.sketch_name,
                    k=self.k,
                    is_hra=self.is_hra,
                )
                median = self.channel.recv("median")

            elif self.role == "server":
                sketch = merge_local_quantile_sketch(
                    channel=self.channel,
                    sketch_name=self.sketch_name,
                    k=self.k,
                    is_hra=self.is_hra,
                )

                if self.sketch_name == "KLL":
                    mask = sketch.is_empty()
                elif self.sketch_name == "REQ":
                    mask = [col_sketch.is_empty() for col_sketch in sketch]

                if not any(mask):
                    median = get_quantiles(
                        quantiles=0.5,
                        sketch=sketch,
                        sketch_name=self.sketch_name,
                    )
                else:
                    median = np.zeros_like(mask, dtype=float)
                    idx = [i for i, x in enumerate(mask) if not x]
                    if self.sketch_name == "KLL":
                        median[idx] = sketch.get_quantiles(0.5, isk=idx).reshape(-1)
                    elif self.sketch_name == "REQ":
                        for i in idx:
                            median[i] = sketch[i].get_quantile(0.5)
                    median[mask] = 0 if self.module.keep_empty_features else np.nan

                self.channel.send_all("median", median)
            return median

        # Most frequent
        elif strategy == "most_frequent":
            if self.role == "client":
                items, counts = [], []
                for col, col_mask in zip(X.T, missing_mask.T):
                    col = col[~col_mask]
                    if len(col) == 0:
                        items.append([])
                        counts.append([])
                    else:
                        col_items, col_counts = _unique(col, return_counts=True)
                        items.append(col_items)
                        counts.append(col_counts)

                send_local_fi_sketch(items, counts, channel=self.channel, k=self.k)
                most_frequent = self.channel.recv("most_frequent")

            elif self.role == "server":
                sketch = merge_local_fi_sketch(
                    channel=self.channel,
                    k=self.k,
                )

                mask = [col_sketch.is_empty() for col_sketch in sketch]
                if not any(mask):
                    most_frequent, _ = get_frequent_items(
                        sketch=sketch,
                        error_type="NFP",
                        max_item=1,
                    )
                    most_frequent = np.array(most_frequent, dtype=object).reshape(-1)
                else:
                    most_frequent = np.empty(len(sketch), dtype=object)
                    for i, empty in enumerate(mask):
                        if empty:
                            most_frequent[i] = (
                                0 if self.module.keep_empty_features else np.nan
                            )
                        else:
                            item, _ = get_frequent_items(
                                sketch[i],
                                error_type="NFP",
                                max_item=1,
                                vector=False,
                            )
                            most_frequent[i] = item[0]
                self.channel.send_all("most_frequent", most_frequent)
            return most_frequent

        # Constant
        elif strategy == "constant":
            if self.role == "client":
                # for constant strategy, self.statistcs_ is used to store
                # fill_value in each column
                return np.full(X.shape[1], fill_value, dtype=X.dtype)
            elif self.role == "server":
                return fill_value


class InterpolateImputer(_PreprocessBase, _BaseImputer):
    def __init__(
        self,
        FL_type=None,
        role=None,
        channel=None,
    ):
        super().__init__(FL_type, role, channel)
        self.module = None  # 存储全局趋势信息
        self.numeric_cols = []  # 数值列列表
        self.non_numeric_cols = []  # 非数值列列表
        self.col_missing_stats = {}  # 列缺失统计
        self.non_numeric_has_missing = False  # 非数值列是否有缺失
        self.valid_data = {}  # 各列有效数据 {col: (indices, values)}

    def _calculate_column_missing_stats(self, X: pd.DataFrame):
        """计算每列的缺失值统计"""
        stats = {}
        for col in X.columns:
            col_data = X[col]
            missing_count = col_data.isnull().sum()
            total_count = len(col_data)
            stats[col] = {
                'missing_count': missing_count,
                'total_count': total_count,
                'missing_ratio': missing_count / total_count if total_count > 0 else 0.0,
                'has_missing': missing_count > 0
            }
        return stats

    def Hfit(self, X):
        self.check_channel()

        if self.role == "client":
            X = pd.DataFrame(X)
            # 区分数值列和非数值列
            self.numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
            self.non_numeric_cols = [col for col in X.columns if col not in self.numeric_cols]
            # 计算列缺失统计
            self.col_missing_stats = self._calculate_column_missing_stats(X)

            # 检查非数值列是否有缺失
            self.non_numeric_has_missing = any(
                self.col_missing_stats[col]['has_missing']
                for col in self.non_numeric_cols
            )
            # 收集各列有效数据
            for col in self.numeric_cols:
                valid_series = X[col].dropna()
                self.valid_data[col] = (
                    valid_series.index.tolist(),
                    valid_series.values.tolist()
                )
            # 非数值列有缺失时发送空结果
            if self.non_numeric_has_missing:
                self.channel.send("local_stats", None)
                self.module = self.channel.recv("global_stats")
                return
            # 计算本地统计
            local_stats = {
                'numeric_cols': self.numeric_cols,
                'col_stats': {}
            }

            for col in self.numeric_cols:
                indices, values = self.valid_data[col]
                n_valid = len(indices)

                if n_valid == 0:
                    col_stats = {
                        'n_valid': 0,
                        'min_val': None,
                        'max_val': None,
                        'sorted_pairs': []
                    }
                else:
                    min_val = np.min(values)
                    max_val = np.max(values)
                    # 按索引排序的(索引, 值)对
                    sorted_pairs = sorted(zip(indices, values), key=lambda x: x[0])

                    col_stats = {
                        'n_valid': n_valid,
                        'min_val': min_val,
                        'max_val': max_val,
                        'sorted_pairs': sorted_pairs
                    }

                local_stats['col_stats'][col] = col_stats

                local_stats['col_stats'][col] = col_stats

            self.channel.send("local_stats", local_stats)
            self.module = self.channel.recv("global_stats")

        elif self.role == "server":
            # 接收所有客户端统计
            all_local_stats = self.channel.recv_all("local_stats")
            # 过滤无效统计（非数值列有缺失的客户端）
            valid_local_stats = [s for s in all_local_stats if s is not None]

            if not valid_local_stats:
                raise ValueError("所有客户端都存在含缺失值的非数值列，无法继续处理")

            # 收集所有数值列
            all_numeric_cols = set()
            for stats in valid_local_stats:
                all_numeric_cols.update(stats['numeric_cols'])
            all_numeric_cols = list(all_numeric_cols)

            # 计算全局统计
            global_stats = {
                'numeric_cols': all_numeric_cols,
                'col_stats': {}
            }

            for col in all_numeric_cols:
                # 收集该列的所有客户端统计
                col_stats_list = []
                for client_stats in valid_local_stats:
                    if col in client_stats['col_stats']:
                        col_stats_list.append(client_stats['col_stats'][col])

                if not col_stats_list:
                    continue

                # 聚合统计信息
                valid_col_stats = [s for s in col_stats_list if s['n_valid'] > 0]
                total_valid = sum(s['n_valid'] for s in valid_col_stats)

                if total_valid == 0:
                    col_global = {
                        'global_mean': None,
                        'global_min': None,
                        'global_max': None,
                        'avg_slope': 0.0,
                        'total_valid': 0
                    }
                else:
                    # 收集所有值和点对
                    all_values = []
                    all_pairs = []
                    for stats in valid_col_stats:
                        all_values.extend([p[1] for p in stats['sorted_pairs']])
                        all_pairs.extend(stats['sorted_pairs'])

                    # 计算全局统计量
                    global_mean = np.mean(all_values)
                    global_min = min(s['min_val'] for s in valid_col_stats)
                    global_max = max(s['max_val'] for s in valid_col_stats)

                    # 计算平均斜率
                    all_pairs_sorted = sorted(all_pairs, key=lambda x: x[0])
                    slopes = []
                    for i in range(len(all_pairs_sorted) - 1):
                        idx1, val1 = all_pairs_sorted[i]
                        idx2, val2 = all_pairs_sorted[i + 1]
                        if idx2 > idx1:
                            slopes.append((val2 - val1) / (idx2 - idx1))

                    avg_slope = np.mean(slopes) if slopes else 0.0

                    col_global = {
                        'global_mean': global_mean,
                        'global_min': global_min,
                        'global_max': global_max,
                        'avg_slope': avg_slope,
                        'total_valid': total_valid
                    }

                global_stats['col_stats'][col] = col_global

            self.channel.send_all("global_stats", global_stats)

    def _find_nearest_valid(self, col: str, idx: int, before: bool):
        """找到指定列中指定索引前后最近的有效数据点"""
        if col not in self.valid_data:
            return None, None

        indices, values = self.valid_data[col]
        if before:
            # 查找前面最近的有效索引
            candidates = [i for i in indices if i < idx]
            if not candidates:
                return None, None
            nearest_idx = max(candidates)
        else:
            # 查找后面最近的有效索引
            candidates = [i for i in indices if i > idx]
            if not candidates:
                return None, None
            nearest_idx = min(candidates)

        # 找到对应的值
        val_idx = indices.index(nearest_idx)
        return nearest_idx, values[val_idx]

    def _linear_interpolation(self, prev_idx: int, prev_val: float,
                              next_idx: int, next_val: float, curr_idx: int):
        """线性插值计算"""
        ratio = (curr_idx - prev_idx) / (next_idx - prev_idx)
        return prev_val + ratio * (next_val - prev_val)

    def _extrapolate_forward(self, prev_idx: int, prev_val: float,
                             curr_idx: int, col: str):
        """基于前值和全局斜率外推"""
        distance = curr_idx - prev_idx
        return prev_val + distance * self.module['col_stats'][col]['avg_slope']

    def _extrapolate_backward(self, next_idx: int, next_val: float,
                              curr_idx: int, col: str):
        """基于后值和全局斜率外推"""
        distance = next_idx - curr_idx
        return next_val - distance * self.module['col_stats'][col]['avg_slope']

    def fit_transform(self, X):
        self.Hfit(X)
        return self.transform(X)

    def transform(self, X):
        # 非数值列有缺失时直接返回原始数据
        if self.non_numeric_has_missing:
            return X

        # 没有全局统计信息时直接返回
        if self.module is None:
            return X

        # 仅处理数值列
        for col in self.numeric_cols:
            # 跳过无缺失值的列
            if not self.col_missing_stats[col]['has_missing']:
                continue

            # 跳过没有全局统计的列
            if col not in self.module['col_stats']:
                continue

            col_data = X[col].copy()
            missing_indices = col_data[col_data.isna()].index.tolist()
            col_global = self.module['col_stats'][col]

            # 处理每个缺失值
            for idx in missing_indices:
                prev_idx, prev_val = self._find_nearest_valid(col, idx, before=True)
                next_idx, next_val = self._find_nearest_valid(col, idx, before=False)

                # 确定插值方式
                if prev_idx is not None and next_idx is not None:
                    # 线性插值
                    interpolated = self._linear_interpolation(prev_idx, prev_val,
                                                              next_idx, next_val, idx)
                elif prev_idx is not None:
                    # 向前外推
                    interpolated = self._extrapolate_forward(prev_idx, prev_val, idx, col)
                elif next_idx is not None:
                    # 向后外推
                    interpolated = self._extrapolate_backward(next_idx, next_val, idx, col)
                else:
                    # 无有效数据，使用全局均值
                    interpolated = col_global['global_mean']

                # 确保值在合理范围内
                if col_global['global_min'] is not None and col_global['global_max'] is not None:
                    interpolated = np.clip(interpolated,
                                           col_global['global_min'],
                                           col_global['global_max'])

                col_data[idx] = interpolated

            X[col] = col_data

        return X


class BFImputer(_PreprocessBase, _BaseImputer):
    def __init__(
            self,
            FL_type=None,
            role=None,
            channel=None,
            strategy='forward'
    ):
        super().__init__(FL_type, role, channel)
        self.module = None  # 存储全局统计信息
        self.strategy = strategy  # 填充策略：向前或向后
        self.numeric_cols = []  # 数值列列表
        self.non_numeric_cols = []  # 非数值列列表
        self.col_missing_stats = {}  # 列缺失统计
        self.non_numeric_has_missing = False  # 非数值列是否有缺失
        self.valid_data = {}  # 各列有效数据 {col: (indices, values)}

    def _calculate_column_missing_stats(self, X: pd.DataFrame):
        """计算每列的缺失值统计"""
        stats = {}
        for col in X.columns:
            col_data = X[col]
            missing_count = col_data.isnull().sum()
            total_count = len(col_data)
            stats[col] = {
                'missing_count': missing_count,
                'total_count': total_count,
                'missing_ratio': missing_count / total_count if total_count > 0 else 0.0,
                'has_missing': missing_count > 0
            }
        return stats

    def Hfit(self, X):
        self.check_channel()

        if self.role == "client":
            X = pd.DataFrame(X)

            # 区分数值列和非数值列
            self.numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
            self.non_numeric_cols = [col for col in X.columns if col not in self.numeric_cols]

            # 计算列缺失统计
            self.col_missing_stats = self._calculate_column_missing_stats(X)

            # 检查非数值列是否有缺失
            self.non_numeric_has_missing = any(
                self.col_missing_stats[col]['has_missing']
                for col in self.non_numeric_cols
            )

            # 收集各列有效数据
            for col in self.numeric_cols:
                valid_series = X[col].dropna()
                self.valid_data[col] = (
                    valid_series.index.tolist(),
                    valid_series.values.tolist()
                )
            # 非数值列有缺失时发送空结果
            if self.non_numeric_has_missing:
                self.channel.send("local_stats", None)
                self.module = self.channel.recv("global_stats")
                return

            # 计算本地统计
            local_stats = {
                'numeric_cols': self.numeric_cols,
                'col_stats': {}
            }

            for col in self.numeric_cols:
                indices, values = self.valid_data[col]
                n_valid = len(indices)
                total_count = len(X[col])

                if n_valid == 0:
                    col_stats = {
                        'n_valid': 0,
                        'first_valid_value': None,
                        'last_valid_value': None,
                        'value_density': 0.0
                    }
                else:
                    # 首个和最后一个有效值
                    first_valid_value = values[0]
                    last_valid_value = values[-1]

                    col_stats = {
                        'n_valid': n_valid,
                        'first_valid_value': first_valid_value,
                        'last_valid_value': last_valid_value,
                        'value_density': n_valid / total_count if total_count > 0 else 0.0
                    }

                local_stats['col_stats'][col] = col_stats

            self.channel.send("local_stats", local_stats)
            self.module = self.channel.recv("global_stats")

        elif self.role == "server":
            # 接收所有客户端统计
            all_local_stats = self.channel.recv_all("local_stats")
            # 过滤无效统计（非数值列有缺失的客户端）
            valid_local_stats = [s for s in all_local_stats if s is not None]

            if not valid_local_stats:
                raise ValueError("所有客户端都存在含缺失值的非数值列，无法继续处理")

            # 收集所有数值列
            all_numeric_cols = set()
            for stats in valid_local_stats:
                all_numeric_cols.update(stats['numeric_cols'])
            all_numeric_cols = list(all_numeric_cols)

            # 计算全局统计
            global_stats = {
                'numeric_cols': all_numeric_cols,
                'col_stats': {}
            }

            for col in all_numeric_cols:
                # 收集该列的所有客户端统计
                col_stats_list = []
                for client_stats in valid_local_stats:
                    if col in client_stats['col_stats']:
                        col_stats_list.append(client_stats['col_stats'][col])

                if not col_stats_list:
                    continue

                # 聚合有效统计信息
                valid_col_stats = [s for s in col_stats_list if s['n_valid'] > 0]
                if not valid_col_stats:
                    global_stats['col_stats'][col] = {
                        'avg_first_valid': None,
                        'avg_last_valid': None,
                        'total_valid': 0,
                        'avg_value_density': 0.0
                    }
                    continue

                # 计算列级全局统计
                total_valid = sum(s['n_valid'] for s in valid_col_stats)
                avg_first_valid = np.mean([s['first_valid_value'] for s in valid_col_stats])
                avg_last_valid = np.mean([s['last_valid_value'] for s in valid_col_stats])
                avg_value_density = np.mean([s['value_density'] for s in valid_col_stats])

                global_stats['col_stats'][col] = {
                    'avg_first_valid': avg_first_valid,
                    'avg_last_valid': avg_last_valid,
                    'total_valid': total_valid,
                    'avg_value_density': avg_value_density
                }

            self.channel.send_all("global_stats", global_stats)

    def fit_transform(self, X):
        self.Hfit(X)
        return self.transform(X)

    def transform(self, X):

        # 非数值列有缺失时直接返回原始数据
        if self.non_numeric_has_missing:
            return X

        # 没有全局统计信息时直接返回
        if self.module is None:
            return X

        # 仅处理数值列
        for col in self.numeric_cols:
            # 跳过无缺失值的列
            if not self.col_missing_stats[col]['has_missing']:
                continue

            # 跳过没有全局统计的列
            if col not in self.module['col_stats']:
                continue

            col_data = X[col].copy()
            col_global = self.module['col_stats'][col]

            # 执行前后填充
            if self.strategy == 'forward':
                # 向前填充（使用前一个有效值）
                col_data = col_data.ffill()
            elif self.strategy == 'backward':
                # 向后填充（使用后一个有效值）
                col_data = col_data.bfill()
            else:
                raise ValueError("填充策略必须是 'forward' 或 'backward'")

            # 处理仍存在的缺失值（边界连续缺失）
            remaining_missing = col_data.isnull()
            if remaining_missing.any():
                # 根据填充策略选择合适的全局补充值
                if self.strategy == 'forward':
                    # 向前填充后仍有缺失，说明数据开头有缺失
                    fill_value = col_global['avg_first_valid']
                else:
                    # 向后填充后仍有缺失，说明数据结尾有缺失
                    fill_value = col_global['avg_last_valid']

                # 若全局值仍为None，使用0填充（最后的备选方案）
                if fill_value is None:
                    fill_value = 0.0

                col_data[remaining_missing] = fill_value

            X[col] = col_data

        return X
