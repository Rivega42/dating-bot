#!/bin/bash
# Add new worker node
set -e

WORKER_IP=$1
WORKER_ID=${2:-"worker-$(date +%s)"}
MAIN_SERVER_IP=$(hostname -I | awk '{print $1}')

if [ -z "$WORKER_IP" ]; then
    echo "Usage: ./add-worker.sh WORKER_IP [WORKER_ID]"
    exit 1
fi

echo "🚀 Adding worker: $WORKER_IP ($WORKER_ID)"

ssh root@$WORKER_IP << EOF
# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# Swap
fallocate -l 4G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Create worker compose
mkdir -p /opt/dating-worker
cat > /opt/dating-worker/docker-compose.yml << 'COMPOSE'
version: '3.8'
services:
  worker:
    image: ghcr.io/\${GITHUB_REPO}-worker:latest
    restart: unless-stopped
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@${MAIN_SERVER_IP}:6379/0
      - MAX_BROWSERS=\${MAX_BROWSERS:-8}
      - WORKER_ID=$WORKER_ID
    shm_size: '2gb'
    deploy:
      resources:
        limits:
          memory: 6G
COMPOSE

cd /opt/dating-worker
docker compose pull
docker compose up -d
EOF

echo "✅ Worker $WORKER_ID added!"
echo "$WORKER_ID,$WORKER_IP,$(date -Iseconds)" >> workers.csv
