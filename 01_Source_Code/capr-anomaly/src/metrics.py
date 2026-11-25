"""Evaluation metrics. Anomaly = positive class (1)."""
import numpy as np
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score, confusion_matrix,
                             precision_recall_curve, matthews_corrcoef)


def best_f1_threshold(y, score):
    """Threshold maximising F1 -- used for score-only methods, tuned on the labeled train set."""
    if len(np.unique(y)) < 2:
        return float(np.percentile(score, 95))
    p, r, t = precision_recall_curve(y, score)
    f1 = 2 * p * r / np.clip(p + r, 1e-12, None)
    return float(t[np.argmax(f1[:-1])])


def evaluate(y_true, score, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "mcc": matthews_corrcoef(y_true, y_pred),
        "auc_roc": roc_auc_score(y_true, score),
        "auc_pr": average_precision_score(y_true, score),
        "fpr": fp / max(1, fp + tn),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
    }
