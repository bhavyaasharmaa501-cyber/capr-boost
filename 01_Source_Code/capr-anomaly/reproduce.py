"""
Re-run a subset of the paper's experiments and compare with the published numbers.

    python reproduce.py --preset headline
    python reproduce.py --preset all_capr_boost
    python reproduce.py --preset full            # every experiment in the paper (many hours on CPU)

Uses the same configs, splits, seeds and code as the paper; results go to results_repro/.
The reference numbers are read from results/report/raw_results_all.csv, restricted to the
same seeds, so a difference of 0.00 means the paper's number was reproduced exactly.
"""
import argparse
import copy
import os
import subprocess
import sys

import pandas as pd
import yaml

CONFIGS = {"darknet2020": "configs/v2_darknet.yaml", "ids2018": "configs/v2_ids2018.yaml"}
PRESETS = {
    "headline": [
        ("darknet2020", [0.05], [0.0], ["capr_boost", "lgbm", "xgb"], [0, 1, 2, 3, 4]),
    ],
    "ids_headline": [
        ("ids2018", [0.005, 0.05], [0.0], ["capr_boost", "lgbm"], [0, 1, 2]),
    ],
    "noise": [
        ("darknet2020", [0.05], [0.2], ["capr_boost", "lgbm"], [0, 1, 2]),
    ],
    "all_capr_boost": [
        ("darknet2020", [0.005, 0.01, 0.05, 0.1, 0.2, 1.0], [0.0], ["capr_boost"], [0, 1, 2, 3, 4]),
        ("darknet2020", [0.05], [0.1, 0.2, 0.3, 0.4], ["capr_boost"], [0, 1, 2]),
        ("ids2018", [0.005, 0.01, 0.05, 0.1, 0.2, 1.0], [0.0], ["capr_boost"], [0, 1, 2]),
    ],
}
METRICS = ["accuracy", "precision", "recall", "f1"]
KEY = ["dataset", "method", "label_ratio", "noise_rate"]


def write_config(ds, jobs, out_root):
    cfg = yaml.safe_load(open(CONFIGS[ds]))
    cfg = copy.deepcopy(cfg)
    cfg["output_dir"] = os.path.join(out_root, ds)
    cfg["experiments"] = {f"job{i}": {"label_ratios": r, "noise_rates": n, "methods": m, "seeds": s}
                          for i, (r, n, m, s) in enumerate(jobs)}
    path = os.path.join(out_root, f"{ds}.yaml")
    os.makedirs(out_root, exist_ok=True)
    yaml.safe_dump(cfg, open(path, "w"))
    return path


def run(preset, out_root):
    if preset == "full":
        cfgs = []
        for ds, path in CONFIGS.items():
            cfg = yaml.safe_load(open(path))
            cfg["output_dir"] = os.path.join(out_root, ds)
            p = os.path.join(out_root, f"{ds}.yaml")
            os.makedirs(out_root, exist_ok=True)
            yaml.safe_dump(cfg, open(p, "w"))
            cfgs.append(p)
    else:
        by_ds = {}
        for ds, r, n, m, s in PRESETS[preset]:
            by_ds.setdefault(ds, []).append((r, n, m, s))
        cfgs = [write_config(ds, jobs, out_root) for ds, jobs in by_ds.items()]
    for c in cfgs:
        subprocess.run([sys.executable, "run_experiments.py", "--config", c], check=True)


def compare(out_root, reference="results/report/raw_results_all.csv"):
    frames = [pd.read_csv(os.path.join(out_root, d, "raw_results.csv"))
              for d in CONFIGS if os.path.exists(os.path.join(out_root, d, "raw_results.csv"))]
    new = pd.concat(frames, ignore_index=True)
    ref = pd.read_csv(reference)
    rows = []
    for k, g in new.groupby(KEY):
        r = ref.set_index(KEY).loc[[k]] if k in ref.set_index(KEY).index else None
        seeds = sorted(g.seed.unique())
        row = dict(zip(KEY, k), seeds=len(seeds))
        for m in ["accuracy", "f1"]:
            row[f"{m}_colab"] = round(g[m].mean() * 100, 2)
            if r is not None:
                rr = r[r.seed.isin(seeds)]
                row[f"{m}_paper"] = round(rr[m].mean() * 100, 2)
                row[f"{m}_diff"] = round(row[f"{m}_colab"] - row[f"{m}_paper"], 2)
        rows.append(row)
    table = pd.DataFrame(rows)
    table["label_ratio"] = (table.label_ratio * 100).map(lambda v: f"{v:g}%")
    table["noise_rate"] = (table.noise_rate * 100).map(lambda v: f"{v:g}%")
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="headline", choices=list(PRESETS) + ["full"])
    ap.add_argument("--out", default="results_repro")
    ap.add_argument("--compare_only", action="store_true")
    a = ap.parse_args()
    if not a.compare_only:
        run(a.preset, a.out)
    t = compare(a.out)
    pd.set_option("display.width", 200)
    print(t.to_string(index=False))
    t.to_csv(os.path.join(a.out, "comparison_with_paper.csv"), index=False)


if __name__ == "__main__":
    main()
