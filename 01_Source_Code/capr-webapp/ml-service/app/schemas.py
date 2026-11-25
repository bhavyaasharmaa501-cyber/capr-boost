from typing import Optional
from pydantic import BaseModel, Field


class FlowFeatures(BaseModel):
    flow_id: Optional[str] = None
    features: list[float]


class PredictRequest(BaseModel):
    dataset: str
    flows: list[FlowFeatures]
    threshold: Optional[float] = None
    mc_uncertainty: bool = Field(True, description="Return ensemble uncertainty (std across members)")


class PredictionResult(BaseModel):
    flow_id: Optional[str]
    anomaly_probability: float
    uncertainty: Optional[float] = None
    is_anomaly: bool
    threshold: float
    coverage: Optional[float] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    features: Optional[list[float]] = None


class PredictResponse(BaseModel):
    dataset: str
    model_version: str
    results: list[PredictionResult]
    inference_ms_total: float
    note: Optional[str] = None


class ExplainRequest(BaseModel):
    dataset: str
    features: list[float]
    top_k: int = 8


class FeatureContribution(BaseModel):
    feature: str
    value: float
    shap: float


class ExplainResponse(BaseModel):
    dataset: str
    anomaly_probability: float
    base_value: float
    top_features: list[FeatureContribution]


class ModelInfo(BaseModel):
    dataset: str
    method: str
    variant: Optional[str]
    label_ratio: float
    n_features: int
    ensemble_size: int
    features: list[str]
    test_accuracy: Optional[float]
    test_precision: Optional[float]
    test_recall: Optional[float]
    test_f1: Optional[float]
    test_auc_pr: Optional[float]
    test_auc_roc: Optional[float]
    test_fpr: Optional[float]


class HealthResponse(BaseModel):
    status: str
    datasets_loaded: list[str]
