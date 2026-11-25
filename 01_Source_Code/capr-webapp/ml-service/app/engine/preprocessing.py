import numpy as np
from sklearn.preprocessing import StandardScaler


class Preprocessor:
    def __init__(self, clip: float = 10.0):
        self.clip = clip
        self.scaler = StandardScaler()

    @staticmethod
    def _log(X):
        return np.sign(X) * np.log1p(np.abs(X))

    def fit(self, X):
        self.scaler.fit(self._log(X))
        return self

    def transform(self, X):
        Z = self.scaler.transform(self._log(X))
        return np.clip(Z, -self.clip, self.clip).astype(np.float32)

    @classmethod
    def from_json(cls, d: dict) -> "Preprocessor":
        obj = cls(clip=d["clip"])
        obj.scaler.mean_ = np.asarray(d["mean"], dtype=np.float64)
        obj.scaler.scale_ = np.asarray(d["scale"], dtype=np.float64)
        obj.scaler.var_ = obj.scaler.scale_ ** 2
        obj.scaler.n_features_in_ = len(d["mean"])
        return obj
