#!/bin/bash
# HeySeen - Stop all services

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🛑 Stopping HeySeen Services..."
echo ""

# Stop Backend Server
if [ -f "server_data/server.pid" ]; then
    SERVER_PID=$(cat server_data/server.pid)
    if ps -p "$SERVER_PID" > /dev/null 2>&1; then
        echo "📦 Stopping Backend Server (PID: $SERVER_PID)..."
        kill "$SERVER_PID"
        sleep 1
        
        # Force kill if still running
        if ps -p "$SERVER_PID" > /dev/null 2>&1; then
            echo "  ⚠️  Force killing..."
            kill -9 "$SERVER_PID" 2>/dev/null || true
        fi
        
        rm -f server_data/server.pid
        echo "✓ Backend stopped"
    else
        echo "⚠️  Backend server not running (stale PID file)"
        rm -f server_data/server.pid
    fi
else
    echo "⚠️  Backend server not running (no PID file)"
fi

echo ""

# Stop Cloudflare Tunnel
echo "🌐 Stopping Cloudflare Tunnel..."
TUNNEL_PID=$(ps aux | grep "cloudflared tunnel" | grep -v grep | awk '{print $2}')

if [ -n "$TUNNEL_PID" ]; then
    kill "$TUNNEL_PID" 2>/dev/null || true
    sleep 1
    
    # Force kill if still running
    if ps -p "$TUNNEL_PID" > /dev/null 2>&1; then
        echo "  ⚠️  Force killing..."
        kill -9 "$TUNNEL_PID" 2>/dev/null || true
    fi
    
    echo "✓ Tunnel stopped"
else
    echo "⚠️  Tunnel not running"
fi

echo ""
echo "✅ All services stopped"
echo ""
echo "💡 Use './start.sh' to start services again"
