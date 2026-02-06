#!/bin/bash
# HeySeen - Check service status

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "📊 HeySeen Service Status"
echo "=========================="
echo ""

# Check Backend Server
echo "📦 Backend Server:"
if [ -f "server_data/server.pid" ]; then
    SERVER_PID=$(cat server_data/server.pid)
    if ps -p "$SERVER_PID" > /dev/null 2>&1; then
        echo "  Status: ✅ Running"
        echo "  PID:    $SERVER_PID"
        echo "  Port:   5555"
        echo "  Local:  http://localhost:5555"
        
        # Check if port is listening
        if lsof -Pi :5555 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "  Listen: ✅ Active"
        else
            echo "  Listen: ⚠️  Not listening on port 5555"
        fi
    else
        echo "  Status: ❌ Stopped (stale PID file)"
        echo "  PID:    $SERVER_PID (not running)"
    fi
else
    echo "  Status: ❌ Stopped"
    echo "  PID:    None"
fi

echo ""

# Check Cloudflare Tunnel
echo "🌐 Cloudflare Tunnel:"
TUNNEL_PID=$(ps aux | grep "cloudflared tunnel" | grep -v grep | awk '{print $2}')

if [ -n "$TUNNEL_PID" ]; then
    echo "  Status: ✅ Running"
    echo "  PID:    $TUNNEL_PID"
    echo "  Domain: heyseen.truyenthong.edu.vn"
    echo "  URL:    https://heyseen.truyenthong.edu.vn"
    
    # Show tunnel connections
    CONN_COUNT=$(ps aux | grep cloudflared | grep -v grep | wc -l)
    echo "  Procs:  $CONN_COUNT"
else
    echo "  Status: ❌ Stopped"
    echo "  PID:    None"
fi

echo ""

# Overall Status
if [ -f "server_data/server.pid" ] && ps -p "$(cat server_data/server.pid)" > /dev/null 2>&1 && [ -n "$TUNNEL_PID" ]; then
    echo "✅ All services are running"
    echo ""
    echo "📝 Logs:"
    echo "  Backend: tail -f server_data/server.log"
    echo "  Tunnel:  tail -f deploy/tunnel.log"
    echo ""
    echo "💡 Quick actions:"
    echo "  ./stop.sh    - Stop all services"
    echo "  ./restart.sh - Restart all services"
elif [ -f "server_data/server.pid" ] && ps -p "$(cat server_data/server.pid)" > /dev/null 2>&1; then
    echo "⚠️  Backend running but tunnel is stopped"
    echo ""
    echo "💡 Run './restart.sh' to fix"
elif [ -n "$TUNNEL_PID" ]; then
    echo "⚠️  Tunnel running but backend is stopped"
    echo ""
    echo "💡 Run './restart.sh' to fix"
else
    echo "❌ All services are stopped"
    echo ""
    echo "💡 Run './start.sh' to start services"
fi
