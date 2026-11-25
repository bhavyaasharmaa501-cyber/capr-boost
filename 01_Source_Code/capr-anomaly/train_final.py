"""
Train the deployable CAPR-Boost model and export what the ML service needs.

    python train_final.py --config configs/v2_darknet.yaml --dataset darknet2020 --label_ratio 0.05

Writes artifacts/<dataset>/: capr_boost_model.joblib, preprocessor.json, meta.json,
feature_importance.csv
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

from src.utils import load_config, ensure_dir
from src.data import load_dataset, make_split
from src.capr_boost import CAPRBoost
from src.metrics import evaluate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v2_darknet.yaml")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--label_ratio", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="artifacts")
    args = ap.parse_args()

    cfg = load_config(args.config)
    ds_cfg = next(d for d in cfg["datasets"] if d["name"] == args.dataset)
    X, y, feats = load_dataset(ds_cfg, seed=42)
    sp = make_split(X, y, args.label_ratio, 0.0, args.seed, cfg.get("test_size", 0.3))

    model = CAPRBoost(cfg.get("boost"), seed=args.seed)
    model.fit(sp["X_l"], sp["y_l"], sp["X_u"])
    s = model.score(sp["X_te"])
    metrics = {k: float(v) for k, v in evaluate(sp["y_te"], s, (s >= 0.5).astype(int)).items()}
    print("variant:", model.variant)
    print("test metrics:", json.dumps(metrics, indent=2))

    out = ensure_dir(os.path.join(args.out, args.dataset))
    model.save(os.path.join(out, "capr_boost_model.joblib"))
    pre = sp["preprocessor"]
    with open(os.path.join(out, "preprocessor.json"), "w") as f:
        json.dump({"clip": pre.clip, "mean": pre.scaler.mean_.tolist(),
                   "scale": pre.scaler.scale_.tolist()}, f)
    pd.DataFrame({"feature": feats, "importance": model.feature_importance()}) \
        .sort_values("importance", ascending=False).to_csv(
            os.path.join(out, "feature_importance.csv"), index=False)
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump({"dataset": args.dataset, "method": "capr_boost", "variant": model.variant,
                   "features": feats, "label_ratio": args.label_ratio, "seed": args.seed,
                   "n_labeled": int(len(sp["y_l"])), "n_test": int(len(sp["y_te"])),
                   "test_metrics": metrics, "boost_cfg": model.c,
                   "normal_values": ds_cfg.get("normal_values")}, f, indent=2)
    print(f"artifacts saved to {out}/")


if __name__ == "__main__":
    main()
