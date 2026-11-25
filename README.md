# CAPR-Boost: Label-Efficient Network Anomaly Detection

**CAPR-Boost** is a noise-aware, semi-supervised gradient-boosted ensemble for detecting
malicious and anomalous network flows when only a few labels are available and some of them
may be wrong. It comes with a complete monitoring web application.

**Live demo:** see the *Deployments / Pages* link of this repository
(login `admin@capr.local` / `Admin@12345`).

## Results (5% labelled data)

| Dataset | Method | Accuracy | F1 |
|---------|--------|---------:|---:|
| CIC-Darknet2020 | CAPR-Boost (5 seeds) | 96.94% | 90.99% |
| CIC-Darknet2020 | FixMatch | 93.08% | 81.94% |
| CSE-CIC-IDS2018 | CAPR-Boost | 99.87% | 99.66% |

Full tables and figures: [`06_Results/`](06_Results/).

## Method in brief
1. **Noise-aware label refinement** - out-of-fold losses + per-class Gaussian mixture to
   down-weight or flip suspicious labels.
2. **Confidence-aware pseudo-labelling** - an unlabelled flow is used only when all ensemble
   members agree and mean confidence > 0.97, with a class-prior quota.
3. **Inner cross-validated variant selection** using only labelled data.
4. **Bagged LightGBM ensemble** - ensemble spread gives an uncertainty score, trees give exact
   SHAP explanations.

## Repository layout

| Folder | Contents |
|--------|----------|
| `01_Source_Code/capr-anomaly` | ML research code, experiments, trained models, datasets |
| `01_Source_Code/capr-webapp` | Angular dashboard, ASP.NET Core API, FastAPI ML service, SQL schema, Docker Compose |
| `02_Research_Paper` | IEEE-format paper (PDF + LaTeX source) |
| `03_Project_Report` | Project report (PDF + DOCX) |
| `04_Presentation` | Final presentation (PPTX + PDF) |
| `05_Screenshots` | Application screenshots |
| `06_Results` | Result tables and figures |
| `07_Reference_Papers` | Links to the base paper and references |
| `08_Colab_Demo` | Google Colab notebook + package for live training |

## Tech stack
Python, LightGBM, scikit-learn, SHAP, FastAPI · ASP.NET Core 8, Dapper, SignalR ·
SQL Server · Angular 18, Angular Material, Chart.js · Docker · GitHub Actions / Pages

## Run
- Local full stack: `HOW_TO_RUN.txt`
- Cloud deployment: [`DEPLOYMENT.md`](DEPLOYMENT.md)
