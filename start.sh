#!/bin/bash
# Railway startup script that properly handles PORT variable

# Use PORT from environment or default to 8080
PORT="${PORT:-8080}"

echo "🚀 Starting server on port $PORT"
uvicorn api.index:app --host 0.0.0.0 --port $PORT