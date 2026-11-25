# ML Service

FastAPI service that serves the trained CAPR-Boost models in `artifacts/<dataset>/`.

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000      # Swagger UI at http://localhost:8000/docs
python test_smoke.py
```

| Endpoint | Purpose |
|---|---|
| `GET /health`, `GET /models` | loaded models and their test metrics |
| `POST /predict` | JSON feature vectors |
| `POST /predict/csv` | CICFlowMeter CSV upload |
| `POST /predict/pcap` | raw PCAP, features extracted with NFStream (approximate) |
| `POST /explain` | TreeSHAP top-k feature contributions for one flow |
| `POST /models/reload` | reload artifacts without restarting |

To deploy a newly trained model, copy `capr-anomaly/artifacts/<dataset>/` here and call
`POST /models/reload`, then press *Sync from ml-service* on the Models page.
