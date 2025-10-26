#!/bin/sh
set -e

echo "========================================"
echo "Science Talk API - Container Startup"
echo "========================================"

echo "Running database migrations..."
alembic upgrade head

echo "Starting application server..."
exec uvicorn talk.interface.api.app:app --host 0.0.0.0 --port 8000
