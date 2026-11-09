"""Tests E2E Selenium (PARTIE 17).

Prérequis : l'API doit tourner (uvicorn api.main:app ou docker compose up).
Si elle n'est pas joignable, les tests sont ignorés (skip) au lieu d'échouer,
ce qui permet de lancer `pytest` sans démarrer le serveur.

URL configurable : APP_URL=http://localhost:8000 pytest tests/test_selenium.py
"""

import os
import urllib.request

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

APP_URL = os.getenv("APP_URL", "http://localhost:8000")


def _server_up():
    try:
        with urllib.request.urlopen(f"{APP_URL}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _server_up(), reason=f"API non joignable sur {APP_URL}"),
]


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    drv = webdriver.Chrome(options=options)
    yield drv
    drv.quit()


def test_swagger_docs(driver):
    driver.get(f"{APP_URL}/docs")
    assert "Churn Prediction API" in driver.title


def test_prediction_from_ui(driver):
    # Ouverture de l'application
    driver.get(f"{APP_URL}/ui")
    assert "Prédiction du churn" in driver.title

    # Saisie des données client
    client = {
        "age": 35,
        "anciennete": 5,
        "revenu": 450000,
        "nb_reclamations": 2,
        "montant_mensuel": 25000,
        "retards_paiement": 2,
    }
    for field, value in client.items():
        element = driver.find_element(By.ID, field)
        element.clear()
        element.send_keys(str(value))

    # Clic sur "Prédire" -> appel API
    driver.find_element(By.ID, "predict-btn").click()

    # Affichage et vérification du résultat
    prediction = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "prediction"))
    )
    assert prediction.text in ("CHURN", "NO_CHURN")

    probability = float(driver.find_element(By.ID, "probability").text)
    assert 0.0 <= probability <= 1.0
