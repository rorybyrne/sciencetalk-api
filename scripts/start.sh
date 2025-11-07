#!/bin/sh
set -e

echo "========================================"
echo "Science Talk API - Container Startup"
echo "========================================"

echo "Running database migrations..."
python scripts/run_migrations.py

echo "Starting application server..."
exec python scripts/start_app.py
