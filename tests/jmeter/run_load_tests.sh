#!/usr/bin/env bash
# Lance le plan JMeter en mode CLI pour 100, 500 et 1000 utilisateurs
# et génère un rapport HTML par palier dans tests/jmeter/results/.
# Prérequis : JMeter installé et l'API démarrée (docker compose up -d).
set -euo pipefail
cd "$(dirname "$0")"
HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
mkdir -p results
for users in 100 500 1000; do
  out="results/${users}_users"
  rm -rf "$out" "$out.jtl"
  echo ">>> Test de charge : ${users} utilisateurs"
  jmeter -n -t churn_load_test.jmx \
    -Jthreads="$users" -Jrampup=10 -Jloops=10 -Jhost="$HOST" -Jport="$PORT" \
    -l "$out.jtl" -e -o "$out"
done
echo "Rapports : tests/jmeter/results/<N>_users/index.html"
