#!/bin/bash
# Deploy da produção. Normalmente roda sozinho no GitHub Actions (.github/workflows/deploy.yml)
# depois que o CI passa na main; do PC, `make deploy` fica para emergência.
#
# Envia o código da pasta atual (arquivos versionados e novos, sem os ignorados pelo git) numa
# única conexão SSH para o infra/server/receive.sh, que troca o src/, atualiza o compose e os
# scripts do servidor e roda o update.sh (gera as imagens, aplica as migrações e sobe a versão).
#
# Acesso: SSH só com chave, como o usuário deploy. Endereço e chave ficam fora do repositório:
#   EUMINI_HOST         (padrão: deploy@<IP em ~/.eumini/vps-ip>)
#   EUMINI_KEY          (padrão: ~/.eumini/vps_ed25519)
#   EUMINI_KNOWN_HOSTS  arquivo com a host key da VPS; quando definido, só aceita essa (CI)
#   EUMINI_CI=1         a chave do CI só roda o receive.sh, então não envia o receive.sh antes
set -euo pipefail
cd "$(dirname "$0")/.."

host="${EUMINI_HOST:-deploy@$(tr -d '[:space:]' < "$HOME/.eumini/vps-ip")}"
key="${EUMINI_KEY:-$HOME/.eumini/vps_ed25519}"
ssh_opts=(-i "$key" -o IdentitiesOnly=yes)
if [ -n "${EUMINI_KNOWN_HOSTS:-}" ]; then
  ssh_opts+=(-o UserKnownHostsFile="$EUMINI_KNOWN_HOSTS" -o StrictHostKeyChecking=yes)
else
  ssh_opts+=(-o StrictHostKeyChecking=accept-new)
fi

# Versão: o commit, mais data e hora se houver alterações ainda sem commit.
tag="$(git rev-parse --short HEAD)"
[ -z "$(git status --porcelain)" ] || tag="${tag}-$(date +%Y%m%d%H%M)"

# Com a chave de administração, leva antes o receive.sh atual: um servidor recém-criado ainda
# não tem nenhum.
if [ -z "${EUMINI_CI:-}" ]; then
  ssh "${ssh_opts[@]}" "$host" \
    "cat > /opt/eumini/receive.sh && chmod 750 /opt/eumini/receive.sh" < infra/server/receive.sh
fi

echo "Enviando o código (${tag}) para ${host}"
git ls-files -z --cached --others --exclude-standard \
  | grep -zvE '^(testes_impressoes|prototipo|docs)/' \
  | while IFS= read -r -d '' file; do [ -f "$file" ] && printf '%s\0' "$file"; done \
  | tar -czf - --null -T - \
  | ssh "${ssh_opts[@]}" "$host" "/opt/eumini/receive.sh ${tag}"
