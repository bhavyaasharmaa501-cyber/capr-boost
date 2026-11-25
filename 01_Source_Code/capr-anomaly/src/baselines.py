"""Baseline methods and a registry that builds any method by name."""
import copy
import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
import os

_NJ = int(os.environ.get("CAPR_NJOBS", "4"))

from .capr import CAPR
from .models import (Classifier, train_classifier, predict_proba, train_autoencoder,
                     recon_error, mlp_layers, to_tensor, class_weights)


class IForestMethod:
    prob_output = False

    def __init__(self, seed=0, **_):
        self.model = IsolationForest(n_estimators=200, contamination="auto",
                                     random_state=seed, n_jobs=_NJ)

    def fit(self, X_l, y_l, X_u, **_):
        self.model.fit(np.vstack([X_l, X_u]))
        return self

    def score(self, X):
        return -self.model.score_samples(X)


class OCSVMMethod:
    prob_output = False

    def __init__(self, seed=0, max_train=5000, **_):
        self.seed, self.max_train = seed, max_train
        self.model = OneClassSVM(kernel="rbf", gamma="scale", nu=0.1)

    def fit(self, X_l, y_l, X_u, **_):
        Xn = X_l[y_l == 0]
        if len(Xn) > self.max_train:
            Xn = Xn[np.random.RandomState(self.seed).choice(len(Xn), self.max_train, False)]
        self.model.fit(Xn)
        return self

    def score(self, X):
        return -self.model.decision_function(X)


class AEMethod:
    prob_output = False

    def __init__(self, model_cfg=None, device="cpu", **_):
        self.m, self.device = model_cfg, device

    def fit(self, X_l, y_l, X_u, **_):
        m = self.m
        self.ae = train_autoencoder(X_l[y_l == 0], m["ae_hidden"], m["ae_latent"],
                                    m["ae_epochs"], m["lr"], m["batch_size"], self.device,
                                    m["min_steps"])
        return self

    def score(self, X):
        return recon_error(self.ae, X, self.device)


class DeepSADMethod:
    """Deep SAD (Ruff et al., ICLR 2020): hypersphere; labeled anomalies pushed away."""
    prob_output = False

    def __init__(self, model_cfg=None, device="cpu", eta=1.0, rep_dim=32, **_):
        self.m, self.device, self.eta, self.rep_dim = model_cfg, device, eta, rep_dim

    def fit(self, X_l, y_l, X_u, **_):
        dev, m = self.device, self.m
        layers, d = mlp_layers(X_l.shape[1], m["hidden"][:2], 0.0, bias=False)
        self.net = nn.Sequential(*layers, nn.Linear(d, self.rep_dim, bias=False)).to(dev)
        X = to_tensor(np.vstack([X_l, X_u]), dev)
        s = to_tensor(np.concatenate([np.where(y_l == 0, 1.0, -1.0), np.zeros(len(X_u))]), dev)
        with torch.no_grad():
            c = self.net(X[:20000]).mean(0)
            c[(c.abs() < 0.1) & (c < 0)] = -0.1
            c[(c.abs() < 0.1) & (c >= 0)] = 0.1
        self.c = c
        opt = torch.optim.AdamW(self.net.parameters(), lr=m["lr"], weight_decay=1e-6)
        n, bs = len(X), m["batch_size"]
        epochs = max(m["ae_epochs"], math.ceil(m["min_steps"] / math.ceil(n / bs)))
        self.net.train()
        for _ in range(epochs):
            perm = torch.randperm(n, device=dev)
            for i in range(0, n, bs):
                idx = perm[i:i + bs]
                dist = ((self.net(X[idx]) - c) ** 2).sum(1)
                si = s[idx]
                loss = torch.where(si == 0, dist, self.eta * (dist + 1e-6) ** si).mean()
                opt.zero_grad()
                loss.backward()
                opt.step()
        self.net.eval()
        return self

    @torch.no_grad()
    def score(self, X):
        out = []
        for i in range(0, len(X), 8192):
            z = self.net(to_tensor(X[i:i + 8192], self.device))
            out.append(((z - self.c) ** 2).sum(1).cpu().numpy())
        return np.concatenate(out)


class SupervisedMethod:
    """Labeled data only (lower bound for semi-supervised methods)."""
    prob_output = True

    def __init__(self, in_dim, model_cfg=None, device="cpu", **_):
        self.m, self.device = model_cfg, device
        self.clf = Classifier(in_dim, model_cfg["hidden"], model_cfg["dropout"])

    def fit(self, X_l, y_l, X_u, **_):
        m = self.m
        train_classifier(self.clf, X_l, y_l, epochs=m["epochs_warmup"] * 2, lr=m["lr"],
                         batch_size=m["batch_size"], device=self.device,
                         min_steps=m["min_steps"] * 2)
        return self

    def score(self, X):
        return predict_proba(self.clf, X, self.device)[0]


class _SSLBase:
    prob_output = True

    def __init__(self, in_dim, model_cfg=None, device="cpu", ssl_epochs=10, **_):
        self.m, self.device, self.ssl_epochs = model_cfg, device, ssl_epochs
        self.model = Classifier(in_dim, model_cfg["hidden"], model_cfg["dropout"]).to(device)

    def _iter(self, X_l, y_l, X_u):
        dev, bs = self.device, self.m["batch_size"]
        Xl, yl, Xu = to_tensor(X_l, dev), to_tensor(y_l, dev, torch.long), to_tensor(X_u, dev)
        self.cw = to_tensor(class_weights(y_l), dev)
        bs_l = min(bs, len(Xl))
        steps = math.ceil(len(Xu) / bs)
        total = steps * self.ssl_epochs
        t = 0
        for _ in range(self.ssl_epochs):
            perm = torch.randperm(len(Xu), device=dev)
            for i in range(steps):
                li = torch.randint(0, len(Xl), (bs_l,), device=dev)
                yield Xl[li], yl[li], Xu[perm[i * bs:(i + 1) * bs]], t / max(1, total)
                t += 1

    def score(self, X):
        return predict_proba(self.model, X, self.device)[0]


class MeanTeacherMethod(_SSLBase):
    """Mean Teacher (Tarvainen & Valpola, NeurIPS 2017) adapted to tabular flows."""

    def fit(self, X_l, y_l, X_u, cons_weight=10.0, ema=0.99, noise=0.1, **_):
        student = self.model
        teacher = copy.deepcopy(student)
        for p in teacher.parameters():
            p.requires_grad_(False)
        opt = torch.optim.AdamW(student.parameters(), lr=self.m["lr"], weight_decay=1e-4)
        student.train(); teacher.train()
        for xl, yl, xu, prog in self._iter(X_l, y_l, X_u):
            w = cons_weight * math.exp(-5 * (1 - min(1.0, prog / 0.3)) ** 2)
            ls = F.cross_entropy(student(xl), yl, weight=self.cw)
            ps = F.softmax(student(xu + noise * torch.randn_like(xu)), 1)
            with torch.no_grad():
                pt = F.softmax(teacher(xu + noise * torch.randn_like(xu)), 1)
            loss = ls + w * F.mse_loss(ps, pt)
            opt.zero_grad(); loss.backward(); opt.step()
            with torch.no_grad():
                for pt_, ps_ in zip(teacher.parameters(), student.parameters()):
                    pt_.mul_(ema).add_(ps_, alpha=1 - ema)
        self.model = teacher.eval()
        return self


class FixMatchMethod(_SSLBase):
    """FixMatch (Sohn et al., NeurIPS 2020) with tabular weak/strong augmentations."""

    def fit(self, X_l, y_l, X_u, tau=0.95, lambda_u=1.0, **_):
        model = self.model
        opt = torch.optim.AdamW(model.parameters(), lr=self.m["lr"], weight_decay=1e-4)
        model.train()
        for xl, yl, xu, _ in self._iter(X_l, y_l, X_u):
            weak = xu + 0.05 * torch.randn_like(xu)
            strong = xu * (torch.rand_like(xu) > 0.2).float() + 0.2 * torch.randn_like(xu)
            with torch.no_grad():
                conf, pl = F.softmax(model(weak), 1).max(1)
                mask = (conf >= tau).float()
            ls = F.cross_entropy(model(xl), yl, weight=self.cw)
            lu = (F.cross_entropy(model(strong), pl, reduction="none") * mask).mean()
            loss = ls + lambda_u * lu
            opt.zero_grad(); loss.backward(); opt.step()
        model.eval()
        return self


class CAPRMethod:
    prob_output = True

    def __init__(self, in_dim, model_cfg=None, capr_cfg=None, device="cpu", **_):
        self.model = CAPR(in_dim, model_cfg, capr_cfg, device)

    def fit(self, X_l, y_l, X_u, y_u_true=None, y_l_true=None, **_):
        self.model.fit(X_l, y_l, X_u, y_u_true=y_u_true, y_l_true=y_l_true)
        return self

    def score(self, X):
        return self.model.score(X)


ABLATIONS = {
    "capr":             {},
    "capr_no_ae":       {"use_ae": False},
    "capr_no_unc":      {"use_uncertainty": False},
    "capr_no_adaptive": {"adaptive_threshold": False},
    "capr_no_gmm":      {"gmm_refine": False},
    "capr_no_refresh":  {"refresh_pseudo": False},
    "capr_no_balance":  {"balance_pseudo": False},
    "capr_no_reweight": {"weight_labeled_noise": False},
    "capr_plus_gate":   {"confident_gate": True},
    "capr_plus_relae":  {"ae_reliability": True},
    "pseudo_label":     {"use_ae": False, "use_uncertainty": False, "adaptive_threshold": False,
                         "gmm_refine": False, "refresh_pseudo": False, "balance_pseudo": False,
                         "tau_base": 0.95},
}

DISPLAY_NAMES = {
    "iforest": "Isolation Forest", "ocsvm": "One-Class SVM", "autoencoder": "Autoencoder",
    "deep_sad": "Deep SAD", "supervised": "Supervised MLP", "pseudo_label": "Pseudo-Label",
    "mean_teacher": "Mean Teacher", "fixmatch": "FixMatch", "capr": "CAPR-Net (ours)",
    "capr_no_ae": "w/o dual-view (AE)", "capr_no_unc": "w/o MC-Dropout uncertainty",
    "capr_no_adaptive": "w/o adaptive threshold", "capr_no_gmm": "w/o GMM refinement",
    "capr_no_refresh": "w/o pseudo-label refresh",
    "capr_no_balance": "w/o distribution alignment",
    "capr_no_reweight": "w/o labeled-noise reweighting",
    "capr_plus_gate": "+ confident-learning gate (no gain)",
    "capr_plus_relae": "+ AE reliability gate (no gain)",
}


def build_method(name, in_dim, cfg, device, seed):
    m, c = cfg["model"], cfg["capr"]
    ssl_epochs = cfg.get("ssl_epochs", 10)
    if name == "iforest":
        return IForestMethod(seed=seed)
    if name == "ocsvm":
        return OCSVMMethod(seed=seed)
    if name == "autoencoder":
        return AEMethod(model_cfg=m, device=device)
    if name == "deep_sad":
        return DeepSADMethod(model_cfg=m, device=device)
    if name == "supervised":
        return SupervisedMethod(in_dim, model_cfg=m, device=device)
    if name == "mean_teacher":
        return MeanTeacherMethod(in_dim, model_cfg=m, device=device, ssl_epochs=ssl_epochs)
    if name == "fixmatch":
        return FixMatchMethod(in_dim, model_cfg=m, device=device, ssl_epochs=ssl_epochs)
    if name in ABLATIONS:
        return CAPRMethod(in_dim, model_cfg=m, capr_cfg={**c, **ABLATIONS[name]}, device=device)
    raise ValueError(f"Unknown method: {name}")


class TreeMethod:
    prob_output = True

    def __init__(self, kind, seed=0, **_):
        import lightgbm as lgb
        import xgboost as xgb
        from sklearn.ensemble import RandomForestClassifier
        if kind == "lgbm":
            self.model = lgb.LGBMClassifier(n_estimators=500, learning_rate=0.04, num_leaves=63,
                                            min_child_samples=5, subsample=0.8, subsample_freq=1,
                                            colsample_bytree=0.7, random_state=seed, n_jobs=_NJ,
                                            verbose=-1)
        elif kind == "xgb":
            self.model = xgb.XGBClassifier(n_estimators=500, learning_rate=0.05, max_depth=8,
                                           subsample=0.8, colsample_bytree=0.7,
                                           tree_method="hist", random_state=seed, n_jobs=_NJ)
        else:
            self.model = RandomForestClassifier(n_estimators=300, n_jobs=_NJ, random_state=seed)

    def fit(self, X_l, y_l, X_u, **_):
        self.model.fit(X_l, y_l)
        return self

    def score(self, X):
        return self.model.predict_proba(X)[:, 1]


class TreeSelfTraining:
    prob_output = True

    def __init__(self, seed=0, rounds=3, tau=0.95, **_):
        self.seed, self.rounds, self.tau = seed, rounds, tau

    def fit(self, X_l, y_l, X_u, **_):
        base = TreeMethod("lgbm", self.seed)
        Xa, ya = X_l, y_l
        for _ in range(self.rounds):
            base = TreeMethod("lgbm", self.seed).fit(Xa, ya, None)
            p = base.score(X_u)
            keep = np.maximum(p, 1 - p) >= self.tau
            Xa = np.vstack([X_l, X_u[keep]])
            ya = np.r_[y_l, (p[keep] >= 0.5).astype(int)]
        self.model = TreeMethod("lgbm", self.seed).fit(Xa, ya, None)
        return self

    def score(self, X):
        return self.model.score(X)


class CAPRBoostMethod:
    prob_output = True

    def __init__(self, cfg=None, seed=0, **_):
        from .capr_boost import CAPRBoost
        self.model = CAPRBoost(cfg, seed)

    def fit(self, X_l, y_l, X_u, **_):
        self.model.fit(X_l, y_l, X_u)
        return self

    def score(self, X):
        return self.model.score(X)


BOOST_ABLATIONS = {
    "capr_boost":            {},
    "capr_boost_no_refine":  {"refine": False},
    "capr_boost_no_pseudo":  {"pseudo": False},
    "capr_boost_no_select":  {"select": False},
    "capr_boost_single":     {"n_models": 1},
}

DISPLAY_NAMES.update({
    "rf": "Random Forest", "xgb": "XGBoost", "lgbm": "LightGBM",
    "lgbm_selftrain": "LightGBM self-training", "capr": "CAPR-Net v1 (MLP)",
    "capr_boost": "CAPR-Boost (proposed)", "capr_boost_no_refine": "w/o noise refinement",
    "capr_boost_no_pseudo": "w/o pseudo-labelling", "capr_boost_no_select": "w/o CV variant selection",
    "capr_boost_single": "single model (no ensemble)",
})

_build_method_v1 = build_method


def build_method(name, in_dim, cfg, device, seed):
    if name in ("rf", "xgb", "lgbm"):
        return TreeMethod(name, seed)
    if name == "lgbm_selftrain":
        return TreeSelfTraining(seed)
    if name in BOOST_ABLATIONS:
        return CAPRBoostMethod({**cfg.get("boost", {}), **BOOST_ABLATIONS[name]}, seed)
    return _build_method_v1(name, in_dim, cfg, device, seed)
