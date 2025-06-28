#!/bin/bash

# Start AI Trading Agent Chat Service
echo "🚀 Starting AI Trading Agent Chat Service..."

# Navigate to app directory
cd "$(dirname "$0")/app"

# Activate virtual environment
source venv/bin/activate

# Create database tables if they don't exist
echo "📊 Initializing database..."
python -c "from database import create_tables; create_tables()"

# Start the FastAPI server with onboarding chat
echo "💬 Starting chat service on http://localhost:8001"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
