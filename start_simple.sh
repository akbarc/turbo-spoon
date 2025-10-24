#!/bin/bash
# Start the Simple Georgia Dashboard

cd "$(dirname "$0")"

echo "================================================"
echo "🚀 Georgia Dashboard - Simple Daily Sales"
echo "================================================"
echo ""
echo "📡 Access URLs:"
echo "   Local:      http://localhost:8080"
echo "   Tailscale:  http://100.126.106.37:8080"
echo ""
echo "================================================"
echo "Starting server..."
echo ""

# Kill any existing process on port 8080
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Wait a moment
sleep 1

# Start the dashboard
python3 simple_dashboard.py
