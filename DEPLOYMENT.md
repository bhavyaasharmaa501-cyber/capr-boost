# Deployment Guide

The project has four parts. They need different kinds of hosting:

| Part | Technology | Where it runs |
|------|-----------|---------------|
| Dashboard (UI) | Angular 18 | **GitHub Pages** (automatic, free) |
| REST API | ASP.NET Core 8 | Render (Docker, free plan) |
| ML inference service | Python FastAPI + LightGBM | Render (Docker, free plan) |
| Database | SQL Server | Azure SQL Database (free offer) |

GitHub Pages can only host static files (HTML/CSS/JS). That is why the dashboard is
published there in **demo mode**: it runs fully in the browser using the real trained
model results (`public/demo/data.json`, generated from `06_Results/` and the model
`meta.json` files). Login, forgot password, dashboard, uploads, alerts, models, research
comparison and user management all work in the demo.

Demo login: `admin@capr.local` / `Admin@12345` (forgot-password code in demo: `482913`).

---

## 1. Dashboard on GitHub Pages (already configured)

The workflow `.github/workflows/deploy-pages.yml` builds the Angular app with
`--configuration demo` and publishes it on every push to `main`.

One-time setup:
1. Repository **Settings -> Pages -> Build and deployment -> Source: GitHub Actions**.
2. GitHub Pages on a free account needs a **public** repository
   (Settings -> General -> Danger Zone -> Change visibility -> Public).
3. Actions tab -> "Deploy dashboard to GitHub Pages" -> **Run workflow**.

Live URL: `https://<your-username>.github.io/<repo-name>/`

## 2. Full stack (optional, for a live backend)

### 2a. Database: Azure SQL (free)
1. https://portal.azure.com -> Create **SQL Database** -> apply the *free database offer*.
2. Networking: allow Azure services and your IP.
3. Open *Query editor* and run `01_Source_Code/capr-webapp/database/schema.sql`.
4. Copy the ADO.NET connection string.

### 2b. ML service + API: Render
1. https://render.com -> sign in with GitHub -> **New -> Blueprint** -> pick this repo.
   Render reads `render.yaml` and creates `capr-ml-service` and `capr-api`.
2. Fill the variables Render asks for:
   - `ConnectionStrings__CaprDb` = Azure SQL connection string
   - `MlService__BaseUrl` = URL of `capr-ml-service` (e.g. `https://capr-ml-service.onrender.com`)
   - `AdminSeed__Password` = admin password of your choice
   - `Cors__AllowedOrigins__0` = `https://<your-username>.github.io`
3. Check `https://capr-api.onrender.com/health` returns `healthy`.

Free Render services sleep after 15 minutes idle; the first request takes ~1 minute.

### 2c. Point the dashboard at the live API
In `01_Source_Code/capr-webapp/frontend/capr-dashboard/src/environments/environment.demo.ts` set:

```ts
export const environment = {
  production: true,
  demo: false,
  apiBaseUrl: 'https://capr-api.onrender.com/api',
  hubUrl: 'https://capr-api.onrender.com/hubs/alerts',
};
```

Commit and push; GitHub Actions redeploys the dashboard.

## 3. Run everything locally (Docker)

```bash
cd 01_Source_Code/capr-webapp
cp .env.example .env
docker compose up --build
```

Open http://localhost:4200. Details: `HOW_TO_RUN.txt`.
