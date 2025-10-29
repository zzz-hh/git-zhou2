import torch
from fediux.utils.logger_util import logger
import numpy as np
from scipy.stats import ks_2samp
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    confusion_matrix
)
from collections import Counter
import pandas as pd
import torch

def classification_metrics(y_true,
                           y_score,
                           multiclass=False,
                           prefix="",
                           metrics_name=["acc",
                                         "f1",
                                         "precision",
                                         "recall",
                                         "auc",
                                         "roc",
                                         "ks",
                                         "confusion_matrix",
                                         "bimodal"],):
    metrics = {}

    if multiclass:
        y_pred = np.argmax(y_score, axis=1)
    else:
        y_pred = np.array(y_score > 0.5, dtype='int')

    for name in metrics_name:
        prefix_name = prefix + name
        if name == "acc":
            metrics[prefix_name] = accuracy_score(y_true, y_pred)
        elif name == "f1":
            if multiclass:
                metrics[prefix_name] = f1_score(y_true, y_pred, average="macro", zero_division=0)
            else:
                metrics[prefix_name] = f1_score(y_true, y_pred, average="binary", zero_division=0)
        elif name == "precision":
            if multiclass:
                metrics[prefix_name] = precision_score(y_true, y_pred, average="macro", zero_division=0)
            else:
                metrics[prefix_name] = precision_score(y_true, y_pred, average="binary", zero_division=0)
        elif name == "recall":
            if multiclass:
                metrics[prefix_name] = recall_score(y_true, y_pred, average="macro", zero_division=0)
            else:
                metrics[prefix_name] = recall_score(y_true, y_pred, average="binary", zero_division=0)
        elif name == "auc":
            if multiclass:
                metrics[prefix_name] = roc_auc_score(y_true, y_score, multi_class="ovr")
            else:
                metrics[prefix_name] = roc_auc_score(y_true, y_pred, multi_class="ovr")
        elif name == "roc" and not multiclass:
            fpr, tpr, thresholds = roc_curve(y_true, y_score)
            logger.info("roc curve: fpr: {}, tpr: {}, thresholds: {}".format(fpr, tpr, thresholds))
            # thresholds[0] is np.inf, but is not a valid JSON value
            ks_good = 1 - fpr
            ks_bad = 1 - tpr
            finite_mask = np.isfinite(thresholds)
            if not np.any(finite_mask):
                best_ks = 0.0
                ks_threshold = 1.0          # 或者取一个合理的默认阈值
            else:
                ks_values = np.abs(tpr - fpr)
                ks_values = ks_values[finite_mask]
                ks_index = np.argmax(ks_values)
                best_ks = ks_values[ks_index]
                ks_threshold = float(thresholds[finite_mask][ks_index])
            
            thresholds[0] = thresholds[1] + 1.
            metrics[prefix + "fpr"] = fpr.tolist()
            metrics[prefix + "tpr"] = tpr.tolist()
            metrics[prefix + "thresholds"] = thresholds.tolist()
            metrics[prefix + "ksgood"] = ks_good.tolist()
            metrics[prefix + "ksbad"] = ks_bad.tolist()
            metrics[prefix + "bestks"] = float(best_ks)
            metrics[prefix + "ksthreshold"] = float(ks_threshold)
            
            metrics[prefix + "prp"] = []
            metrics[prefix + "prr"] = []
            for thr in thresholds:
                # y_pred = [1 if scr > thr else 0 for scr in y_score]
                tmp_pred = np.array(y_score > thr, dtype='int')
                precision = precision_score(y_true, tmp_pred, average="binary", zero_division=0)
                recall = recall_score(y_true, tmp_pred, average="binary", zero_division=0)
                metrics[prefix + "prp"].append(float(precision))
                metrics[prefix + "prr"].append(float(recall))
            
            metrics[prefix + "liftv"] = []
            metrics[prefix + "liftp"] = []
            for q in range(0, 101, 10):
                thr = np.percentile(y_score, q)
                tmp_pred = np.array(y_score > thr, dtype='int')
                cm = confusion_matrix(y_true, tmp_pred)
                tp = int(cm[1][1])
                tn = int(cm[0][0])
                fp = int(cm[0][1])
                fn = int(cm[1][0])
                p = tp + fp
                n = tn + fn
                lift = 0.
                try:
                    # 避免除0错误
                    lift = (tp / (tp + fp)) / ((tp + fn) / (p + n))
                except:
                    pass
                metrics[prefix + "liftv"].append(lift)
                metrics[prefix + "liftp"].append(q)
                
            metrics[prefix + "gainv"] = []
            metrics[prefix + "gainp"] = []
            for q in range(0, 101, 10):
                thr = np.percentile(y_score, q)
                tmp_pred = np.array(y_score > thr, dtype='int')
                cm = confusion_matrix(y_true, tmp_pred)
                tp = int(cm[1][1])
                tn = int(cm[0][0])
                fp = int(cm[0][1])
                fn = int(cm[1][0])
                p = tp + fp
                if p == 0:
                    gain = 0.
                else:
                    gain = tp / p
                metrics[prefix + "gainv"].append(gain)
                metrics[prefix + "gainp"].append(q)
        elif name == "ks" and not multiclass:
            pos_idx = y_true == 1
            metrics[prefix_name] = ks_2samp(y_score[pos_idx],
                                            y_score[~pos_idx]).statistic
        elif name == "confusion_matrix":
            cm = confusion_matrix(y_true, y_pred)
            metrics[prefix + "confusion_matrix"] = cm.tolist()
            metrics[prefix + "labels"] = list(range(cm.shape[0]))
        elif name == "bimodal" and not multiclass:
            def cls(tmp_data, category_dict):
                for k in category_dict:
                    if category_dict[k][0] <= tmp_data < category_dict[k][1]:
                        return k
            def cutBins(score):
                # 等距分箱
                bin_count = 100
                bins = np.linspace(0, 1, bin_count + 1)
                bins1 = pd.cut(score, bins=bins, right=False)
                category_dict = {}
                for i, bin in enumerate(bins1.array.categories):
                    category_dict[i] = (float(bin.left), float(bin.right))
                # 统计在不同分箱上占的比例
                score_pd = score.to_frame(name='_y_score')
                score_pd['category'] = -1
                score_pd['category'] = score_pd['_y_score'].apply(lambda x: cls(x, category_dict))
                property_dict = dict(Counter(score_pd['category'].tolist()))
                total = sum(property_dict.values())
                for k in property_dict:
                    property_dict[k] = property_dict[k] / total
                return category_dict, property_dict
            if isinstance(y_score, torch.Tensor):
                _y_score = y_score.cpu().detach().numpy()
                if _y_score.shape[-1] == 1:
                    _y_score = _y_score.squeeze()
            else:
                _y_score = y_score
            score1 = pd.Series(_y_score)
            score0 = 1 - score1
            # 分箱
            category1_dict, property1_dict = cutBins(score1)
            category0_dict, property0_dict = cutBins(score0)
            # 排序返回数据
            metrics[prefix + "bimodalx"] = []
            metrics[prefix + "bimodaly"] = []
            for k in category1_dict.keys():
                metrics[prefix + "bimodalx"].append(category1_dict[k])
                metrics[prefix + "bimodaly"].append(property1_dict.get(k, 0.))

        else:
            raise ValueError(f"Unsupported metrics: {name}")
        
        if name in ["roc", "bimodal"]:
            logger.info(f"{name} is computed but not printed")
        else:
            logger.info(f"{name}: {metrics[prefix_name]}")
        
    return metrics