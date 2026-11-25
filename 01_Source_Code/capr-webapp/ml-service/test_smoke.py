import io
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("CAPR_ARTIFACTS_DIR", os.path.join(os.path.dirname(__file__), "artifacts"))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FAILURES = []


def check(name, cond, detail=""):
    print(f"[{'OK  ' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def main():
    r = client.get("/health")
    check("GET /health", r.status_code == 200, r.text)
    loaded = r.json().get("datasets_loaded", [])
    check("darknet2020 model loaded", "darknet2020" in loaded, loaded)

    models = {m["dataset"]: m for m in client.get("/models").json()}
    m = models.get("darknet2020")
    check("GET /models lists darknet2020", m is not None)
    check("model reports accuracy", m and m["test_accuracy"] is not None)
    feats = m["features"]
    x = np.abs(np.random.RandomState(0).randn(len(feats)) * 50).tolist()

    r = client.post("/predict", json={"dataset": "darknet2020", "flows": [{"flow_id": "a", "features": x}]})
    check("POST /predict", r.status_code == 200, r.text)
    res = r.json()["results"][0]
    check("probability in [0,1]", 0 <= res["anomaly_probability"] <= 1)
    check("uncertainty returned", res["uncertainty"] is not None)

    r = client.post("/predict", json={"dataset": "darknet2020", "flows": [{"features": x[:5]}]})
    check("wrong feature count -> 422", r.status_code == 422)
    r = client.post("/predict", json={"dataset": "nope", "flows": [{"features": x}]})
    check("unknown dataset -> 404", r.status_code == 404)

    df = pd.DataFrame([x, x], columns=feats)
    df.insert(0, "Flow ID", ["f1", "f2"])
    r = client.post("/predict/csv", data={"dataset": "darknet2020"},
                    files={"file": ("t.csv", io.BytesIO(df.to_csv(index=False).encode()), "text/csv")})
    check("POST /predict/csv", r.status_code == 200 and len(r.json()["results"]) == 2, r.text)

    r = client.post("/explain", json={"dataset": "darknet2020", "features": x, "top_k": 5})
    check("POST /explain", r.status_code == 200 and len(r.json()["top_features"]) == 5, r.text)

    print(f"\n{len(FAILURES)} failure(s)")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
