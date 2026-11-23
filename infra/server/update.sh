#!/bin/bash
# Gera as imagens a partir do código em src/ e sobe a nova versão. Roda no servidor, em
# /opt/eumini, como deploy. Chamado pelo receive.sh, a cada deploy.
set -euo pipefail
cd /opt/eumini

tag="${1:?informe a tag}"
[[ "$tag" =~ ^[0-9a-z.-]{7,64}$ ]] || { echo "Tag inválida: $tag" >&2; exit 1; }

set_env() {
  if grep -qE "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
previous="$(grep -E '^TAG=' .env | cut -d= -f2 || true)"
set_env SRC_DIR ./src
set_env TAG "$tag"
echo "Versão: ${previous:-nenhuma} -> ${tag}"

docker compose build --quiet
docker compose up -d --wait postgres
docker compose run --rm migrate
docker compose up -d --remove-orphans --wait --wait-timeout 180
# Imagens e cache de build com mais de 7 dias saem; as recentes ficam para voltar versão.
docker image prune -a -f --filter "until=168h" >/dev/null
docker builder prune -f --filter "until=168h" >/dev/null
docker compose ps --format "table {{.Service}}\t{{.Status}}"
