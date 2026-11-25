"""CAPR-Boost: confidence-aware, noise-robust boosted ensemble for traffic anomaly detection."""
import os

import joblib
import numpy as np
import lightgbm as lgb
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import StratifiedKFold

DEFAULT_BOOST = dict(n_models=3, n_estimators=500, learning_rate=0.04, num_leaves=63,
                     min_child_samples=5, subsample=0.8, colsample_bytree=0.7,
                     oof_folds=5, select_folds=3, refine=True, pseudo=True, select=True,
                     tau=0.97, pl_cap=2.0, max_unlabeled=60000, flip_conf=0.3,
                     flip_weight=0.2, min_weight=0.05,
                     n_jobs=int(os.environ.get("CAPR_NJOBS", "4")))

VARIANTS = ("plain", "refine", "refine_pl", "pl")


def _lgbm(c, seed, n_estimators=None, num_leaves=None, min_child=None):
    return lgb.LGBMClassifier(
        n_estimators=n_estimators or c["n_estimators"], learning_rate=c["learning_rate"],
        num_leaves=num_leaves or c["num_leaves"],
        min_child_samples=min_child or c["min_child_samples"], subsample=c["subsample"],
        subsample_freq=1, colsample_bytree=c["colsample_bytree"], random_state=seed,
        n_jobs=c["n_jobs"], verbose=-1)


class CAPRBoost:
    prob_output = True

    def __init__(self, cfg=None, seed=0):
        self.c = {**DEFAULT_BOOST, **(cfg or {})}
        self.seed = seed
        self.models = []
        self.history = []
        self.variant = None

    def _oof(self, X, y, w=None):
        p = np.zeros(len(y))
        k = min(self.c["oof_folds"], int(np.bincount(y, minlength=2).min()))
        if k < 2:
            return np.where(y == 1, 0.9, 0.1)
        for a, b in StratifiedKFold(k, shuffle=True, random_state=self.seed).split(X, y):
            m = _lgbm(self.c, self.seed, n_estimators=150, num_leaves=15, min_child=20)
            m.fit(X[a], y[a], sample_weight=None if w is None else w[a])
            p[b] = m.predict_proba(X[b])[:, 1]
        return p

    @staticmethod
    def _clean_prob(p, y):
        loss = -np.log(np.clip(np.where(y == 1, p, 1 - p), 1e-6, 1.0))
        w = np.ones(len(y))
        for cls in (0, 1):
            m = y == cls
            if m.sum() < 10:
                continue
            l = loss[m].reshape(-1, 1)
            g = GaussianMixture(2, random_state=0, reg_covar=1e-4).fit(l)
            w[m] = g.predict_proba(l)[:, int(np.argmin(g.means_.ravel()))]
        return w

    def _refine(self, X, y):
        c = self.c
        p = self._oof(X, y)
        w = self._clean_prob(p, y)
        flip = (w < c["flip_weight"]) & (np.abs(p - 0.5) > c["flip_conf"])
        y2 = y.copy()
        y2[flip] = 1 - y2[flip]
        w2 = np.where(flip, 0.8, np.clip(w, c["min_weight"], 1.0))
        return y2, w2, {"flipped": int(flip.sum()), "down_weighted": int((w2 < 0.5).sum())}

    def _ensemble(self, X, y, w=None, n=None):
        return [_lgbm(self.c, self.seed + i).fit(X, y, sample_weight=w)
                for i in range(n or self.c["n_models"])]

    @staticmethod
    def _proba(models, X):
        P = np.stack([m.predict_proba(X)[:, 1] for m in models])
        return P.mean(0), P.std(0), P

    def _pseudo(self, models, X_l, y_l, w_l, X_u):
        c = self.c
        if X_u is None or len(X_u) == 0:
            return X_l, y_l, w_l, 0
        rng = np.random.RandomState(self.seed)
        if len(X_u) > c["max_unlabeled"]:
            X_u = X_u[rng.choice(len(X_u), c["max_unlabeled"], replace=False)]
        mean, _, P = self._proba(models, X_u)
        lab = (mean >= 0.5).astype(int)
        agree = np.all((P >= 0.5) == lab[None, :], axis=0)
        conf = np.maximum(mean, 1 - mean)
        prior = float(np.average(y_l, weights=w_l))
        keep = []
        for cls in (0, 1):
            idx = np.where((lab == cls) & agree & (conf >= c["tau"]))[0]
            share = prior if cls == 1 else 1 - prior
            cap = int(c["pl_cap"] * len(y_l) * share)
            keep.append(idx[np.argsort(-conf[idx])][:cap])
        keep = np.concatenate(keep)
        if len(keep) == 0:
            return X_l, y_l, w_l, 0
        return (np.vstack([X_l, X_u[keep]]), np.r_[y_l, lab[keep]],
                np.r_[w_l, conf[keep]], len(keep))

    def _fit_variant(self, variant, X_l, y_l, X_u, n_models=None):
        info = {"variant": variant, "flipped": 0, "down_weighted": 0, "n_pseudo": 0}
        y, w = y_l, np.ones(len(y_l))
        if variant.startswith("refine"):
            y, w, r = self._refine(X_l, y_l)
            info.update(r)
        models = self._ensemble(X_l, y, w, n_models)
        if variant.endswith("pl"):
            Xa, ya, wa, n_pl = self._pseudo(models, X_l, y, w, X_u)
            info["n_pseudo"] = n_pl
            if n_pl:
                models = self._ensemble(Xa, ya, wa, n_models)
        return models, info

    def _select(self, X_l, y_l, X_u):
        c = self.c
        has_u = X_u is not None and len(X_u) > 0
        cands = [v for v in VARIANTS
                 if (c["refine"] or "refine" not in v)
                 and ((c["pseudo"] and has_u) or not v.endswith("pl"))]
        if len(cands) == 1:
            return cands[0], {}
        k = min(c["select_folds"], int(np.bincount(y_l, minlength=2).min()))
        if k < 2:
            return cands[0], {}
        scores = {v: [] for v in cands}
        for a, b in StratifiedKFold(k, shuffle=True, random_state=self.seed + 99).split(X_l, y_l):
            for v in cands:
                models, _ = self._fit_variant(v, X_l[a], y_l[a], X_u, n_models=1)
                pred = self._proba(models, X_l[b])[0] >= 0.5
                scores[v].append(float((pred == y_l[b]).mean()))
        mean = {v: float(np.mean(s)) for v, s in scores.items()}
        best = max(mean.values())
        order = sorted(cands, key=lambda v: VARIANTS.index(v))
        choice = next(v for v in order if mean[v] >= best - 1e-3)
        return choice, mean

    def fit(self, X_l, y_l, X_u=None, **_):
        y_l = np.asarray(y_l).astype(int)
        c = self.c
        if c["select"]:
            self.variant, cv = self._select(X_l, y_l, X_u)
        else:
            self.variant = "refine_pl" if c["refine"] and c["pseudo"] else \
                "refine" if c["refine"] else "pl" if c["pseudo"] else "plain"
            cv = {}
        self.models, info = self._fit_variant(self.variant, X_l, y_l, X_u)
        self.history = [{**info, **{f"cv_{k}": v for k, v in cv.items()}}]
        return self

    def score(self, X):
        return self._proba(self.models, X)[0]

    def predict_with_uncertainty(self, X):
        mean, std, _ = self._proba(self.models, X)
        return mean, std

    def contributions(self, X):
        C = np.mean([m.booster_.predict(X, pred_contrib=True) for m in self.models], axis=0)
        return C[:, :-1], C[:, -1]

    def feature_importance(self):
        imp = np.mean([m.booster_.feature_importance("gain") for m in self.models], axis=0)
        return imp / max(imp.sum(), 1e-12)

    def save(self, path):
        joblib.dump({"cfg": self.c, "seed": self.seed, "variant": self.variant,
                     "models": self.models, "history": self.history}, path)

    @classmethod
    def load(cls, path):
        d = joblib.load(path)
        obj = cls(d["cfg"], d["seed"])
        obj.models, obj.variant, obj.history = d["models"], d["variant"], d["history"]
        return obj
