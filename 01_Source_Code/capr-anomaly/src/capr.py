"""CAPR-Net v1: confidence-aware pseudo-label refinement with an MLP backbone."""
import numpy as np
import joblib
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import roc_auc_score

from .models import (Classifier, train_classifier, predict_proba, per_sample_loss,
                     train_autoencoder, recon_error, AutoEncoder)

DEFAULT_CAPR = dict(rounds=5, mc_passes=10, alpha=0.6, tau_base=0.95, tau_min=0.70,
                    lambda_unc=1.0, gmm_clean_threshold=0.5, use_ae=True,
                    use_uncertainty=True, adaptive_threshold=True, gmm_refine=True,
                    refresh_pseudo=True, balance_pseudo=True, oof_folds=5,
                    label_correction=False, score_mode="classifier",
                    confident_gate=False, agree_floor=0.85, min_label_weight=0.1,
                    ae_reliability=False, ae_min_auc=0.55, weight_labeled_noise=True)
DEFAULT_MODEL = dict(hidden=[256, 128, 64], dropout=0.2, lr=1e-3, batch_size=512,
                     epochs_warmup=20, epochs_per_round=8, min_steps=300,
                     ae_hidden=[128, 64], ae_latent=16, ae_epochs=30)


class CAPR:
    prob_output = True

    def __init__(self, in_dim, model_cfg=None, capr_cfg=None, device="cpu", verbose=False):
        self.in_dim = in_dim
        self.m = {**DEFAULT_MODEL, **(model_cfg or {})}
        self.c = {**DEFAULT_CAPR, **(capr_cfg or {})}
        self.device = device
        self.verbose = verbose
        self.history = []
        self.ae, self.cal, self.clf = None, None, None

    def _fit_ae(self, X_l, y_l):
        X_norm = X_l[y_l == 0]
        m = self.m
        self.ae = train_autoencoder(X_norm, m["ae_hidden"], m["ae_latent"], m["ae_epochs"],
                                    m["lr"], m["batch_size"], self.device, m["min_steps"])
        err = np.log1p(recon_error(self.ae, X_l, self.device)).reshape(-1, 1)
        if len(np.unique(y_l)) == 2:
            self.cal = LogisticRegression(class_weight="balanced").fit(err, y_l)
        else:
            self.cal = np.sort(err.ravel())

    def _p_ae(self, X):
        err = np.log1p(recon_error(self.ae, X, self.device)).reshape(-1, 1)
        if isinstance(self.cal, LogisticRegression):
            return self.cal.predict_proba(err)[:, 1]
        return np.searchsorted(self.cal, err.ravel()) / len(self.cal)

    def _ae_reliability_check(self, X_l, y_l):
        """Fit the AE on an inner split and measure its held-out reconstruction AUC."""
        if len(np.unique(y_l)) < 2 or min(np.bincount(y_l, minlength=2)) < 10:
            return True
        Xa, Xb, ya, yb = train_test_split(X_l, y_l, test_size=0.3, stratify=y_l, random_state=0)
        m = self.m
        ae_probe = train_autoencoder(Xa[ya == 0], m["ae_hidden"], m["ae_latent"],
                                     max(10, m["ae_epochs"] // 2), m["lr"], m["batch_size"],
                                     self.device, m["min_steps"] // 2)
        err = recon_error(ae_probe, Xb, self.device)
        auc = roc_auc_score(yb, err)
        auc = max(auc, 1 - auc)
        self.ae_auc = float(auc)
        return auc >= self.c["ae_min_auc"]

    def _thresholds(self, pred, conf):
        tb, tmin = self.c["tau_base"], self.c["tau_min"]
        if not self.c["adaptive_threshold"]:
            return np.array([tb, tb])
        effect = np.array([
            np.mean(conf[pred == k] >= tb) if np.any(pred == k) else 0.0 for k in (0, 1)
        ])
        beta = effect / effect.max() if effect.max() > 0 else np.zeros(2)
        mapped = beta / (2.0 - beta)
        return np.maximum(tmin, tb * mapped)

    @staticmethod
    def _gmm_clean_prob(loss, y):
        clean = np.ones(len(loss))
        for k in (0, 1):
            idx = np.where(y == k)[0]
            if len(idx) < 20:
                continue
            l = loss[idx]
            l = (l - l.min()) / (l.max() - l.min() + 1e-12)
            if l.std() < 1e-6:
                continue
            gmm = GaussianMixture(2, max_iter=30, reg_covar=5e-4, random_state=0)
            gmm.fit(l.reshape(-1, 1))
            clean_comp = int(np.argmin(gmm.means_.ravel()))
            clean[idx] = gmm.predict_proba(l.reshape(-1, 1))[:, clean_comp]
        return clean

    def _oof_clean_prob(self, X_l, y_l):
        """Out-of-fold loss: each labeled sample is scored by a model that never saw it."""
        m, k = self.m, self.c["oof_folds"]
        if np.bincount(y_l, minlength=2).min() < k:
            return np.ones(len(y_l)), None
        loss, p_oof = np.zeros(len(y_l)), np.zeros(len(y_l))
        for tr, va in StratifiedKFold(k, shuffle=True, random_state=0).split(X_l, y_l):
            clf = Classifier(self.in_dim, m["hidden"], m["dropout"])
            train_classifier(clf, X_l[tr], y_l[tr], epochs=m["epochs_warmup"], lr=m["lr"],
                             batch_size=m["batch_size"], device=self.device,
                             min_steps=m["min_steps"])
            loss[va] = per_sample_loss(clf, X_l[va], y_l[va], self.device)
            p_oof[va] = predict_proba(clf, X_l[va], self.device)[0]
        return self._gmm_clean_prob(loss, y_l), p_oof

    @staticmethod
    def _balance(idx, lab, conf, prior):
        """Distribution alignment: keep pseudo-labels per class in proportion to the class prior."""
        counts = np.array([np.sum(lab == k) for k in (0, 1)])
        if counts.min() == 0:
            return idx, lab, conf
        total = int(np.min(counts / np.clip(prior, 1e-6, None)))
        keep = []
        for k in (0, 1):
            ck = np.where(lab == k)[0]
            q = max(1, int(round(total * prior[k])))
            keep.append(ck[np.argsort(-conf[ck])[:q]])
        keep = np.sort(np.concatenate(keep))
        return idx[keep], lab[keep], conf[keep]

    def fit(self, X_l, y_l, X_u, y_u_true=None, y_l_true=None):
        c, m, dev = self.c, self.m, self.device
        y_work = np.asarray(y_l, dtype=int).copy()
        n_l, n_u = len(X_l), len(X_u)

        self.ae_active = False
        if c["use_ae"]:
            self.ae_active = self._ae_reliability_check(X_l, y_work) if c["ae_reliability"] else True
            self._fit_ae(X_l, y_work)
            p_ae_u = self._p_ae(X_u) if self.ae_active else None

        w_l = np.ones(n_l)
        if c["gmm_refine"] and c["weight_labeled_noise"]:
            clean_l, p_oof = self._oof_clean_prob(X_l, y_work)
            if c["confident_gate"] and p_oof is not None:
                agree = (p_oof >= 0.5).astype(int) == y_work
                clean_l = np.where(agree, np.maximum(clean_l, c["agree_floor"]), clean_l)
            w_l = np.maximum(clean_l, c["min_label_weight"])
            if c["label_correction"] and p_oof is not None:
                pred_o = (p_oof >= 0.5).astype(int)
                flip = (clean_l < c["gmm_clean_threshold"]) & (pred_o != y_work) & \
                       (np.maximum(p_oof, 1 - p_oof) >= c["tau_base"])
                y_work[flip] = pred_o[flip]
                w_l[flip] = 1.0
                self.n_corrected = int(flip.sum())
        prior = np.array([w_l[y_work == k].sum() for k in (0, 1)])
        prior = prior / prior.sum()

        self.clf = Classifier(self.in_dim, m["hidden"], m["dropout"]).to(dev)
        opt = train_classifier(self.clf, X_l, y_work, w_l, epochs=m["epochs_warmup"],
                               lr=m["lr"], batch_size=m["batch_size"], device=dev,
                               min_steps=m["min_steps"])

        acc_idx = np.array([], dtype=int)
        acc_lab = np.array([], dtype=int)
        acc_conf = np.array([], dtype=float)

        for r in range(1, c["rounds"] + 1):
            T = c["mc_passes"] if c["use_uncertainty"] else 1
            p_c, std = predict_proba(self.clf, X_u, dev, mc_passes=T)
            if c["use_ae"] and self.ae_active:
                p = c["alpha"] * p_c + (1 - c["alpha"]) * p_ae_u
                agree = (p_c >= 0.5) == (p_ae_u >= 0.5)
            else:
                p, agree = p_c, np.ones(n_u, dtype=bool)
            pred = (p >= 0.5).astype(int)
            conf = np.maximum(p, 1 - p)
            if c["use_uncertainty"]:
                conf = np.clip(conf - c["lambda_unc"] * std, 0.0, 1.0)

            tau = self._thresholds(pred, conf)
            sel = agree & (conf >= tau[pred])

            if c["refresh_pseudo"]:
                idx, lab, cf = np.where(sel)[0], pred[sel], conf[sel]
                if c["balance_pseudo"]:
                    idx, lab, cf = self._balance(idx, lab, cf, prior)
            else:
                new = sel & ~np.isin(np.arange(n_u), acc_idx)
                if c["balance_pseudo"]:
                    ni, nl_, nc = self._balance(np.where(new)[0], pred[new], conf[new], prior)
                    new = np.zeros(n_u, dtype=bool); new[ni] = True
                acc_idx = np.concatenate([acc_idx, np.where(new)[0]])
                acc_lab = np.concatenate([acc_lab, pred[new]])
                acc_conf = np.concatenate([acc_conf, conf[new]])
                idx, lab, cf = acc_idx, acc_lab, acc_conf

            X_tr = np.vstack([X_l, X_u[idx]])
            y_tr = np.concatenate([y_work, lab]).astype(int)
            w_tr = np.concatenate([np.ones(n_l), cf])
            keep = np.ones(len(y_tr), dtype=bool)
            n_drop = 0

            w_tr[:n_l] = w_l
            if c["gmm_refine"] and len(idx):
                loss_p = per_sample_loss(self.clf, X_u[idx], lab, dev)
                clean_p = self._gmm_clean_prob(loss_p, lab)
                keep[n_l:] = clean_p >= c["gmm_clean_threshold"]
                w_tr[n_l:] *= clean_p
                n_drop = int((~keep[n_l:]).sum())

            train_classifier(self.clf, X_tr[keep], y_tr[keep], w_tr[keep],
                             epochs=m["epochs_per_round"], batch_size=m["batch_size"],
                             device=dev, optimizer=opt, min_steps=m["min_steps"] // 2)

            kept_idx, kept_lab = idx[keep[n_l:]], y_tr[n_l:][keep[n_l:]]
            rec = dict(round=r, n_pseudo=len(kept_idx), n_dropped=n_drop,
                       tau_normal=float(tau[0]), tau_anomaly=float(tau[1]),
                       ae_active=bool(self.ae_active), ae_auc=getattr(self, "ae_auc", None),
                       pseudo_anomaly_frac=float(kept_lab.mean()) if len(kept_lab) else 0.0,
                       pseudo_label_acc=(float(np.mean(kept_lab == y_u_true[kept_idx]))
                                         if y_u_true is not None and len(kept_idx) else None),
                       labeled_noise_rate=(float(np.mean(y_work != y_l_true))
                                           if y_l_true is not None else None),
                       effective_noise_rate=(float(np.sum(w_l * (y_work != y_l_true)) / w_l.sum())
                                             if y_l_true is not None else None))
            self.history.append(rec)
            if self.verbose:
                print("   ", rec, flush=True)
        return self

    def score(self, X):
        p_c, _ = predict_proba(self.clf, X, self.device)
        if self.c["use_ae"] and self.ae_active and self.c["score_mode"] == "fused":
            return self.c["alpha"] * p_c + (1 - self.c["alpha"]) * self._p_ae(X)
        return p_c

    def predict(self, X, threshold=0.5):
        return (self.score(X) >= threshold).astype(int)

    def predict_with_confidence(self, X, mc_passes=None):
        """For deployment: anomaly probability + MC-Dropout uncertainty per flow."""
        T = mc_passes or self.c["mc_passes"]
        p_c, std = predict_proba(self.clf, X, self.device, mc_passes=T)
        if self.c["use_ae"] and self.ae_active and self.c["score_mode"] == "fused":
            p = self.c["alpha"] * p_c + (1 - self.c["alpha"]) * self._p_ae(X)
        else:
            p = p_c
        return p, std

    def save(self, path):
        joblib.dump({
            "in_dim": self.in_dim, "m": self.m, "c": self.c, "cal": self.cal,
            "clf": {k: v.cpu() for k, v in self.clf.state_dict().items()},
            "ae": {k: v.cpu() for k, v in self.ae.state_dict().items()} if self.ae else None,
            "history": self.history, "ae_active": getattr(self, "ae_active", False),
            "ae_auc": getattr(self, "ae_auc", None),
        }, path)

    @classmethod
    def load(cls, path, device="cpu"):
        d = joblib.load(path)
        obj = cls(d["in_dim"], d["m"], d["c"], device)
        obj.clf = Classifier(d["in_dim"], d["m"]["hidden"], d["m"]["dropout"])
        obj.clf.load_state_dict(d["clf"])
        obj.clf.to(device).eval()
        if d["ae"] is not None:
            obj.ae = AutoEncoder(d["in_dim"], d["m"]["ae_hidden"], d["m"]["ae_latent"])
            obj.ae.load_state_dict(d["ae"])
            obj.ae.to(device).eval()
        obj.cal, obj.history = d["cal"], d["history"]
        obj.ae_active = d.get("ae_active", d["ae"] is not None)
        obj.ae_auc = d.get("ae_auc")
        return obj
