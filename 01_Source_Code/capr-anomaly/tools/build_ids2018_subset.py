import sys, glob, numpy as np, pandas as pd
src, out = sys.argv[1], sys.argv[2]
rng = np.random.RandomState(7)
parts = []
for f in sorted(glob.glob(f"{src}/*.csv")):
    d = pd.read_csv(f, low_memory=False)
    d = d[d["Label"] != "Label"]
    d = d.drop(columns=["Timestamp"])
    feats = [c for c in d.columns if c not in ("Label", "Dst Port", "Protocol")]
    d[feats] = d[feats].apply(pd.to_numeric, errors="coerce")
    d = d.replace([np.inf, -np.inf], np.nan).dropna()
    d = d.drop_duplicates(subset=feats)
    for lab, g in d.groupby("Label"):
        n = 50000 if lab == "Benign" else 10000
        parts.append(g.sample(min(n, len(g)), random_state=rng))
    print(f, flush=True)
df = pd.concat(parts, ignore_index=True).sample(frac=1, random_state=7)
feats = [c for c in df.columns if c not in ("Label", "Dst Port", "Protocol")]
df = df.drop_duplicates(subset=feats)
print(df.Label.value_counts())
df.to_csv(out, index=False, compression="gzip")
