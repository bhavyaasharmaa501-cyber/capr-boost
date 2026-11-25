"""Write small CSV samples drawn only from the held-out test split, for demoing the web app."""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data import ID_COLUMNS, TEST_SPLIT_SEED
from src.utils import load_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    ds = load_config(args.config)["datasets"][0]
    df = pd.read_csv(ds["path"], low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    labels = df[ds["label_col"]].astype(str).str.strip()
    y = (~labels.str.lower().isin({v.lower() for v in ds["normal_values"]})).astype(int).values
    drop = {ds["label_col"]} | set(ds.get("drop_cols", []))
    feat_cols = [c for c in df.columns if c not in drop and c.lower() not in ID_COLUMNS]
    X = df[feat_cols].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    X = X.dropna(axis=1, how="all")
    keep = ~X.isna().any(axis=1)
    X, y_k = X[keep.values], y[keep.values]
    X = X.loc[:, X.nunique() > 1]
    dedup = ~X.duplicated()
    idx = X.index[dedup.values].values
    y_k = y_k[dedup.values]
    _, te_idx = train_test_split(idx, test_size=0.3, stratify=y_k, random_state=TEST_SPLIT_SEED)
    rng = np.random.RandomState(1)
    pick = rng.choice(te_idx, size=min(args.n, len(te_idx)), replace=False)
    df.loc[pick].to_csv(args.out, index=False)
    print(f"wrote {len(pick)} test-split rows to {args.out}")


if __name__ == "__main__":
    main()
