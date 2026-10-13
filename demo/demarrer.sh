#!/bin/sh
# Démonstration sur Mac ou Linux.
cd "$(dirname "$0")/.." || exit 1
docker compose -f docker-compose.demo.yml up -d --build || exit 1
echo "Attente de l'application..."
i=0
until curl -sf -o /dev/null http://localhost:8080/sante; do
  i=$((i + 1)); [ "$i" -gt 60 ] && { echo "L'application ne répond pas."; exit 1; }
  sleep 3
done
echo "Ouvrez http://localhost:8080 - identifiants : ADMIN, RH01, M001, S001 à S004 ; mot de passe : Proximy2026"
(command -v open >/dev/null && open http://localhost:8080) || (command -v xdg-open >/dev/null && xdg-open http://localhost:8080) || true
