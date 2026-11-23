#!/bin/bash
# Recebe uma versão e a publica. Roda no servidor, em /opt/eumini, como deploy.
#
# Lê do stdin o código em tar.gz (enviado pelo infra/deploy.sh), troca o src/, copia de lá o
# compose e os scripts do servidor e chama o update.sh. É a única coisa que a chave do GitHub
# Actions consegue rodar: no authorized_keys ela vem com command="/opt/eumini/receive.sh", e aí a
# tag chega pelo comando pedido ($SSH_ORIGINAL_COMMAND). A chave de administração chama com a
# tag como argumento.
#
# Tudo fica dentro de main: o bash lê a função inteira antes de rodar, então este arquivo pode
# ser substituído pela versão nova no meio da execução.
set -euo pipefail

main() {
  local tag
  if [ $# -ge 1 ]; then
    tag="$1"
  else
    local -a words
    read -r -a words <<< "${SSH_ORIGINAL_COMMAND:-}"
    if [ "${#words[@]}" -ne 2 ] || [ "${words[0]}" != /opt/eumini/receive.sh ]; then
      echo "Uso: /opt/eumini/receive.sh <tag>, com o código em tar.gz no stdin" >&2
      exit 2
    fi
    tag="${words[1]}"
  fi
  [[ "$tag" =~ ^[0-9a-z.-]{7,64}$ ]] || { echo "Tag inválida: $tag" >&2; exit 1; }

  cd /opt/eumini
  rm -rf src.new
  mkdir src.new
  tar -xzf - -C src.new
  rm -rf src
  mv src.new src

  install -m 640 src/infra/compose.yml compose.yml
  install -m 750 src/infra/server/{receive,update,backup,bootstrap-secrets}.sh .
  ./update.sh "$tag"
}

main "$@"
exit
