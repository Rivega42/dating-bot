#!/bin/bash
# Dating Bot Platform - Auto Install
set -e

GITHUB_REPO=${1:-""}
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then log_error "Run as root: sudo $0"; exit 1; fi

echo ""
echo "============================================"
echo "🚀 Dating Bot Platform - Install"
echo "============================================"

apt update && apt upgrade -y
apt install -y curl wget git unzip htop nano ufw fail2ban ca-certificates gnupg lsb-release

# Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi
log_success "Docker installed"

# Swap 4GB
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile && chmod 600 /swapfile
    mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
log_success "Swap configured"

# Firewall
ufw default deny incoming > /dev/null
ufw default allow outgoing > /dev/null
ufw allow 22/tcp > /dev/null
ufw allow 80/tcp > /dev/null
ufw allow 443/tcp > /dev/null
ufw allow 3000/tcp > /dev/null
ufw --force enable > /dev/null
log_success "Firewall configured"

# User
if ! id "datingbot" &>/dev/null; then
    useradd -m -s /bin/bash -G docker datingbot
fi

# Clone project
PROJECT_DIR="/home/datingbot/dating-bot"
if [ -n "$GITHUB_REPO" ]; then
    if [ -d "$PROJECT_DIR" ]; then
        cd $PROJECT_DIR && git pull origin main
    else
        git clone https://github.com/$GITHUB_REPO.git $PROJECT_DIR
    fi
fi
cd $PROJECT_DIR
chown -R datingbot:datingbot $PROJECT_DIR

# Generate .env
if [ ! -f .env ]; then
    cp .env.example .env
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)/" .env
    sed -i "s/JWT_SECRET=.*/JWT_SECRET=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9' | head -c 64)/" .env
    sed -i "s/GRAFANA_PASSWORD=.*/GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)/" .env
    chmod 600 .env
fi

# SSL
mkdir -p nginx/ssl
if [ ! -f nginx/ssl/fullchain.pem ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=DatingBot/CN=localhost" 2>/dev/null
fi

chmod +x scripts/*.sh 2>/dev/null || true
docker compose up -d --build

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}✅ INSTALLED${NC}"
echo "API: http://$PUBLIC_IP:8000"
echo "Grafana: http://$PUBLIC_IP:3000"
echo "Config: $PROJECT_DIR/.env"
echo ""
echo "⚠️  Fill BEGET_DB_* and BEGET_S3_* in .env!"
