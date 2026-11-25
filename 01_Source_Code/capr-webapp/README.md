# CAPR-Net Web Application

Full-stack application for the CAPR-Boost encrypted-traffic anomaly detector. An analyst uploads a
CICFlowMeter CSV (or a raw PCAP), every flow is scored with an anomaly probability and an
ensemble uncertainty, anomalous flows are explained with TreeSHAP feature contributions, and
alerts are pushed live to an Angular dashboard.

## Architecture

```
Browser ──> Angular 18 dashboard (nginx, :4200)
              │  /api, /hubs
              ▼
           ASP.NET Core 8 API (:8080) ──HTTP──> FastAPI ML service (:8000)
              │  Dapper + T-SQL, SignalR                LightGBM ensemble, TreeSHAP, NFStream
              ▼
           SQL Server 2022 (:1433)
```

| Folder | Technology |
|---|---|
| `ml-service/` | Python 3.13, FastAPI, LightGBM, scikit-learn, NFStream |
| `backend/` | .NET 8, ASP.NET Core Web API, Dapper, SignalR, PBKDF2 password hashing |
| `frontend/capr-dashboard/` | Angular 18, Angular Material, Chart.js, SignalR client |
| `database/schema.sql` | SQL Server schema (idempotent, safe to re-run) |
| `sample-data/` | 1,500-flow samples taken only from the held-out test split, for demos |

## Option A: run everything with Docker (recommended)

```bash
cp .env.example .env            # Windows: copy .env.example .env
# edit .env: MSSQL_SA_PASSWORD, ADMIN_PASSWORD, ML_SERVICE_API_KEY
docker compose up -d --build
docker compose ps               # every service should be healthy
```

Open http://localhost:4200 and sign in with `admin@capr.local` and the `ADMIN_PASSWORD` from `.env`.
Stop with `docker compose down` (data stays in the `mssql-data` volume); `docker compose down -v`
removes the data as well.

What the compose setup provides:

- Health checks on every service. The API waits for a healthy database, a finished schema
  migration (`db-init`) and a healthy ML service; the frontend waits for a healthy API.
- Only the frontend port (4200) is published on all interfaces. SQL Server, the ML service and the
  API are bound to 127.0.0.1.
- The ML service and the API run as non-root users. Container logs rotate at 10 MB x 3 files.
- Login, forgot-password and reset endpoints are rate-limited per client IP (30 requests/minute).
- `GET /health` on the API checks the database connection; the ML service has its own `/health`.
- nginx serves the Angular build with gzip, long-lived caching for hashed assets and security
  headers (nosniff, frame deny, referrer and permissions policy).
- The schema script is idempotent and runs on every start without deleting data.

### Using a model trained in Google Colab

The Colab notebook (`08_Colab_Demo/CAPR_Boost_Colab_Demo.ipynb`, Part C) downloads
`capr_models.zip`. Extract it into `ml-service/artifacts/` so that
`artifacts/<dataset>/capr_boost_model.joblib`, `meta.json`, `preprocessor.json` and
`feature_importance.csv` are replaced, then:

```bash
docker compose restart ml-service
```

and click **Models -> Sync from ml-service** in the web app. The artifacts folder is mounted
read-only into the container, so no image rebuild is needed.

## Option B: run each part manually (Windows / Linux / macOS)

Prerequisites: Python 3.11+, .NET 8 SDK, Node.js 20+, SQL Server (Express or Developer edition, or
the Docker image).

1. **Database**
   ```bash
   sqlcmd -S localhost -U sa -P <password> -C -i database/schema.sql
   ```
2. **ML service**
   ```bash
   cd ml-service
   python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --port 8000
   ```
3. **Backend API** (new terminal)
   ```bash
   cd backend/src/CaprApi
   set ConnectionStrings__CaprDb=Server=localhost,1433;Database=CaprDb;User Id=sa;Password=<password>;TrustServerCertificate=True;
   set AdminSeed__Password=Admin@12345
   set ASPNETCORE_URLS=http://localhost:5080
   dotnet run
   ```
   (On Linux/macOS use `export NAME=value` instead of `set`.)
4. **Frontend** (new terminal)
   ```bash
   cd frontend/capr-dashboard
   npm install
   npm start
   ```
   Open http://localhost:4200.

## Demo script (for the viva)

1. Sign in as admin. The dashboard shows the two active models and their test accuracy.
2. **Uploads → Upload CSV**, choose `darknet2020`, select `sample-data/darknet2020_test_sample.csv`.
3. Open the upload, click an anomalous flow and show the SHAP explanation panel.
4. **Alerts**: acknowledge or resolve an alert (status is stored in SQL Server).
5. **Models / Research**: compare methods. Import `capr-anomaly/results/report/raw_results_all.csv`
   on the Research page to load every experiment run.
6. **Forgot password**: sign out, click *Forgot password?*, enter an email, use the 6-digit code,
   set a new password. Without SMTP settings the code is shown on screen (demo mode); with SMTP
   configured in `.env` it is emailed.

## Security features

- PBKDF2 password hashing (ASP.NET Core `PasswordHasher`), role-based access (Admin, Analyst, Viewer).
- Forgot password with 6-digit one-time code: SHA-256 hashed at rest, 15-minute expiry,
  5 attempts per code, 3 requests per 15 minutes, no user enumeration.
- Change password for signed-in users; password policy of 8+ characters with letters and digits.
- Audit log table (`dbo.AuditEvents`) for logins, failed logins and password events.
- Optional shared API key between the backend and the ML service.

## Tests

```bash
cd ml-service && python test_smoke.py          # 11 API checks against the real trained models
cd backend && dotnet build                      # compiles the API
cd frontend/capr-dashboard && npx ng build      # production build with strict templates
```
