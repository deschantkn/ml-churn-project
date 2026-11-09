from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root():

    response = client.get("/")

    assert response.status_code == 200


def test_health():

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json()["status"] == "UP"


def test_model_info():

    response = client.get("/model/info")

    assert response.status_code == 200


def test_prediction():

    payload = {
        "age": 35,
        "anciennete": 5,
        "revenu": 450000,
        "nb_reclamations": 2,
        "montant_mensuel": 25000,
        "retards_paiement": 2,
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "prediction" in data
    assert "probability" in data
    assert "model_version" in data


def test_prediction_invalid_payload():

    response = client.post("/predict", json={"age": "abc"})

    assert response.status_code == 422


def test_ui():

    response = client.get("/ui")

    assert response.status_code == 200
    assert "Prédire" in response.text


def test_metrics():

    client.post(
        "/predict",
        json={
            "age": 35,
            "anciennete": 5,
            "revenu": 450000,
            "nb_reclamations": 2,
            "montant_mensuel": 25000,
            "retards_paiement": 2,
        },
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "churn_predictions_total" in response.text
