#!/bin/bash
# Georgia Dashboard - Simple Local Startup Script
# Access via Tailscale or local network

cd "$(dirname "$0")"

echo "============================================="
echo "🚀 Georgia Dashboard - Local Access"
echo "============================================="
echo ""

# Get IP addresses
echo "📡 Network Access URLs:"
echo ""
echo "   Local:      http://localhost:8080"
echo ""

# Get all non-loopback IP addresses
IPs=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')
for ip in $IPs; do
    if [[ $ip == 100.* ]]; then
        echo "   Tailscale:  http://$ip:8080"
    else
        echo "   Network:    http://$ip:8080"
    fi
done

echo ""
echo "============================================="
echo "Starting server..."
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start the dashboard
python3 run.py
