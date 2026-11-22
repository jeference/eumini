#!/bin/bash
# Deploy da produção, rodado do PC: `make deploy`.
#
# 1. Envia o código da pasta atual (arquivos versionados e novos, sem os ignorados pelo git)
#    para /opt/eumini/src, junto com o compose e os scripts do servidor.
# 2. Roda o update.sh no servidor: gera as imagens, aplica as migrações e sobe a versão.
#
# Acesso: SSH só com chave, como o usuário deploy. Endereço e chave ficam fora do repositório:
#   EUMINI_HOST  (padrão: deploy@<IP em ~/.eumini/vps-ip>)
#   EUMINI_KEY   (padrão: ~/.eumini/vps_ed25519)
set -euo pipefail
cd "$(dirname "$0")/.."

host="${EUMINI_HOST:-deploy@$(tr -d '[:space:]' < "$HOME/.eumini/vps-ip")}"
key="${EUMINI_KEY:-$HOME/.eumini/vps_ed25519}"
ssh_opts=(-i "$key" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)

# Versão: o commit, mais data e hora se houver alterações ainda sem commit.
tag="$(git rev-parse --short HEAD)"
[ -z "$(git status --porcelain)" ] || tag="${tag}-$(date +%Y%m%d%H%M)"

echo "Enviando o código (${tag}) para ${host}"
git ls-files -z --cached --others --exclude-standard \
  | grep -zvE '^(testes_impressoes|prototipo|docs)/' \
  | while IFS= read -r -d '' file; do [ -f "$file" ] && printf '%s\0' "$file"; done \
  | tar -czf - --null -T - \
  | ssh "${ssh_opts[@]}" "$host" \
      "rm -rf /opt/eumini/src.new && mkdir -p /opt/eumini/src.new \
       && tar -xzf - -C /opt/eumini/src.new \
       && rm -rf /opt/eumini/src && mv /opt/eumini/src.new /opt/eumini/src"

scp -q "${ssh_opts[@]}" infra/compose.yml infra/server/update.sh infra/server/backup.sh \
  infra/server/bootstrap-secrets.sh "${host}:/opt/eumini/"
ssh "${ssh_opts[@]}" "$host" "chmod 750 /opt/eumini/*.sh && /opt/eumini/update.sh '${tag}'"
