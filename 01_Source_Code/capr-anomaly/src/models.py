"""Neural building blocks + generic training / inference helpers (PyTorch)."""
import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def mlp_layers(in_dim, hidden, dropout=0.0, bias=True):
    layers, d = [], in_dim
    for h in hidden:
        layers += [nn.Linear(d, h, bias=bias), nn.ReLU()]
        if dropout > 0:
            layers.append(nn.Dropout(dropout))
        d = h
    return layers, d


class Classifier(nn.Module):
    """MLP with dropout. Dropout doubles as a Bayesian approximation for MC-Dropout."""

    def __init__(self, in_dim, hidden=(256, 128, 64), dropout=0.2):
        super().__init__()
        layers, d = mlp_layers(in_dim, hidden, dropout)
        self.body = nn.Sequential(*layers)
        self.head = nn.Linear(d, 2)

    def forward(self, x):
        return self.head(self.body(x))


class AutoEncoder(nn.Module):
    def __init__(self, in_dim, hidden=(128, 64), latent=16):
        super().__init__()
        enc, d = mlp_layers(in_dim, list(hidden))
        self.encoder = nn.Sequential(*enc, nn.Linear(d, latent))
        dec, d2 = mlp_layers(latent, list(reversed(hidden)))
        self.decoder = nn.Sequential(*dec, nn.Linear(d2, in_dim))

    def forward(self, x):
        return self.decoder(self.encoder(x))


def to_tensor(X, device, dtype=torch.float32):
    return torch.as_tensor(np.asarray(X), dtype=dtype, device=device)


def class_weights(y):
    counts = np.bincount(np.asarray(y, dtype=int), minlength=2).astype(float)
    counts[counts == 0] = 1.0
    return counts.sum() / (2.0 * counts)


def train_classifier(model, X, y, sample_w=None, epochs=10, lr=1e-3, batch_size=512,
                     device="cpu", optimizer=None, min_steps=300, weight_decay=1e-4):
    """Class-balanced, sample-weighted cross-entropy training. Returns the optimizer."""
    model.to(device)
    if optimizer is None:
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    y = np.asarray(y, dtype=int)
    w = class_weights(y)[y]
    if sample_w is not None:
        w = w * np.asarray(sample_w, dtype=float)
    Xt, yt = to_tensor(X, device), to_tensor(y, device, torch.long)
    wt = to_tensor(w, device)
    n = len(Xt)
    steps_per_epoch = max(1, math.ceil(n / batch_size))
    epochs = max(epochs, math.ceil(min_steps / steps_per_epoch))
    model.train()
    for _ in range(epochs):
        perm = torch.randperm(n, device=device)
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            loss_vec = F.cross_entropy(model(Xt[idx]), yt[idx], reduction="none")
            loss = (loss_vec * wt[idx]).sum() / wt[idx].sum().clamp_min(1e-8)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    model.eval()
    return optimizer


@torch.no_grad()
def predict_proba(model, X, device="cpu", mc_passes=1, batch_size=8192):
    """P(anomaly). With mc_passes>1 dropout stays active -> returns (mean, std) over passes."""
    model.to(device)
    model.train() if mc_passes > 1 else model.eval()
    chunks = []
    for i in range(0, len(X), batch_size):
        xb = to_tensor(X[i:i + batch_size], device)
        ps = torch.stack([F.softmax(model(xb), dim=1)[:, 1] for _ in range(mc_passes)])
        chunks.append(ps.cpu().numpy())
    model.eval()
    P = np.concatenate(chunks, axis=1)
    return P.mean(0), P.std(0)


@torch.no_grad()
def per_sample_loss(model, X, y, device="cpu", batch_size=8192):
    model.eval()
    out = []
    for i in range(0, len(X), batch_size):
        xb = to_tensor(X[i:i + batch_size], device)
        yb = to_tensor(y[i:i + batch_size], device, torch.long)
        out.append(F.cross_entropy(model(xb), yb, reduction="none").cpu().numpy())
    return np.concatenate(out)


def train_autoencoder(X, hidden=(128, 64), latent=16, epochs=30, lr=1e-3, batch_size=512,
                      device="cpu", min_steps=300):
    ae = AutoEncoder(X.shape[1], hidden, latent).to(device)
    opt = torch.optim.AdamW(ae.parameters(), lr=lr, weight_decay=1e-5)
    Xt = to_tensor(X, device)
    n = len(Xt)
    epochs = max(epochs, math.ceil(min_steps / max(1, math.ceil(n / batch_size))))
    ae.train()
    for _ in range(epochs):
        perm = torch.randperm(n, device=device)
        for i in range(0, n, batch_size):
            xb = Xt[perm[i:i + batch_size]]
            loss = F.mse_loss(ae(xb), xb)
            opt.zero_grad()
            loss.backward()
            opt.step()
    ae.eval()
    return ae


@torch.no_grad()
def recon_error(ae, X, device="cpu", batch_size=8192):
    ae.eval()
    out = []
    for i in range(0, len(X), batch_size):
        xb = to_tensor(X[i:i + batch_size], device)
        out.append(((ae(xb) - xb) ** 2).mean(1).cpu().numpy())
    return np.concatenate(out)
