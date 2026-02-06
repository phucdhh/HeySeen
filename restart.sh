#!/bin/bash
# HeySeen - Restart all services

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🔄 Restarting HeySeen Services..."
echo ""

# Stop services first
./stop.sh

echo ""
echo "⏳ Waiting 2 seconds..."
sleep 2
echo ""

# Start services
./start.sh
