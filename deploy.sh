#!/bin/bash
set -e
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'
echo "=========================================="
echo "  Cleanvid Deployment"
echo "=========================================="
# Pull code (via git-helper container)
echo -e "${CYAN}==>${NC} Pulling latest code..."
docker exec git-helper /scripts/pull-cleanvid.sh

# Fix file permissions (need sudo for chown)
echo -e "${CYAN}==>${NC} Fixing file permissions..."
sudo chown -R scum:users /volume1/docker/cleanvid2/

# Build on host (no sudo needed - you're in docker group)
echo -e "${CYAN}==>${NC} Building Docker image..."
cd /volume1/docker/cleanvid2
docker build -t cleanvid:2.0 .

# Copy entire source tree into running container (workaround for Docker cache issues)
echo -e "${CYAN}==>${NC} Syncing source code into container..."
docker cp /volume1/docker/cleanvid2/src/cleanvid/. cleanvid2:/app/src/cleanvid/

# Restart
echo -e "${CYAN}==>${NC} Restarting container..."
docker-compose restart

sleep 5

if docker ps | grep -q cleanvid2; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""
    echo "📊 Container status:"
    docker ps | grep cleanvid2
    echo ""
    echo "📋 Last 10 log lines:"
    docker logs cleanvid2 --tail 10
    echo ""
    echo "🌐 Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
    echo "💡 To view live logs: docker logs -f cleanvid2"
else
    echo "❌ Deployment failed!"
    exit 1
fi
