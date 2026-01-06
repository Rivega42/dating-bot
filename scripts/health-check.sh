#!/bin/bash
echo "📊 Dating Bot Health Check"
echo "========================="

# API
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API: healthy"
else
    echo "❌ API: down"
fi

# Redis
if docker exec datingbot-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "✅ Redis: healthy"
else
    echo "❌ Redis: down"
fi

# Containers
echo ""
echo "🐳 Containers:"
docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || docker ps --format "table {{.Names}}\t{{.Status}}"

# Resources
echo ""
echo "💻 Resources:"
echo "CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')%"
echo "RAM: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2}')"
