import numpy as np
from math import ceil
import warnings
from scipy import special
from scipy.interpolate import BSpline
from ._power import PowerTransformer as SKL_PowerTransformer
from sklearn.preprocessing import QuantileTransformer as SKL_QuantileTransformer
from sklearn.preprocessing import SplineTransformer as SKL_SplineTransformer
from sklearn.utils import check_array, resample
from .base import _PreprocessBase
from ._power import (
    _yeojohnson_transform,
    boxcox_normmax_client,
    boxcox_normmax_server,
    yeojohnson_normmax_client,
    yeojohnson_normmax_server,
)
from .util import validate_quantile_sketch_params
from ..stats import col_min_max, col_quantile
import pandas as pd


class PowerTransformer(_PreprocessBase):
    def __init__(
        self,
        method="yeo-johnson",
        standardize=True,
        copy=True,
        FL_type=None,
        role=None,
        channel=None,
    ):
        super().__init__(FL_type, role, channel)
        if self.FL_type == "H":
            self.check_channel()
        self.module = SKL_PowerTransformer(
            method=method,
            standardize=standardize,
            copy=copy,
        )

    def Hfit(self, X):
        self._Hfit(X, force_transform=False)
        return self

    def _Hfit(self, X, force_transform=False):
        self.module._validate_params()

        if self.role == "client":
            X = self.module._check_input(X, in_fit=True, check_positive=True)

            if not self.module.copy and not force_transform:  # if call from fit()
                X = X.copy()  # force copy so that fit does not change X inplace

            optim_function = {
                "box-cox": boxcox_normmax_client,
                "yeo-johnson": yeojohnson_normmax_client,
            }[self.module.method]

            transform_function = {
                "box-cox": special.boxcox,
                "yeo-johnson": _yeojohnson_transform,
            }[self.module.method]

            col_num = X.shape[1]
            self.channel.send("col_num", col_num)

            self.module.lambdas_ = np.empty(col_num)
            for i, col in enumerate(X.T):
                mask = np.isnan(col)
                if np.all(mask):
                    raise ValueError("Column must not be all nan.")

                self.module.lambdas_[i] = optim_function(col[~mask], self.channel)

                if self.module.standardize or force_transform:
                    X[:, i] = transform_function(X[:, i], self.module.lambdas_[i])

            if self.module.standardize:
                n_samples = np.repeat(X.shape[0], X.shape[1])
                n_nan = np.isnan(X).sum(axis=0)
                n_samples -= n_nan
                if np.ptp(n_samples) == 0:
                    n_samples = n_samples[0]
                self.channel.send("n_samples", n_samples)

                X_sum = np.nansum(X, axis=0)
                self.channel.send("X_sum", X_sum)
                self.module._mean = self.channel.recv("mean")

                X_sum_square = np.sum(np.square(X / self.module._mean - 1), axis=0)
                self.channel.send("X_sum_square", X_sum_square)
                self.module._scale = self.channel.recv("scale")

                if force_transform:
                    X = (X - self.module._mean) / self.module._scale

            return X

        elif self.role == "server":
            optim_function = {
                "box-cox": boxcox_normmax_server,
                "yeo-johnson": yeojohnson_normmax_server,
            }[self.module.method]

            col_num = self.channel.recv_all("col_num")
            if np.ptp(col_num) != 0:
                raise RuntimeError(f"Not all col_num are equal: {col_num}")
            col_num = col_num[0]

            self.module.lambdas_ = np.empty(col_num)
            for i in range(col_num):
                self.module.lambdas_[i] = optim_function(self.channel)

            if self.module.standardize:
                n_samples = self.channel.recv_all("n_samples")
                # n_samples could be np.int or np.ndarray
                n_sum = 0
                for n in n_samples:
                    n_sum += n
                if isinstance(n_sum, np.ndarray) and np.ptp(n_sum) == 0:
                    n_sum = n_sum[0]

                X_sum = self.channel.recv_all("X_sum")
                self.module._mean = np.sum(X_sum, axis=0) / n_sum
                self.channel.send_all("mean", self.module._mean)

                X_sum_square = self.channel.recv_all("X_sum_square")
                X_sum_square = np.sum(X_sum_square, axis=0)

                self.module._scale = abs(self.module._mean) * np.sqrt(
                    X_sum_square / n_sum
                )
                self.module._scale[self.module._scale == 0] = 1.0
                self.channel.send_all("scale", self.module._scale)

    def fit_transform(self, X):
        if self.FL_type == "V":
            return self.module.fit_transform(X)
        else:
            return self._Hfit(X, force_transform=True)


class QuantileTransformer(_PreprocessBase):
    def __init__(
        self,
        n_quantiles=1000,
        output_distribution="uniform",
        ignore_implicit_zeros=False,
        subsample=10_000,
        random_state=None,
        copy=True,
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
        self.module = SKL_QuantileTransformer(
            n_quantiles=n_quantiles,
            output_distribution=output_distribution,
            ignore_implicit_zeros=ignore_implicit_zeros,
            subsample=subsample,
            random_state=random_state,
            copy=copy,
        )

    def Hfit(self, X):
        self.module._validate_params()
        validate_quantile_sketch_params(self)

        if self.module.n_quantiles > self.module.subsample:
            raise ValueError(
                "The number of quantiles cannot be greater than"
                " the number of samples used. Got {} quantiles"
                " and {} samples.".format(
                    self.module.n_quantiles, self.module.subsample
                )
            )

        if self.role == "client":
            X = self.module._check_inputs(X, in_fit=True, copy=False)
            n_samples = X.shape[0]
            self.channel.send("n_samples", n_samples)
            n_quantiles = self.channel.recv("n_quantiles")

            if n_quantiles < self.module.n_quantiles:
                warnings.warn(
                    "n_quantiles (%s) is greater than the total number "
                    "of samples (%s). n_quantiles is set to "
                    "n_samples." % (self.module.n_quantiles, n_quantiles)
                )

        elif self.role == "server":
            n_samples = sum(self.channel.recv_all("n_samples"))

            if self.module.n_quantiles > n_samples:
                warnings.warn(
                    "n_quantiles (%s) is greater than the total number "
                    "of samples (%s). n_quantiles is set to "
                    "n_samples." % (self.module.n_quantiles, n_samples)
                )
            n_quantiles = max(1, min(self.module.n_quantiles, n_samples))
            self.channel.send_all("n_quantiles", n_quantiles)

        self.module.n_quantiles_ = n_quantiles

        # Create the quantiles of reference
        self.module.references_ = np.linspace(
            0, 1, self.module.n_quantiles_, endpoint=True
        )
        self._dense_fit(X, n_samples)
        return self

    def _dense_fit(self, X, n_samples):
        if self.module.ignore_implicit_zeros:
            warnings.warn(
                "'ignore_implicit_zeros' takes effect only with"
                " sparse matrix. This parameter has no effect."
            )

        if self.role == "client":
            subsample_ratio = self.channel.recv("subsample_ratio")
            if subsample_ratio is not None:
                X = resample(
                    X,
                    replace=False,
                    n_samples=ceil(subsample_ratio * n_samples),
                    random_state=self.module.random_state,
                )

        elif self.role == "server":
            subsample = self.module.subsample
            if n_samples > subsample:
                subsample_ratio = subsample / n_samples
            else:
                subsample_ratio = None
            self.channel.send_all("subsample_ratio", subsample_ratio)

        quantiles = col_quantile(
            role=self.role,
            X=X if self.role == "client" else None,
            quantiles=self.module.references_,
            sketch_name=self.sketch_name,
            k=self.k,
            is_hra=self.is_hra,
            channel=self.channel,
        )
        self.module.quantiles_ = quantiles


class SplineTransformer(_PreprocessBase):
    def __init__(
        self,
        n_knots=5,
        degree=3,
        knots="uniform",
        extrapolation="constant",
        include_bias=True,
        order="C",
        sparse_output=False,
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
        self.module = SKL_SplineTransformer(
            n_knots=n_knots,
            degree=degree,
            knots=knots,
            extrapolation=extrapolation,
            include_bias=include_bias,
            order=order,
            sparse_output=sparse_output,
        )

    def Hfit(self, X):
        self.module._validate_params()
        validate_quantile_sketch_params(self)

        if not isinstance(self.module.knots, str):
            base_knots = check_array(self.module.knots, dtype=np.float64)
            if base_knots.shape[0] < 2:
                raise ValueError("Number of knots, knots.shape[0], must be >= 2.")
            elif not np.all(np.diff(base_knots, axis=0) > 0):
                raise ValueError("knots must be sorted without duplicates.")

        if self.role == "client":
            X = self.module._validate_data(
                X,
                reset=True,
                ensure_min_samples=2,
                ensure_2d=True,
            )

            _, n_features = X.shape

            if isinstance(self.module.knots, str):
                base_knots = self._get_base_knot_positions(X)
            else:
                if base_knots.shape[1] != n_features:
                    raise ValueError("knots.shape[1] == n_features is violated.")

        elif self.role == "server":
            if isinstance(self.module.knots, str):
                base_knots = self._get_base_knot_positions()

            n_features = base_knots.shape[1]

        # number of knots for base interval
        n_knots = base_knots.shape[0]

        if self.module.extrapolation == "periodic" and n_knots <= self.module.degree:
            raise ValueError(
                "Periodic splines require degree < n_knots. Got n_knots="
                f"{n_knots} and degree={self.module.degree}."
            )

        # number of splines basis functions
        if self.module.extrapolation != "periodic":
            n_splines = n_knots + self.module.degree - 1
        else:
            # periodic splines have self.degree less degrees of freedom
            n_splines = n_knots - 1

        degree = self.module.degree
        n_out = n_features * n_splines
        # We have to add degree number of knots below, and degree number knots
        # above the base knots in order to make the spline basis complete.
        if self.module.extrapolation == "periodic":
            # For periodic splines the spacing of the first / last degree knots
            # needs to be a continuation of the spacing of the last / first
            # base knots.
            period = base_knots[-1] - base_knots[0]
            knots = np.r_[
                base_knots[-(degree + 1) : -1] - period,
                base_knots,
                base_knots[1 : (degree + 1)] + period,
            ]

        else:
            # Eilers & Marx in "Flexible smoothing with B-splines and
            # penalties" https://doi.org/10.1214/ss/1038425655 advice
            # against repeating first and last knot several times, which
            # would have inferior behaviour at boundaries if combined with
            # a penalty (hence P-Spline). We follow this advice even if our
            # splines are unpenalized. Meaning we do not:
            # knots = np.r_[
            #     np.tile(base_knots.min(axis=0), reps=[degree, 1]),
            #     base_knots,
            #     np.tile(base_knots.max(axis=0), reps=[degree, 1])
            # ]
            # Instead, we reuse the distance of the 2 fist/last knots.
            dist_min = base_knots[1] - base_knots[0]
            dist_max = base_knots[-1] - base_knots[-2]

            knots = np.r_[
                np.linspace(
                    base_knots[0] - degree * dist_min,
                    base_knots[0] - dist_min,
                    num=degree,
                ),
                base_knots,
                np.linspace(
                    base_knots[-1] + dist_max,
                    base_knots[-1] + degree * dist_max,
                    num=degree,
                ),
            ]

        # With a diagonal coefficient matrix, we get back the spline basis
        # elements, i.e. the design matrix of the spline.
        # Note, BSpline appreciates C-contiguous float64 arrays as c=coef.
        coef = np.eye(n_splines, dtype=np.float64)
        if self.module.extrapolation == "periodic":
            coef = np.concatenate((coef, coef[:degree, :]))

        extrapolate = self.module.extrapolation in ["periodic", "continue"]

        bsplines = [
            BSpline.construct_fast(knots[:, i], coef, degree, extrapolate=extrapolate)
            for i in range(n_features)
        ]
        self.module.bsplines_ = bsplines

        self.module.n_features_out_ = n_out - n_features * (
            1 - self.module.include_bias
        )
        return self

    def _get_base_knot_positions(self, X=None):
        if self.module.knots == "quantile":
            quantiles = np.linspace(
                start=0, stop=1, num=self.module.n_knots, dtype=np.float64
            )
            knots = col_quantile(
                role=self.role,
                X=X if self.role == "client" else None,
                quantiles=quantiles,
                sketch_name=self.sketch_name,
                k=self.k,
                is_hra=self.is_hra,
                channel=self.channel,
            )
            knots = np.transpose(knots)

        else:
            # knots == 'uniform':
            x_min, x_max = col_min_max(
                role=self.role,
                X=X if self.role == "client" else None,
                ignore_nan=False,
                channel=self.channel,
            )

            knots = np.linspace(
                start=x_min,
                stop=x_max,
                num=self.module.n_knots,
                endpoint=True,
                dtype=np.float64,
            )
        return knots


class PCATransformer(_PreprocessBase):
    def __init__(
            self,
            FL_type=None,
            role=None,
            channel=None,
            n_components=2,  # 降维后的维度
            whiten=False  # 是否白化（标准化主成分）
    ):
        super().__init__(FL_type, role, channel)
        self.module = None  # 存储全局PCA参数
        self.n_components = n_components  # 目标维度
        self.whiten = whiten  # 是否白化

        # 客户端本地统计
        self.local_mean = None  # 本地均值
        self.local_cov = None  # 本地协方差矩阵
        self.sample_count = 0  # 本地样本数量
        self.feature_count = 0  # 特征数量
        self.feature_names = []


    def _validate_data(self, X: pd.DataFrame) -> np.ndarray:
        """验证数据有效性，确保为数值型且无缺失值"""
        # 检查是否为数值型数据
        print(X, 9999999999)
        # 检查是否有缺失值
        if X.isnull().any().any():
            raise ValueError("PCA不支持含缺失值的数据，请先进行缺失值填充")
        print(X.dtypes)
        if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in X.dtypes):
            non_numeric_cols = [col for col, dtype in X.dtypes.items()
                                if not pd.api.types.is_numeric_dtype(dtype)]
            raise ValueError(f"PCA仅支持数值型数据，发现非数值列: {non_numeric_cols}")

        return X.values

    def Hfit(self, X):
        self.check_channel()
        X = pd.DataFrame(X)

        # 验证数据并转换为numpy数组
        X_array = self._validate_data(X)
        self.sample_count, self.feature_count = X_array.shape

        if self.role == "client":
            # 检查目标维度是否合理
            if self.n_components < 1 or self.n_components > self.feature_count:
                raise ValueError(f"n_components必须在1到{self.feature_count}之间")
            # 计算本地统计量
            self.local_mean = np.mean(X_array, axis=0)  # 特征均值
            X_centered = X_array - self.local_mean  # 中心化数据

            # 计算本地协方差矩阵（已归一化）
            self.local_cov = (X_centered.T @ X_centered) / (self.sample_count - 1)

            # 发送本地统计到服务器
            local_stats = {
                'mean': self.local_mean,
                'cov': self.local_cov,
                'sample_count': self.sample_count,
                'feature_count': self.feature_count
            }
            self.channel.send("local_stats", local_stats)

            # 接收全局PCA参数
            self.module = self.channel.recv("global_pca_params")

        elif self.role == "server":
            # 接收所有客户端的统计信息
            all_local_stats = self.channel.recv_all("local_stats")

            if not all_local_stats:
                raise ValueError("没有收到任何客户端的统计信息")

            # 检查所有客户端的特征数量是否一致
            feature_counts = {s['feature_count'] for s in all_local_stats}
            if len(feature_counts) > 1:
                raise ValueError("所有客户端的特征数量必须一致")
            feature_count = feature_counts.pop()

            # 检查目标维度是否合理
            if self.n_components < 1 or self.n_components > feature_count:
                raise ValueError(f"n_components必须在1到{feature_count}之间")

            # 聚合全局均值（加权平均）
            total_samples = sum(s['sample_count'] for s in all_local_stats)
            global_mean = np.zeros(feature_count)
            for stats in all_local_stats:
                weight = stats['sample_count'] / total_samples
                global_mean += weight * stats['mean']

            # 聚合全局协方差矩阵
            global_cov = np.zeros((feature_count, feature_count))

            # 第一步：累加每个客户端的协方差贡献
            for stats in all_local_stats:
                n = stats['sample_count']
                global_cov += (n - 1) * stats['cov']

            # 第二步：添加跨客户端均值差异的贡献
            for stats in all_local_stats:
                n = stats['sample_count']
                mean_diff = stats['mean'] - global_mean
                global_cov += n * np.outer(mean_diff, mean_diff)

            # 归一化
            global_cov /= (total_samples - 1)

            # 计算特征值和特征向量（主成分）
            eigenvalues, eigenvectors = np.linalg.eigh(global_cov)

            # 按特征值降序排序
            sorted_indices = np.argsort(eigenvalues)[::-1]
            eigenvalues = eigenvalues[sorted_indices]
            eigenvectors = eigenvectors[:, sorted_indices]

            # 选择前n_components个主成分
            top_eigenvectors = eigenvectors[:, :self.n_components]

            # 计算解释方差比
            explained_variance = eigenvalues[:self.n_components]
            explained_variance_ratio = explained_variance / np.sum(eigenvalues)

            # 准备全局PCA参数
            global_pca_params = {
                'mean': global_mean,
                'components': top_eigenvectors,
                'explained_variance': explained_variance,
                'explained_variance_ratio': explained_variance_ratio,
                'n_components': self.n_components,
                'whiten': self.whiten
            }

            # 发送全局参数到所有客户端
            self.channel.send_all("global_pca_params", global_pca_params)
            self.module = global_pca_params

    def fit_transform(self, X):
        self.Hfit(X)
        return self.transform(X)

    def transform(self, X):
        """将数据投影到主成分上"""
        if self.module is None:
            raise RuntimeError("请先调用fit进行训练")

        X = pd.DataFrame(X)
        X_array = self._validate_data(X)

        # 中心化数据（使用全局均值）
        X_centered = X_array - self.module['mean']

        # 投影到主成分上
        X_transformed = X_centered @ self.module['components']

        # 白化（如果启用）
        if self.module['whiten']:
            # 除以每个主成分的标准差
            stddev = np.sqrt(self.module['explained_variance'])
            X_transformed /= stddev

        # 转换回DataFrame
        columns = [f'pc_{i + 1}' for i in range(self.module['n_components'])]
        self.feature_names = columns
        return pd.DataFrame(X_transformed, columns=columns, index=X.index)

    def get_feature_names_out(self):
        return self.feature_names
