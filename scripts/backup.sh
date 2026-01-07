#!/bin/bash
BACKUP_DIR="/home/datingbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

echo "📦 Creating backup..."

# Redis
docker exec datingbot-redis redis-cli BGSAVE 2>/dev/null
sleep 2
docker cp datingbot-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb 2>/dev/null

# Volumes
tar -czf $BACKUP_DIR/volumes_$DATE.tar.gz \
    -C /var/lib/docker/volumes . 2>/dev/null || true

# Cleanup old (7 days)
find $BACKUP_DIR -type f -mtime +7 -delete 2>/dev/null

echo "✅ Backup saved: $BACKUP_DIR/*_$DATE.*"
ls -lh $BACKUP_DIR/*$DATE* 2>/dev/null
