#!/bin/bash

# Georgia Dashboard API Startup Script

echo "🚀 Starting Georgia Dashboard API..."
echo

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env with your database configuration."
    echo "See api/README.md for details."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies (use MAIN requirements.txt that works with Streamlit)
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q -r api/requirements.txt

# Start API
echo
echo "✅ Starting API server..."
echo "📍 API will be available at: http://localhost:5000"
echo "📚 API Documentation: http://localhost:5000"
echo "❤️  Health Check: http://localhost:5000/api/health"
echo
echo "Press Ctrl+C to stop the server"
echo

cd api
python app.py
