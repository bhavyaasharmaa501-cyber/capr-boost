import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config
from .model_registry import get_registry
from .routers import health, predict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("capr.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("models loaded: %s", get_registry().list_datasets() or "(none)")
    yield


app = FastAPI(title="CAPR-Boost ML Service",
              description="Inference API for the CAPR-Boost encrypted-traffic anomaly detector.",
              version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_OPEN_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    if config.API_KEY and request.url.path not in _OPEN_PATHS:
        if request.headers.get("X-API-Key") != config.API_KEY:
            return JSONResponse(status_code=401, content={"detail": "missing or invalid X-API-Key"})
    return await call_next(request)


app.include_router(health.router)
app.include_router(predict.router)


@app.get("/")
def root():
    return {"service": "capr-ml-service", "docs": "/docs"}
