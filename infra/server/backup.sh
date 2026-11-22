#!/bin/bash
# Backup do banco: pg_dump -> criptografia com age -> S3. Roda às 03:00 pelo eumini-backup.timer
# (instalado pelo post-install.sh) como o usuário deploy. Teste na hora: /opt/eumini/backup.sh
#
# O servidor só tem a chave pública (backup.age.pub): quem invadir a máquina não lê os backups.
# A chave privada fica com o dono, fora do servidor. Usa o bucket e a chave da AWS da própria
# aplicação (.env.app), na pasta backups/db/, e apaga os arquivos com mais de 30 dias.
set -euo pipefail
cd /opt/eumini

env_value() { grep -E "^$1=" .env.app | tail -1 | cut -d= -f2-; }
bucket="$(env_value AWS_STORAGE_BUCKET_NAME)"
prefix="backups/db/"
retention_days=30
aws_cli() {
  docker run --rm -i \
    -e AWS_ACCESS_KEY_ID="$(env_value AWS_ACCESS_KEY_ID)" \
    -e AWS_SECRET_ACCESS_KEY="$(env_value AWS_SECRET_ACCESS_KEY)" \
    -e AWS_DEFAULT_REGION="$(env_value AWS_S3_REGION_NAME)" \
    amazon/aws-cli:2.41.2 "$@"
}

key="${prefix}$(date +%F).dump.age"
docker compose exec -T postgres pg_dump -U eumini -d eumini --format=custom \
  | age --encrypt --recipients-file backup.age.pub \
  | aws_cli s3 cp - "s3://${bucket}/${key}" --only-show-errors
echo "Backup enviado: s3://${bucket}/${key}"

# Retenção: o nome do arquivo é a data do backup.
limit="$(date -d "-${retention_days} days" +%F)"
aws_cli s3 ls "s3://${bucket}/${prefix}" | awk '{print $4}' | while read -r name; do
  day="${name%%.dump.age}"
  if [[ "$day" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ && "$day" < "$limit" ]]; then
    aws_cli s3 rm "s3://${bucket}/${prefix}${name}" --only-show-errors
    echo "Backup antigo apagado: ${name}"
  fi
done
