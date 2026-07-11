#!/bin/bash

echo "Starting Where2Stream Web UI..."
echo "================================"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "Error: Please run this script from the web-ui directory"
    exit 1
fi

# Install dependencies if not already installed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Check if Python dependencies are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip install fastapi uvicorn python-multipart
fi

# Start the API server in the background
echo "Starting API server on port 8000..."
python3 server.py &
API_PID=$!

# Wait a bit for the server to start
sleep 2

# Start the Vite dev server
echo "Starting Vite dev server on port 3000..."
echo "Open your browser to http://localhost:3000"
echo ""

npm run dev

# Clean up on exit
kill $API_PID 2>/dev/null
