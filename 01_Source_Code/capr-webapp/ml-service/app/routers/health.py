from fastapi import APIRouter

from ..model_registry import get_registry
from ..schemas import HealthResponse, ModelInfo

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", datasets_loaded=get_registry().list_datasets())


@router.get("/models", response_model=list[ModelInfo])
def list_models():
    reg = get_registry()
    out = []
    for name in reg.list_datasets():
        m = reg.get(name)
        tm = m.meta.get("test_metrics", {})
        out.append(ModelInfo(
            dataset=name, method=m.meta.get("method", "capr_boost"), variant=m.model.variant,
            label_ratio=m.meta.get("label_ratio", 0.0), n_features=m.n_features,
            ensemble_size=len(m.model.models), features=m.meta["features"],
            test_accuracy=tm.get("accuracy"), test_precision=tm.get("precision"),
            test_recall=tm.get("recall"), test_f1=tm.get("f1"), test_auc_pr=tm.get("auc_pr"),
            test_auc_roc=tm.get("auc_roc"), test_fpr=tm.get("fpr")))
    return out


@router.post("/models/reload")
def reload_models():
    get_registry().reload()
    return {"status": "reloaded", "datasets_loaded": get_registry().list_datasets()}
