#!/bin/bash
# HeySeen - Start all services

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Starting HeySeen Services..."
echo ""

# Check if already running
if [ -f "server_data/server.pid" ]; then
    SERVER_PID=$(cat server_data/server.pid)
    if ps -p "$SERVER_PID" > /dev/null 2>&1; then
        echo "⚠️  Backend server already running (PID: $SERVER_PID)"
    else
        rm -f server_data/server.pid
    fi
fi

# Start Backend Server
echo "📦 Starting Backend Server..."
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Ensure server_data directory exists
mkdir -p server_data

# Start server in background
source .venv/bin/activate
nohup uvicorn heyseen.server.app:app --host 0.0.0.0 --port 5555 > server_data/server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > server_data/server.pid

echo "✓ Backend started (PID: $SERVER_PID)"
echo "  Local: http://localhost:5555"
echo ""

# Wait for server to be ready
sleep 2
if ! ps -p "$SERVER_PID" > /dev/null 2>&1; then
    echo "❌ Backend failed to start. Check server_data/server.log"
    exit 1
fi

# Start Cloudflare Tunnel
echo "🌐 Starting Cloudflare Tunnel..."
cd deploy
./start_tunnel_bg.sh
cd ..

echo ""
echo "✅ All services started successfully!"
echo ""
echo "📊 Access:"
echo "  - Local:  http://localhost:5555"
echo "  - Public: https://heyseen.pedu.vn"
echo ""
echo "📝 Logs:"
echo "  - Backend: server_data/server.log"
echo "  - Tunnel:  deploy/tunnel.log"
echo ""
echo "💡 Use './stop.sh' to stop all services"
echo "💡 Use './status.sh' to check service status"
