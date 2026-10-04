#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_USER="${1:-cvsz}"

log() { printf '\n[zwslcore-bootstrap] %s\n' "$*"; }

if [[ ${EUID} -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "/etc/os-release is missing." >&2
  exit 1
fi

. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "Ubuntu is required; detected ${ID:-unknown}." >&2
  exit 1
fi

log "Installing base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  ca-certificates \
  curl \
  git \
  gnupg \
  jq \
  make \
  openssl \
  python3 \
  python3-pip \
  python3-venv \
  build-essential \
  unzip \
  zip \
  rsync \
  lsb-release \
  procps \
  iproute2

if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker Engine from Docker's official Ubuntu repository"

  for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc; do
    dpkg-query -W -f='${db:Status-Abbrev}' "$package" 2>/dev/null | grep -q '^ii ' && apt-get remove -y "$package" || true
  done

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc

  ARCH="$(dpkg --print-architecture)"
  CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME}}"

  cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${CODENAME}
Components: stable
Architectures: ${ARCH}
Signed-By: /etc/apt/keyrings/docker.asc
EOF

  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

log "Enabling Docker"
systemctl enable docker
systemctl restart docker

if ! id -u "$INSTALL_USER" >/dev/null 2>&1; then
  log "Creating Linux user $INSTALL_USER"
  useradd --create-home --shell /bin/bash "$INSTALL_USER"
  usermod -aG sudo "$INSTALL_USER"
  touch "/var/lib/zwslcore-user-created"
fi

usermod -aG docker "$INSTALL_USER"

log "Validating installed software"
docker version >/dev/null
docker compose version >/dev/null
git --version
python3 --version
curl --version | head -1
make --version | head -1

printf '\n[zwslcore-bootstrap] Ubuntu host prerequisites are ready.\n'
