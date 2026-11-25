import json
import logging
import os
import time

import numpy as np

from .engine.capr_boost import CAPRBoost
from .engine.preprocessing import Preprocessor
from . import config

log = logging.getLogger("capr.registry")
MODEL_FILE = "capr_boost_model.joblib"


class LoadedModel:
    def __init__(self, dataset: str, path: str):
        self.dataset = dataset
        t0 = time.time()
        self.model = CAPRBoost.load(os.path.join(path, MODEL_FILE))
        with open(os.path.join(path, "preprocessor.json")) as f:
            self.preprocessor = Preprocessor.from_json(json.load(f))
        with open(os.path.join(path, "meta.json")) as f:
            self.meta = json.load(f)
        log.info("loaded model '%s' in %.2fs (%d features)", dataset, time.time() - t0,
                 len(self.meta["features"]))

    @property
    def n_features(self) -> int:
        return len(self.meta["features"])

    def score(self, X_raw: np.ndarray):
        return self.model.predict_with_uncertainty(self.preprocessor.transform(X_raw))

    def explain(self, X_raw: np.ndarray):
        contrib, base = self.model.contributions(self.preprocessor.transform(X_raw))
        return contrib, base


class ModelRegistry:
    def __init__(self, artifacts_dir: str):
        self.artifacts_dir = artifacts_dir
        self._models: dict[str, LoadedModel] = {}
        self.reload()

    def reload(self):
        found = {}
        if os.path.isdir(self.artifacts_dir):
            for name in sorted(os.listdir(self.artifacts_dir)):
                path = os.path.join(self.artifacts_dir, name)
                if os.path.isfile(os.path.join(path, MODEL_FILE)):
                    try:
                        found[name] = LoadedModel(name, path)
                    except Exception as e:
                        log.error("failed to load model '%s': %s", name, e)
        self._models = found
        if not found:
            log.warning("no models found under %s", self.artifacts_dir)

    def get(self, dataset: str) -> LoadedModel:
        if dataset not in self._models:
            available = ", ".join(self._models) or "(none loaded)"
            raise KeyError(f"no model registered for dataset '{dataset}'. Available: {available}")
        return self._models[dataset]

    def list_datasets(self) -> list[str]:
        return sorted(self._models)


registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global registry
    if registry is None:
        registry = ModelRegistry(os.path.abspath(config.ARTIFACTS_DIR))
    return registry
