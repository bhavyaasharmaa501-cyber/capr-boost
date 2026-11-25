"""
Aggregate raw_results.csv files into summary tables and publication figures.

    python make_report.py --results results/darknet2020 results/ids2018 --out results/report
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.baselines import DISPLAY_NAMES

METRICS = ["accuracy", "precision", "recall", "f1", "auc_roc", "auc_pr", "fpr", "mcc", "fit_time_s"]
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#7a5cc9", "#8c8c8c"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
BASE_PAPER = {
    "name": "Liu et al. 2024 (Sensors 24:6507), CICIDS2017, as reported",
    "f1_by_ratio": {0.005: 0.9802, 0.01: 0.9865, 0.05: 0.9940, 0.10: 0.9940, 0.20: 0.9973},
    "full_label": {"accuracy": 0.9999, "precision": 0.9998, "recall": 0.9998, "f1": 0.9998},
}
LABEL_SWEEP = ["iforest", "supervised", "mean_teacher", "fixmatch", "capr", "rf", "xgb",
               "lgbm", "lgbm_selftrain", "capr_boost"]
LINE_METHODS = ["capr_boost", "lgbm", "xgb", "lgbm_selftrain", "fixmatch", "capr", "mean_teacher"]


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
        "axes.spines.right": False, "axes.edgecolor": "#8a8a8a", "axes.grid": True,
        "grid.color": "#e6e6e6", "grid.linewidth": 0.8, "axes.axisbelow": True,
        "legend.frameon": False, "savefig.dpi": 300, "savefig.bbox": "tight"})


def summarise(raw):
    g = raw.groupby(["dataset", "method", "label_ratio", "noise_rate"])
    agg = g[METRICS].agg(["mean", "std"])
    agg.columns = [f"{m}_{s}" for m, s in agg.columns]
    agg["n_seeds"] = g.size()
    return agg.reset_index()


def name(m):
    return DISPLAY_NAMES.get(m, m)


def pm(row, metric, pct=True):
    m, s = row[f"{metric}_mean"], row[f"{metric}_std"]
    s = 0.0 if pd.isna(s) else s
    return f"{100*m:.2f} ± {100*s:.2f}" if pct else f"{m:.4f} ± {s:.4f}"


def table_label_sweep(summ, ds, metric):
    d = summ[(summ.dataset == ds) & (summ.noise_rate == 0)]
    ratios = sorted(d.label_ratio.unique())
    rows = []
    for m in [x for x in LABEL_SWEEP + ["rf", "xgb", "lgbm"] if x in set(d.method)]:
        if any(r["Method"] == name(m) for r in rows):
            continue
        r = {"Method": name(m)}
        for lr in ratios:
            c = d[(d.method == m) & (d.label_ratio == lr)]
            r[f"{lr*100:g}%"] = pm(c.iloc[0], metric) if len(c) else "—"
        rows.append(r)
    return pd.DataFrame(rows)


def fig_vs_labels(summ, ds, metric, out):
    d = summ[(summ.dataset == ds) & (summ.noise_rate == 0) & (summ.label_ratio < 1)]
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for i, m in enumerate([m for m in LINE_METHODS if m in set(d.method)]):
        c = d[d.method == m].sort_values("label_ratio")
        lw = 2.4 if m == "capr_boost" else 1.6
        ax.errorbar(c.label_ratio * 100, c[f"{metric}_mean"] * 100, yerr=c[f"{metric}_std"].fillna(0) * 100,
                    marker=MARKERS[i], ms=6, lw=lw, capsize=3, color=PALETTE[i], label=name(m))
    if ds == "ids2018" and metric == "f1":
        xs = sorted(BASE_PAPER["f1_by_ratio"])
        ax.plot([x * 100 for x in xs], [BASE_PAPER["f1_by_ratio"][x] * 100 for x in xs], ls="--",
                color="#444444", lw=1.4, marker="x", label="Base paper (CICIDS2017, reported)")
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 5, 10, 20])
    ax.set_xticklabels(["0.5", "1", "5", "10", "20"])
    ax.set_xlabel("Labelled training data (%)")
    ax.set_ylabel(f"{'Accuracy' if metric == 'accuracy' else 'F1-score'} (%)")
    ax.set_title(f"{ds}: {'accuracy' if metric == 'accuracy' else 'F1'} vs. label budget", loc="left")
    ax.legend(fontsize=8, ncol=2, loc="lower right")
    fig.savefig(os.path.join(out, f"fig_{metric}_vs_labels_{ds}.png"))
    plt.close(fig)


def fig_noise(summ, ds, out):
    d = summ[(summ.dataset == ds) & (summ.label_ratio == 0.05)]
    methods = [m for m in ["capr_boost", "capr", "lgbm", "fixmatch", "mean_teacher", "supervised"]
               if len(d[d.method == m].noise_rate.unique()) > 2]
    if not methods:
        return
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for i, m in enumerate(methods):
        c = d[d.method == m].sort_values("noise_rate")
        ax.errorbar(c.noise_rate * 100, c.f1_mean * 100, yerr=c.f1_std.fillna(0) * 100, marker=MARKERS[i],
                    ms=6, lw=2.4 if m == "capr_boost" else 1.6, capsize=3, color=PALETTE[i], label=name(m))
    ax.set_xlabel("Injected label noise (%)")
    ax.set_ylabel("F1-score (%)")
    ax.set_title(f"{ds}: robustness to noisy labels (5% labelled)", loc="left")
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(out, f"fig_f1_vs_noise_{ds}.png"))
    plt.close(fig)


def fig_ablation(summ, ds, out):
    d = summ[(summ.dataset == ds) & (summ.label_ratio == 0.05) & summ.method.str.startswith("capr_boost")]
    if d.empty:
        return
    order = ["capr_boost", "capr_boost_no_refine", "capr_boost_no_pseudo", "capr_boost_no_select",
             "capr_boost_single"]
    noises = sorted(d.noise_rate.unique())
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    w = 0.8 / len(noises)
    for j, nz in enumerate(noises):
        vals = [d[(d.method == m) & (d.noise_rate == nz)].f1_mean.mean() * 100 for m in order]
        errs = [d[(d.method == m) & (d.noise_rate == nz)].f1_std.mean() * 100 for m in order]
        xs = [i + j * w for i in range(len(order))]
        ax.bar(xs, vals, w * 0.92, yerr=errs, capsize=2, color=PALETTE[j], label=f"{nz*100:g}% label noise")
    ax.set_xticks([i + w * (len(noises) - 1) / 2 for i in range(len(order))])
    ax.set_xticklabels(["Full", "w/o noise\nrefinement", "w/o pseudo-\nlabelling", "w/o CV\nselection",
                        "single\nmodel"], fontsize=8)
    lo = d.f1_mean.min() * 100
    ax.set_ylim(max(0, lo - 8), 100)
    ax.set_ylabel("F1-score (%)")
    ax.set_title(f"{ds}: ablation of CAPR-Boost components", loc="left")
    ax.legend(fontsize=8, loc="lower right")
    fig.savefig(os.path.join(out, f"fig_ablation_{ds}.png"))
    plt.close(fig)


def fig_v1_vs_v2(summ, out):
    d = summ[(summ.dataset == "darknet2020") & (summ.noise_rate == 0) & summ.method.isin(["capr", "capr_boost"])
             & (summ.label_ratio < 1)]
    if d.empty:
        return
    ratios = sorted(d.label_ratio.unique())
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4))
    for ax, metric, lab in zip(axes, ["accuracy", "f1"], ["Accuracy (%)", "F1-score (%)"]):
        for j, m in enumerate(["capr", "capr_boost"]):
            vals = [d[(d.method == m) & (d.label_ratio == r)][f"{metric}_mean"].mean() * 100 for r in ratios]
            ax.bar([i + j * 0.4 for i in range(len(ratios))], vals, 0.37, color=PALETTE[j], label=name(m))
        ax.set_xticks([i + 0.2 for i in range(len(ratios))])
        ax.set_xticklabels([f"{r*100:g}%" for r in ratios])
        ax.set_xlabel("Labelled data")
        ax.set_ylabel(lab)
        ax.set_ylim(50, 100)
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle("Darknet2020: previous version (v1) vs. upgraded CAPR-Boost (v2)", x=0.02, ha="left")
    fig.savefig(os.path.join(out, "fig_v1_vs_v2_darknet2020.png"))
    plt.close(fig)


def fig_feature_importance(art_dir, ds, out, k=15):
    p = os.path.join(art_dir, ds, "feature_importance.csv")
    if not os.path.exists(p):
        return
    fi = pd.read_csv(p).head(k)[::-1]
    fig, ax = plt.subplots(figsize=(6.0, 4.4))
    ax.barh(fi.feature, fi.importance * 100, color=PALETTE[0], height=0.7)
    ax.set_xlabel("Share of total split gain (%)")
    ax.set_title(f"{ds}: top-{k} flow features (CAPR-Boost)", loc="left")
    ax.grid(axis="y", visible=False)
    fig.savefig(os.path.join(out, f"fig_feature_importance_{ds}.png"))
    plt.close(fig)


def fig_confusion(art_dir, ds, out):
    p = os.path.join(art_dir, ds, "meta.json")
    if not os.path.exists(p):
        return
    tm = json.load(open(p))["test_metrics"]
    cm = [[tm["tn"], tm["fp"]], [tm["fn"], tm["tp"]]]
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    ax.imshow(cm, cmap="Blues")
    ax.grid(False)
    for i in range(2):
        for j in range(2):
            v = int(cm[i][j])
            ax.text(j, i, f"{v:,}", ha="center", va="center",
                    color="white" if v > max(map(max, cm)) / 2 else "#1a1a1a", fontsize=11)
    ax.set_xticks([0, 1], ["Normal", "Anomaly"])
    ax.set_yticks([0, 1], ["Normal", "Anomaly"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(f"{ds} test set (acc {tm['accuracy']*100:.2f}%)", loc="left", fontsize=9)
    fig.savefig(os.path.join(out, f"fig_confusion_{ds}.png"))
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", default="results/report")
    ap.add_argument("--artifacts", default="artifacts")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    style()

    raw = pd.concat([pd.read_csv(os.path.join(r, "raw_results.csv")) for r in args.results], ignore_index=True)
    raw.to_csv(os.path.join(args.out, "raw_results_all.csv"), index=False)
    summ = summarise(raw)
    summ.to_csv(os.path.join(args.out, "summary.csv"), index=False)

    md = ["# Experiment summary (mean ± std over seeds, percentages)\n"]
    for ds in sorted(summ.dataset.unique()):
        seeds = int(summ[summ.dataset == ds].n_seeds.max())
        for metric, title in [("accuracy", "Accuracy"), ("f1", "F1-score")]:
            t = table_label_sweep(summ, ds, metric)
            t.to_csv(os.path.join(args.out, f"table_{metric}_{ds}.csv"), index=False)
            md += [f"\n## {ds}: {title} vs. labelled ratio ({seeds} seeds, clean labels)\n", t.to_markdown(index=False)]
        nz = summ[(summ.dataset == ds) & (summ.label_ratio == 0.05) & (summ.noise_rate > 0)]
        if not nz.empty:
            rows = []
            for m in [x for x in ["supervised", "mean_teacher", "fixmatch", "capr", "lgbm", "capr_boost"] if x in set(nz.method)]:
                r = {"Method": name(m)}
                for n in sorted(summ[(summ.dataset == ds) & (summ.method == m) & (summ.label_ratio == 0.05)].noise_rate):
                    c = summ[(summ.dataset == ds) & (summ.method == m) & (summ.label_ratio == 0.05) & (summ.noise_rate == n)]
                    r[f"{n*100:g}% noise"] = pm(c.iloc[0], "f1")
                rows.append(r)
            t = pd.DataFrame(rows)
            t.to_csv(os.path.join(args.out, f"table_noise_{ds}.csv"), index=False)
            md += [f"\n## {ds}: F1 under label noise (5% labelled)\n", t.to_markdown(index=False)]
        ab = summ[(summ.dataset == ds) & summ.method.str.startswith("capr_boost") & (summ.label_ratio == 0.05)
                  & summ.noise_rate.isin([0.0, 0.2])]
        if ab.method.nunique() > 1:
            rows = []
            for m in ["capr_boost", "capr_boost_no_refine", "capr_boost_no_pseudo", "capr_boost_no_select", "capr_boost_single"]:
                r = {"Variant": name(m)}
                for n in [0.0, 0.2]:
                    c = ab[(ab.method == m) & (ab.noise_rate == n)]
                    r[f"Acc @ {n*100:g}% noise"] = pm(c.iloc[0], "accuracy") if len(c) else "—"
                    r[f"F1 @ {n*100:g}% noise"] = pm(c.iloc[0], "f1") if len(c) else "—"
                rows.append(r)
            t = pd.DataFrame(rows)
            t.to_csv(os.path.join(args.out, f"table_ablation_{ds}.csv"), index=False)
            md += [f"\n## {ds}: ablation (5% labelled)\n", t.to_markdown(index=False)]
        full = summ[(summ.dataset == ds) & (summ.label_ratio == 1.0)]
        if not full.empty:
            rows = [{"Method": name(r.method), "Accuracy": pm(r, "accuracy"), "Precision": pm(r, "precision"),
                     "Recall": pm(r, "recall"), "F1": pm(r, "f1")} for _, r in full.iterrows()]
            md += [f"\n## {ds}: fully labelled training set\n", pd.DataFrame(rows).to_markdown(index=False)]
        for metric in ["accuracy", "f1"]:
            fig_vs_labels(summ, ds, metric, args.out)
        fig_noise(summ, ds, args.out)
        fig_ablation(summ, ds, args.out)
        fig_feature_importance(args.artifacts, ds, args.out)
        fig_confusion(args.artifacts, ds, args.out)
    fig_v1_vs_v2(summ, args.out)
    open(os.path.join(args.out, "summary.md"), "w").write("\n".join(md) + "\n")
    print(f"report written to {args.out}/")


if __name__ == "__main__":
    main()
