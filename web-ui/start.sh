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
    pip install -r requirements.txt
fi

# Check if TMDB_API_KEY is set
if [ -z "$TMDB_API_KEY" ]; then
    echo "Warning: TMDB_API_KEY not found in environment"
    echo "Please set it in your .env file or export it:"
    echo "export TMDB_API_KEY=your_api_key_here"
fi

# Start the API server in the background
echo "Starting API server on port 8000..."
python3 server_simple.py &
API_PID=$!

# Wait a bit for the server to start
sleep 3

# Check if server started successfully
if ! curl -s http://localhost:8000/ > /dev/null; then
    echo "Error: API server failed to start"
    echo "Check if port 8000 is available and TMDB_API_KEY is set"
    kill $API_PID 2>/dev/null
    exit 1
fi

echo "API server is running!"

# Start the Vite dev server
echo "Starting Vite dev server on port 3000..."
echo "Open your browser to http://localhost:3000"
echo ""

npm run dev

# Clean up on exit
kill $API_PID 2>/dev/null
