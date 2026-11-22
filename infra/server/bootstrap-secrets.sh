#!/bin/bash
# Gera, no próprio servidor, os segredos que só a EuMini usa. Roda em /opt/eumini como deploy.
# Não sobrescreve valores existentes: pode rodar de novo sem trocar chaves (trocar a chave de
# criptografia tornaria os CPFs gravados ilegíveis).
set -euo pipefail
cd /opt/eumini
umask 077
touch .env .env.app

# Grava NOME=valor só se o nome não existir ou estiver vazio no arquivo.
set_if_empty() {
  local file="$1" name="$2" value="$3"
  if grep -qE "^${name}=.+" "$file"; then
    echo "${name}: já existe em ${file}, mantido."
  elif grep -qE "^${name}=" "$file"; then
    sed -i "s|^${name}=.*|${name}=${value}|" "$file"
    echo "${name}: gerado em ${file}."
  else
    echo "${name}=${value}" >> "$file"
    echo "${name}: gerado em ${file}."
  fi
}

set_if_empty .env POSTGRES_PASSWORD "$(openssl rand -hex 24)"
set_if_empty .env.app DJANGO_SECRET_KEY "$(openssl rand -hex 48)"
# Chave Fernet: 32 bytes em base64 seguro para URL.
set_if_empty .env.app FIELD_ENCRYPTION_KEY "$(openssl rand -base64 32 | tr '+/' '-_')"
chmod 600 .env .env.app
