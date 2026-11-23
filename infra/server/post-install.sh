#!/bin/bash
# Instalação do servidor de produção da EuMini (Ubuntu 26.04 LTS).
#
# Roda uma vez, como root, como "post-install script" da Hostinger ao recriar o VPS. Antes do
# envio, os marcadores são trocados pelas chaves públicas:
#   __DEPLOY_SSH_PUBKEY__  quem administra (shell completo)
#   __CI_SSH_PUBKEY__      GitHub Actions (só roda o /opt/eumini/receive.sh, sem shell nem túnel)
# A saída fica em /post_install.log.
#
# Exposição: o firewall da Hostinger só deixa entrar a porta 22 (SSH só com chave, só o usuário
# deploy). O site não usa porta nenhuma: chega pelo túnel da Cloudflare (container).
set -euo pipefail

DEPLOY_SSH_PUBKEY="__DEPLOY_SSH_PUBKEY__"
CI_SSH_PUBKEY="__CI_SSH_PUBKEY__"
export DEBIAN_FRONTEND=noninteractive
step() { echo "==> $(date -Is) $*"; }

step "Sistema: nome, fuso e pacotes"
hostnamectl set-hostname eumini-prod
timedatectl set-timezone America/Sao_Paulo
apt-get update
apt-get -y upgrade
apt-get install -y ca-certificates curl unattended-upgrades age

step "Swap de 2 GB (reserva contra falta de memória)"
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

step "Docker (repositório oficial)"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")"
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
# live-restore: atualizar o Docker não derruba os containers.
cat > /etc/docker/daemon.json <<'EOF'
{
  "live-restore": true,
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "5" }
}
EOF
systemctl restart docker

step "Usuário deploy (único que entra por SSH) e pasta da aplicação"
id deploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash --groups docker,systemd-journal deploy
install -d -o deploy -g deploy -m 700 /home/deploy/.ssh
{
  echo "${DEPLOY_SSH_PUBKEY}"
  # Sem a chave do CI (marcador não trocado), o deploy fica só pelo PC.
  case "${CI_SSH_PUBKEY}" in
    ssh-*) echo "restrict,command=\"/opt/eumini/receive.sh\" ${CI_SSH_PUBKEY}" ;;
  esac
} > /home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
install -d -o deploy -g deploy -m 750 /opt/eumini

step "SSH: só chave, sem root, só o usuário deploy"
cat > /etc/ssh/sshd_config.d/10-eumini.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowUsers deploy
MaxAuthTries 3
EOF
sshd -t
systemctl reload ssh || systemctl restart ssh

step "Atualizações automáticas: segurança do Ubuntu e Docker; reboot às 04:00"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
cat > /etc/apt/apt.conf.d/52eumini-upgrades <<'EOF'
Unattended-Upgrade::Origins-Pattern { "origin=Docker"; };
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
EOF
# As atualizações rodam de madrugada, depois do backup das 03:00.
mkdir -p /etc/systemd/system/apt-daily-upgrade.timer.d
cat > /etc/systemd/system/apt-daily-upgrade.timer.d/override.conf <<'EOF'
[Timer]
OnCalendar=
OnCalendar=*-*-* 03:30
RandomizedDelaySec=10m
EOF

step "Backup diário do banco às 03:00 (o script chega com o primeiro deploy)"
cat > /etc/systemd/system/eumini-backup.service <<'EOF'
[Unit]
Description=Backup do banco da EuMini para o S3
Wants=network-online.target docker.service
After=network-online.target docker.service

[Service]
Type=oneshot
User=deploy
WorkingDirectory=/opt/eumini
ExecStart=/opt/eumini/backup.sh
EOF
cat > /etc/systemd/system/eumini-backup.timer <<'EOF'
[Unit]
Description=Backup diário do banco da EuMini

[Timer]
OnCalendar=*-*-* 03:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now eumini-backup.timer

step "Fim"
rm -f /post_install
