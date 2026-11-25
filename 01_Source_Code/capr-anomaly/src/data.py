"""Data pipeline for encrypted-traffic anomaly detection."""
import glob
import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from .utils import log

ID_COLUMNS = {
    "flow id", "flow_id", "src ip", "source ip", "src_ip", "dst ip", "destination ip",
    "dst_ip", "src port", "source port", "src_port", "dst port", "destination port",
    "dst_port", "timestamp", "protocol", "id", "unnamed: 0", "simillarhttp",
    "bidirectional_first_seen_ms", "bidirectional_last_seen_ms",
    "src2dst_first_seen_ms", "src2dst_last_seen_ms",
    "dst2src_first_seen_ms", "dst2src_last_seen_ms",
    "src_mac", "dst_mac", "src_oui", "dst_oui", "vlan_id", "tunnel_id",
    "expiration_id", "ip_version",
}


def load_synthetic(cfg: dict, seed: int = 42):
    """Imbalanced, overlapping, multi-cluster data that mimics flow statistics."""
    n = cfg.get("n_samples", 20000)
    ratio = cfg.get("anomaly_ratio", 0.2)
    X, y = make_classification(
        n_samples=n, n_features=40, n_informative=14, n_redundant=10,
        n_clusters_per_class=4, weights=[1 - ratio, ratio], class_sep=1.2,
        flip_y=0.0, random_state=seed,
    )
    X = np.expm1(X - X.min(axis=0)).astype(np.float32)
    names = [f"f{i}" for i in range(X.shape[1])]
    return X, y.astype(int), names


def load_csv_dataset(cfg: dict, seed: int = 42):
    files = sorted(glob.glob(cfg["path"]))
    if not files:
        raise FileNotFoundError(f"No CSV files match: {cfg['path']}")
    log(f"  reading {len(files)} file(s) ...")
    frames = [pd.read_csv(f, low_memory=False, encoding=cfg.get("encoding", "utf-8"),
                          encoding_errors="ignore") for f in files]
    df = pd.concat(frames, ignore_index=True)
    df.columns = [c.strip() for c in df.columns]

    label_col = cfg["label_col"]
    if label_col not in df.columns:
        raise KeyError(f"label_col '{label_col}' not found. Columns: {list(df.columns)[:15]}...")
    labels = df[label_col].astype(str).str.strip()
    normal_values = {str(v).strip().lower() for v in cfg["normal_values"]}
    y = (~labels.str.lower().isin(normal_values)).astype(int).values

    drop = {label_col} | set(cfg.get("drop_cols", []))
    feat_cols = [c for c in df.columns if c not in drop and c.lower() not in ID_COLUMNS]
    X = df[feat_cols].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.dropna(axis=1, how="all")

    keep = ~X.isna().any(axis=1)
    X, y = X[keep.values], y[keep.values]
    X = X.loc[:, X.nunique() > 1]

    dedup = ~X.duplicated()
    X, y = X[dedup.values], y[dedup.values]

    max_n = cfg.get("max_samples")
    if max_n and len(X) > max_n:
        idx, _ = train_test_split(np.arange(len(X)), train_size=max_n,
                                  stratify=y, random_state=seed)
        X, y = X.iloc[idx], y[idx]

    log(f"  samples={len(X)}, features={X.shape[1]}, anomaly_ratio={y.mean():.3f}")
    return X.values.astype(np.float32), y.astype(int), list(X.columns)


def load_dataset(cfg: dict, seed: int = 42):
    if cfg.get("type", "csv") == "synthetic":
        return load_synthetic(cfg, seed)
    return load_csv_dataset(cfg, seed)


class Preprocessor:
    """Signed log1p (tames heavy-tailed byte/packet counters) + standardisation + clipping."""

    def __init__(self, clip: float = 10.0):
        self.clip = clip
        self.scaler = StandardScaler()

    @staticmethod
    def _log(X):
        return np.sign(X) * np.log1p(np.abs(X))

    def fit(self, X):
        self.scaler.fit(self._log(X))
        return self

    def transform(self, X):
        if len(X) == 0:
            return np.empty((0, self.scaler.n_features_in_), dtype=np.float32)
        Z = self.scaler.transform(self._log(X))
        return np.clip(Z, -self.clip, self.clip).astype(np.float32)


TEST_SPLIT_SEED = 42


def dev_test_split(X, y, test_size: float = 0.3):
    """Fixed, seed-independent hold-out test set."""
    return train_test_split(X, y, test_size=test_size, stratify=y, random_state=TEST_SPLIT_SEED)


def make_split(X, y, label_ratio: float, noise_rate: float, seed: int, test_size: float = 0.3):
    """Fixed test split; the train part is split into labeled/unlabeled sets by seed."""
    rng = np.random.RandomState(seed)
    X_tr, X_te, y_tr, y_te = dev_test_split(X, y, test_size)
    if label_ratio >= 1.0:
        lab_idx, unl_idx = np.arange(len(X_tr)), np.arange(0)
    else:
        lab_idx, unl_idx = train_test_split(np.arange(len(X_tr)), train_size=label_ratio,
                                            stratify=y_tr, random_state=seed)
    y_l_true = y_tr[lab_idx].copy()
    y_l = y_l_true.copy()
    if noise_rate > 0:
        n_flip = int(round(noise_rate * len(y_l)))
        flip = rng.choice(len(y_l), n_flip, replace=False)
        y_l[flip] = 1 - y_l[flip]

    pre = Preprocessor().fit(X_tr)
    return {
        "X_l": pre.transform(X_tr[lab_idx]), "y_l": y_l, "y_l_true": y_l_true,
        "X_u": pre.transform(X_tr[unl_idx]), "y_u_true": y_tr[unl_idx],
        "X_te": pre.transform(X_te), "y_te": y_te,
        "preprocessor": pre,
    }
