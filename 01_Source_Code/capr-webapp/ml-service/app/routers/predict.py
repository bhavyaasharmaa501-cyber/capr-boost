import logging
import tempfile
import time
from io import BytesIO

import numpy as np
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import config, feature_mapping
from ..model_registry import LoadedModel, get_registry
from ..schemas import (ExplainRequest, ExplainResponse, FeatureContribution,
                       PredictRequest, PredictResponse, PredictionResult)

log = logging.getLogger("capr.predict")
router = APIRouter(tags=["predict"])


def _get_model(dataset: str) -> LoadedModel:
    try:
        return get_registry().get(dataset)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _model_version(meta: dict) -> str:
    return f"{meta.get('method', 'capr_boost')}-seed{meta.get('seed', 0)}-lr{meta.get('label_ratio', 0)}"


def _score(lm: LoadedModel, X_raw: np.ndarray, with_uncertainty: bool):
    p, std = lm.score(X_raw)
    return p, (std if with_uncertainty else None)


def _to_results(flow_ids, p, std, threshold, coverage=None, flow_meta=None):
    n = len(p)
    cov_list = coverage if coverage is not None else [None] * n
    meta_list = flow_meta if flow_meta is not None else [{}] * n
    return [
        PredictionResult(
            flow_id=flow_ids[i], anomaly_probability=float(p[i]),
            uncertainty=float(std[i]) if std is not None else None,
            is_anomaly=bool(p[i] >= threshold), threshold=float(threshold),
            coverage=float(cov_list[i]) if cov_list[i] is not None else None,
            src_ip=meta_list[i].get("src_ip"), dst_ip=meta_list[i].get("dst_ip"),
            src_port=meta_list[i].get("src_port"), dst_port=meta_list[i].get("dst_port"),
            features=meta_list[i].get("features"))
        for i in range(n)
    ]


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    lm = _get_model(req.dataset)
    if not req.flows:
        raise HTTPException(422, "'flows' must contain at least one entry")
    if len(req.flows) > config.MAX_BATCH_FLOWS:
        raise HTTPException(413, f"{len(req.flows)} flows exceeds the limit of {config.MAX_BATCH_FLOWS}")
    for f in req.flows:
        if len(f.features) != lm.n_features:
            raise HTTPException(422, f"flow '{f.flow_id}' has {len(f.features)} features, "
                                     f"model '{req.dataset}' expects {lm.n_features}")
    t0 = time.time()
    X = np.asarray([f.features for f in req.flows], dtype=np.float32)
    thr = req.threshold if req.threshold is not None else config.DEFAULT_THRESHOLD
    p, std = _score(lm, X, req.mc_uncertainty)
    return PredictResponse(dataset=req.dataset, model_version=_model_version(lm.meta),
                           results=_to_results([f.flow_id for f in req.flows], p, std, thr),
                           inference_ms_total=(time.time() - t0) * 1000)


def _resolve_columns(df: pd.DataFrame, expected: list[str]) -> list[str]:
    df.columns = [str(c).strip() for c in df.columns]
    lookup = {c.lower(): c for c in df.columns}
    resolved, missing = [], []
    for feat in expected:
        if feat in df.columns:
            resolved.append(feat)
        elif feat.lower() in lookup:
            resolved.append(lookup[feat.lower()])
        else:
            missing.append(feat)
    if missing:
        raise HTTPException(422, f"CSV is missing {len(missing)} expected column(s), e.g. "
                                 f"{missing[:5]}. Upload a CICFlowMeter export or use /predict/pcap.")
    return resolved


_ENDPOINT_COLS = {
    "src_ip": ("src ip", "source ip", "src_ip"),
    "dst_ip": ("dst ip", "destination ip", "dst_ip"),
    "src_port": ("src port", "source port", "src_port"),
    "dst_port": ("dst port", "destination port", "dst_port"),
}


def _endpoint_meta(df: pd.DataFrame, X: np.ndarray):
    lookup = {c.lower(): c for c in df.columns}
    found = {k: next((lookup[a] for a in aliases if a in lookup), None) for k, aliases in _ENDPOINT_COLS.items()}
    out = []
    for i, (_, row) in enumerate(df.iterrows()):
        m = {"features": X[i].astype(float).tolist()}
        for k, col in found.items():
            if col is None or pd.isna(row[col]):
                continue
            v = row[col]
            if k.endswith("port"):
                try:
                    m[k] = int(float(v))
                except (TypeError, ValueError):
                    continue
            else:
                m[k] = str(v)
        out.append(m)
    return out


@router.post("/predict/csv", response_model=PredictResponse)
async def predict_csv(dataset: str = Form(...), threshold: float | None = Form(None),
                      mc_uncertainty: bool = Form(True), file: UploadFile = File(...)):
    lm = _get_model(dataset)
    raw = await file.read()
    try:
        df = pd.read_csv(BytesIO(raw), low_memory=False, encoding="utf-8", encoding_errors="ignore")
    except Exception as e:
        raise HTTPException(422, f"could not parse '{file.filename}' as CSV: {e}")
    if df.empty:
        raise HTTPException(422, "CSV has no data rows")
    if len(df) > config.MAX_BATCH_FLOWS:
        raise HTTPException(413, f"{len(df)} rows exceeds the limit of {config.MAX_BATCH_FLOWS}")

    cols = _resolve_columns(df, lm.meta["features"])
    Xdf = df[cols].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    n_bad = int(Xdf.isna().sum().sum())
    X = Xdf.fillna(0.0).values.astype(np.float32)

    t0 = time.time()
    thr = threshold if threshold is not None else config.DEFAULT_THRESHOLD
    p, std = _score(lm, X, mc_uncertainty)
    note = (f"{n_bad} non-numeric or missing cell(s) were treated as 0" if n_bad else None)
    return PredictResponse(dataset=dataset, model_version=_model_version(lm.meta),
                           results=_to_results([str(i) for i in df.index], p, std, thr,
                                               flow_meta=_endpoint_meta(df, X)),
                           inference_ms_total=(time.time() - t0) * 1000, note=note)


@router.post("/predict/pcap", response_model=PredictResponse)
async def predict_pcap(dataset: str = Form(...), threshold: float | None = Form(None),
                       mc_uncertainty: bool = Form(True), file: UploadFile = File(...)):
    lm = _get_model(dataset)
    try:
        from nfstream import NFStreamer
    except ImportError:
        raise HTTPException(500, "nfstream is not installed on this ml-service instance")

    raw = await file.read()
    if not raw:
        raise HTTPException(422, "uploaded file is empty")
    with tempfile.NamedTemporaryFile(suffix=".pcap") as tmp:
        tmp.write(raw)
        tmp.flush()
        try:
            flows_df = NFStreamer(source=tmp.name, statistical_analysis=True).to_pandas()
        except Exception as e:
            raise HTTPException(422, f"could not parse '{file.filename}' as a PCAP: {e}")
    if flows_df.empty:
        raise HTTPException(422, f"no flows extracted from '{file.filename}'")
    if len(flows_df) > config.MAX_PCAP_FLOWS:
        raise HTTPException(413, f"{len(flows_df)} flows exceeds the limit of {config.MAX_PCAP_FLOWS}")

    expected = lm.meta["features"]
    t0 = time.time()
    vecs, covs, flow_ids, flow_meta = [], [], [], []
    for _, row in flows_df.iterrows():
        r = row.to_dict()
        vec, cov = feature_mapping.extract_features(r, expected)
        vecs.append(vec)
        covs.append(cov)
        flow_ids.append(f"{r.get('src_ip', '?')}:{r.get('src_port', '?')}->"
                        f"{r.get('dst_ip', '?')}:{r.get('dst_port', '?')}")
        flow_meta.append({
            "src_ip": r.get("src_ip"), "dst_ip": r.get("dst_ip"),
            "src_port": int(r["src_port"]) if r.get("src_port") is not None else None,
            "dst_port": int(r["dst_port"]) if r.get("dst_port") is not None else None,
            "features": vec.tolist()})
    X = np.vstack(vecs).astype(np.float32)
    thr = threshold if threshold is not None else config.DEFAULT_THRESHOLD
    p, std = _score(lm, X, mc_uncertainty)
    note = (f"Features were derived from the raw capture with NFStream; average schema coverage "
            f"{float(np.mean(covs)):.0%}. Scores are approximate compared with a CICFlowMeter CSV.")
    return PredictResponse(dataset=dataset, model_version=_model_version(lm.meta),
                           results=_to_results(flow_ids, p, std, thr, covs, flow_meta),
                           inference_ms_total=(time.time() - t0) * 1000, note=note)


@router.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    lm = _get_model(req.dataset)
    if len(req.features) != lm.n_features:
        raise HTTPException(422, f"expected {lm.n_features} features, got {len(req.features)}")
    X_raw = np.asarray([req.features], dtype=np.float32)
    contrib, base = lm.explain(X_raw)
    sv = contrib[0]
    features = lm.meta["features"]
    top_k = max(1, min(req.top_k, len(features)))
    order = np.argsort(-np.abs(sv))[:top_k]
    top = [FeatureContribution(feature=features[i], value=float(X_raw[0, i]), shap=float(sv[i]))
           for i in order]
    prob = float(lm.score(X_raw)[0][0])
    return ExplainResponse(dataset=req.dataset, anomaly_probability=prob,
                           base_value=float(base[0]), top_features=top)
