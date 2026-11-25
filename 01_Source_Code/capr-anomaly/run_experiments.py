"""
Runs all experiments defined in a YAML config and writes:
    <output_dir>/raw_results.csv    one row per (dataset, label_ratio, noise_rate, seed, method)
    <output_dir>/capr_history.csv   per-round pseudo-label statistics of every CAPR variant

Resumable: already-finished runs are skipped, so a Colab disconnect loses at most one run.

Usage:
    python run_experiments.py --config configs/default.yaml
    python run_experiments.py --config configs/default.yaml --quick     # fast smoke test
"""
import argparse
import os
import time
from collections import defaultdict

import pandas as pd
import torch

from src.utils import load_config, set_seed, get_device, ensure_dir, log
from src.data import load_dataset, make_split
from src.baselines import build_method
from src.metrics import evaluate, best_f1_threshold

KEY = ["dataset", "label_ratio", "noise_rate", "seed", "method"]


def quick_overrides(cfg):
    cfg["seeds"] = [0]
    cfg["model"].update(epochs_warmup=5, epochs_per_round=2, ae_epochs=5, min_steps=100)
    cfg["capr"].update(rounds=3, mc_passes=5)
    cfg["ssl_epochs"] = 2
    for exp in cfg["experiments"].values():
        exp["label_ratios"] = exp["label_ratios"][:2]
        exp["noise_rates"] = exp["noise_rates"][:2]
    return cfg


def build_jobs(cfg):
    """{(ratio, noise, seed): set(methods)} -- one data split is shared by all its methods."""
    jobs = defaultdict(set)
    for exp in cfg["experiments"].values():
        if not exp.get("enabled", True):
            continue
        for r in exp["label_ratios"]:
            for n in exp["noise_rates"]:
                for s in exp.get("seeds", cfg["seeds"]):
                    jobs[(float(r), float(n), int(s))].update(exp["methods"])
    return jobs


def append_csv(rows, path):
    """Append rows, always aligned to the file's existing header."""
    if not rows:
        return
    df = pd.DataFrame(rows)
    if os.path.exists(path):
        existing_cols = pd.read_csv(path, nrows=0).columns.tolist()
        extra = [c for c in df.columns if c not in existing_cols]
        if extra:
            log(f"  note: {os.path.basename(path)} gained new column(s) {extra}; "
                f"rewriting header to include them")
            head = pd.read_csv(path)
            pd.concat([head, df], ignore_index=True).to_csv(path, index=False)
            return
        df = df.reindex(columns=existing_cols)
        df.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, mode="a", header=True, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--datasets", nargs="*", help="run only these dataset names")
    args = ap.parse_args()

    cfg = load_config(args.config)
    torch.set_num_threads(int(os.environ.get("CAPR_NJOBS", "4")))
    if args.quick:
        cfg = quick_overrides(cfg)
    device = get_device(cfg.get("device", "auto"))
    out = ensure_dir(cfg.get("output_dir", "results"))
    raw_path = os.path.join(out, "raw_results.csv")
    hist_path = os.path.join(out, "capr_history.csv")
    boost_hist_path = os.path.join(out, "boost_history.csv")
    log(f"device={device}  output={out}")

    done = set()
    if os.path.exists(raw_path):
        prev = pd.read_csv(raw_path)
        done = {tuple(x) for x in prev[KEY].astype(str).values.tolist()}
        log(f"resuming: {len(done)} runs already finished")

    jobs = build_jobs(cfg)
    for ds_cfg in cfg["datasets"]:
        name = ds_cfg["name"]
        if args.datasets and name not in args.datasets:
            continue
        log(f"\n=== dataset: {name} ===")
        X, y, feats = load_dataset(ds_cfg, seed=42)

        for (ratio, noise, seed), methods in sorted(jobs.items()):
            todo = [m for m in sorted(methods)
                    if (name, str(ratio), str(noise), str(seed), m) not in done]
            if not todo:
                continue
            set_seed(seed)
            sp = make_split(X, y, ratio, noise, seed, cfg.get("test_size", 0.3))
            log(f"\n[{name}] labeled={len(sp['y_l'])} unlabeled={len(sp['y_u_true'])} "
                f"test={len(sp['y_te'])} | ratio={ratio} noise={noise} seed={seed}")

            for mname in todo:
                set_seed(seed)
                method = build_method(mname, sp["X_l"].shape[1], cfg, device, seed)
                t0 = time.time()
                method.fit(sp["X_l"], sp["y_l"], sp["X_u"],
                           y_u_true=sp["y_u_true"], y_l_true=sp["y_l_true"])
                fit_time = time.time() - t0

                t0 = time.time()
                s_te = method.score(sp["X_te"])
                infer_ms = 1000 * (time.time() - t0) / len(sp["y_te"])
                thr = 0.5 if method.prob_output else best_f1_threshold(
                    sp["y_l"], method.score(sp["X_l"]))
                res = evaluate(sp["y_te"], s_te, (s_te >= thr).astype(int))

                row = dict(dataset=name, label_ratio=ratio, noise_rate=noise, seed=seed,
                           method=mname, n_labeled=len(sp["y_l"]),
                           fit_time_s=round(fit_time, 2), infer_ms_per_flow=round(infer_ms, 5),
                           **{k: round(v, 5) if isinstance(v, float) else v
                              for k, v in res.items()})
                append_csv([row], raw_path)
                hist = getattr(getattr(method, "model", None), "history", None)
                if hist:
                    hp = boost_hist_path if mname.startswith("capr_boost") else hist_path
                    append_csv([dict(dataset=name, label_ratio=ratio, noise_rate=noise,
                                     seed=seed, method=mname, **h) for h in hist], hp)
                log(f"  {mname:<18} F1={res['f1']:.4f} AUC-PR={res['auc_pr']:.4f} "
                    f"AUC-ROC={res['auc_roc']:.4f} FPR={res['fpr']:.4f} ({fit_time:.1f}s)")

    log(f"\nFinished. Now run:  python make_report.py --results {out}")


if __name__ == "__main__":
    main()
