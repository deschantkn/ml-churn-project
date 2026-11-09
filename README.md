# ML Churn Project

Prédiction du churn des clients d'un opérateur télécom : d'un modèle de Data Science
à une application industrialisée (API, tests, Docker, CI/CD, logs, monitoring).

## Architecture

```
Utilisateur ──► Interface Web (/ui) ──► FastAPI (/predict) ──► Random Forest (models/model.pkl)

FastAPI ── logs JSON ──► Logstash ──► Elasticsearch ──► Kibana
FastAPI ── /metrics  ──► Prometheus ──► Grafana
Git ──► GitHub Actions ──► Tests unitaires/API ──► Tests E2E Selenium ──► Build Docker
```

## Arborescence

| Chemin | Rôle |
|---|---|
| `src/generate_data.py` | Génération du dataset (`data/raw/churn.csv`) |
| `notebooks/exploration.py` | Exploration des données (graphiques dans `data/`) |
| `src/train.py` | Entraînement / comparaison des modèles, sauvegarde `models/model.pkl` |
| `api/main.py` | API FastAPI : `/`, `/health`, `/model/info`, `/predict`, `/ui`, `/metrics` |
| `frontend/index.html` | Interface Web de saisie client (servie sur `/ui`) |
| `tests/test_api.py` | Tests Pytest de l'API |
| `tests/test_selenium.py` | Tests E2E Selenium (Swagger + parcours de prédiction) |
| `tests/jmeter/` | Plan de test de charge JMeter + script 100/500/1000 utilisateurs |
| `docker/logstash/logstash.conf` | Pipeline Logstash → Elasticsearch |
| `monitoring/prometheus/prometheus.yml` | Configuration du scraping Prometheus |
| `monitoring/grafana/` | Datasource et dashboard Grafana provisionnés automatiquement |
| `.github/workflows/ci.yml` | Pipeline CI : tests, E2E, build Docker |

## Guide d'installation

### Prérequis
Python 3.14, Git, Docker + Docker Compose. Google Chrome pour Selenium, Apache JMeter pour les tests de charge.

### En local (sans Docker)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/generate_data.py      # dataset
python src/train.py              # modèle
uvicorn api.main:app --reload    # API sur http://127.0.0.1:8000
```

- Swagger : http://127.0.0.1:8000/docs
- Interface Web : http://127.0.0.1:8000/ui

### Avec Docker Compose (stack complète)
```bash
docker compose up -d --build
docker compose ps
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Interface Web | http://localhost:8000/ui |
| Kibana | http://localhost:5601 |
| Elasticsearch | http://localhost:9200 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |

La stack ELK demande environ 2 Go de RAM disponibles pour Docker.

## Tests

```bash
pytest                              # tests API (Selenium ignoré si l'API n'est pas démarrée)
pytest -m "not e2e"                 # uniquement les tests unitaires/API
pytest tests/test_selenium.py -v    # E2E : nécessite l'API démarrée
APP_URL=http://SERVER_IP:8000 pytest tests/test_selenium.py
```

### Test de charge JMeter
```bash
# Interface graphique : ouvrir tests/jmeter/churn_load_test.jmx dans jmeter
# Mode CLI, les trois paliers d'un coup, rapport HTML par palier :
./tests/jmeter/run_load_tests.sh
# Un palier précis :
jmeter -n -t tests/jmeter/churn_load_test.jmx -Jthreads=500 -Jrampup=10 -Jloops=10 \
  -l results.jtl -e -o report/
```
Les rapports (`tests/jmeter/results/<N>_users/index.html`) donnent le temps moyen, la médiane,
les percentiles 90/95, le débit (requests/sec) et le % d'erreurs.

## Logs (ELK)

L'API écrit des logs JSON (console + `LOG_FILE`) avec les champs :
`timestamp` (quand), `client_ip` (qui), `operation` (quelle opération), `model` / `model_version` (quel modèle),
`prediction` / `probability` (quel résultat), `response_time_ms` (combien de temps), `exception` (quelle erreur).

Dans Kibana : *Stack Management → Data Views → Create* avec le pattern `ml-churn-logs-*`,
puis *Discover* pour rechercher par exemple `operation:prediction`, `level:ERROR`,
`model_version:"1.0.0"` ou `response_time_ms > 100`.

## Monitoring (Prometheus + Grafana)

Métriques exposées sur `/metrics` : métriques HTTP de `prometheus-fastapi-instrumentator`
et métriques métier `churn_predictions_total{result}`, `churn_prediction_errors_total`,
`churn_prediction_duration_seconds`.

Le dashboard **ML Churn API** est provisionné automatiquement dans Grafana : nombre de requêtes,
temps de réponse p50/p95, nombre d'erreurs, taux d'erreur, nombre de prédictions et répartition CHURN/NO_CHURN.

## Déploiement sur un serveur

```bash
sudo apt update && sudo apt install git -y
git clone https://github.com/deschantkn/ml-churn-project.git
cd ml-churn-project
docker compose build
docker compose up -d
docker compose ps
curl http://SERVER_IP:8000/health
curl -X POST http://SERVER_IP:8000/predict -H "Content-Type: application/json" \
  -d '{"age":35,"anciennete":5,"revenu":450000,"nb_reclamations":2,"montant_mensuel":25000,"retards_paiement":2}'
```

## Documentation

- [Documentation technique](docs/documentation_technique.md)
- [Rapport d'industrialisation](docs/rapport_industrialisation.md)
