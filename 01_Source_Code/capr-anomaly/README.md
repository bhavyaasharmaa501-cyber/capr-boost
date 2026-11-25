# capr-anomaly: CAPR-Boost research code

Semi-supervised, label-noise-aware anomaly detection on network flow features.
This folder contains the model, all baselines, the datasets used, the experiment configs,
the raw results and the scripts that turn them into tables and figures.

## Method in brief

CAPR-Boost (`src/capr_boost.py`) has four stages:

1. **S1 noise-aware refinement**: 5-fold out-of-fold LightGBM probabilities, per-sample loss,
   per-class two-component GMM; suspicious labels are flipped or down-weighted.
2. **S2 confidence-aware pseudo-labelling**: unlabelled flows are accepted only when all
   ensemble members agree and mean confidence is at least 0.97, with a class-prior quota.
3. **S3 variant selection**: plain / refine / pl / refine_pl chosen by 3-fold CV on the
   labelled data only.
4. **S4 ensemble**: three LightGBM models; mean probability is the score, the standard
   deviation is the uncertainty, TreeSHAP gives per-flow explanations.

The earlier neural version (CAPR-Net v1, `src/capr.py`) is kept as a baseline.

## Layout

```
src/               model, baselines, data loading, metrics
configs/           v2_darknet.yaml, v2_ids2018.yaml, default.yaml (synthetic smoke test)
data/              CIC-Darknet2020 CSV, CSE-CIC-IDS2018 subset (csv.gz)
tools/             IDS2018 subset builder, demo-sample extractor
run_experiments.py runs every method / ratio / noise / seed in a config (resumable)
make_report.py     summary tables and figures
train_final.py     trains the deployed models into artifacts/<dataset>/
reproduce.py       re-runs paper experiments and compares with the published numbers
results/           raw per-run CSVs and results/report/ (tables, figures, summary)
artifacts/         deployed models used by the web application
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Reproduce

```bash
python run_experiments.py --config configs/default.yaml        # quick synthetic check
python run_experiments.py --config configs/v2_darknet.yaml
python run_experiments.py --config configs/v2_ids2018.yaml
python make_report.py --results results/darknet2020 results/ids2018 --out results/report --artifacts artifacts
python train_final.py --config configs/v2_darknet.yaml --dataset darknet2020
python train_final.py --config configs/v2_ids2018.yaml --dataset ids2018
```

### Check the published numbers

```bash
python reproduce.py --preset headline        # Darknet2020, 5% labels, 5 seeds (~5-8 min)
python reproduce.py --preset noise           # 20% label noise
python reproduce.py --preset ids_headline    # IDS2018, 0.5% and 5% labels
python reproduce.py --preset all_capr_boost  # every CAPR-Boost number
```

`reproduce.py` re-runs the selected experiments with the same configs, split and seeds and prints
the new mean next to the published one (`results/report/raw_results_all.csv`, same seeds). A
`diff` of 0.00 means the number was reproduced exactly. The same script is used by the Google
Colab notebook in `08_Colab_Demo/`.

Set `CAPR_NJOBS` to control CPU threads (default 4). On a 4-core CPU the two full configs
take several hours; the finished results are already included in `results/`.

## Evaluation rules

- A stratified 30% test split is fixed with seed 42 and is never used for training,
  model selection or threshold tuning.
- Label noise is injected only into the labelled training subset.
- Exact duplicate flows are removed before splitting.
- Every number in the paper, report and slides comes from `results/report/summary.csv`.

## Results

See `results/report/summary.md` for all tables (mean ± std over seeds).
