import json
import logging
import os
import time
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

MODEL_NAME = "Random Forest"
MODEL_VERSION = "1.0.0"
FEATURES = [
    "age",
    "anciennete",
    "revenu",
    "nb_reclamations",
    "montant_mensuel",
    "retards_paiement",
]


# --- Logging (PARTIE 19) -----------------------------------------------------
# Chaque ligne de log est un objet JSON : lisible par un humain dans la console
# et directement exploitable par Logstash / Elasticsearch / Kibana.
class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging():
    handlers = [logging.StreamHandler()]
    log_file = os.getenv("LOG_FILE")
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    for handler in handlers:
        handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


setup_logging()
logger = logging.getLogger("churn-api")


# --- Métriques métier (PARTIE 21/22) -------------------------------------------
PREDICTIONS = Counter(
    "churn_predictions_total",
    "Nombre de prédictions par résultat",
    ["result", "model_version"],
)
PREDICTION_ERRORS = Counter(
    "churn_prediction_errors_total",
    "Nombre d'erreurs de prédiction",
    ["model_version"],
)
PREDICTION_LATENCY = Histogram(
    "churn_prediction_duration_seconds",
    "Durée d'inférence du modèle",
    ["model_version"],
)


app = FastAPI(title="Churn Prediction API", version=MODEL_VERSION)

model = joblib.load("models/model.pkl")

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


class ClientData(BaseModel):
    age: int
    anciennete: int
    revenu: float
    nb_reclamations: int
    montant_mensuel: float
    retards_paiement: int


@app.get("/")
def root():
    return {
        "application": "Churn Prediction API",
        "version": MODEL_VERSION,
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/model/info")
def model_info():
    return {"model": MODEL_NAME, "version": MODEL_VERSION}


@app.get("/ui", include_in_schema=False)
def ui():
    return FileResponse(FRONTEND)


@app.post("/predict")
def predict(data: ClientData, request: Request):
    start = time.time()
    client_ip = request.client.host if request.client else "unknown"

    try:
        values = pd.DataFrame([data.model_dump()], columns=FEATURES)
        prediction = int(model.predict(values)[0])
        probability = float(model.predict_proba(values)[0][1])
    except Exception:
        duration_ms = round((time.time() - start) * 1000, 2)
        PREDICTION_ERRORS.labels(MODEL_VERSION).inc()
        logger.exception(
            "Prediction error",
            extra={
                "extra_fields": {
                    "operation": "prediction_error",
                    "client_ip": client_ip,
                    "model": MODEL_NAME,
                    "model_version": MODEL_VERSION,
                    "input": data.model_dump(),
                    "response_time_ms": duration_ms,
                }
            },
        )
        raise HTTPException(status_code=500, detail="Prediction error")

    duration = time.time() - start
    duration_ms = round(duration * 1000, 2)
    result = "CHURN" if prediction == 1 else "NO_CHURN"

    PREDICTIONS.labels(result, MODEL_VERSION).inc()
    PREDICTION_LATENCY.labels(MODEL_VERSION).observe(duration)

    logger.info(
        f"Prediction request: model_version={MODEL_VERSION}",
        extra={
            "extra_fields": {
                "operation": "prediction",
                "client_ip": client_ip,
                "model": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "input": data.model_dump(),
                "prediction": result,
                "probability": round(probability, 4),
                "response_time_ms": duration_ms,
            }
        },
    )

    return {
        "prediction": result,
        "probability": round(probability, 4),
        "model_version": MODEL_VERSION,
        "duration_ms": duration_ms,
    }


Instrumentator().instrument(app).expose(app)
