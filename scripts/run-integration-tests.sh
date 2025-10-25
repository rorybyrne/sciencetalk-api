#!/bin/bash
# Script to run integration tests with database migrations
# This ensures the database is properly set up before running tests

set -e  # Exit on error

echo "===================="
echo "Integration Test Runner"
echo "===================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h ${DATABASE_HOST:-postgres} -p ${DATABASE_PORT:-5432} -U ${DATABASE_USER:-talk}; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Migrations complete!"

# Run integration tests
echo "Running integration tests..."
pytest tests/integration -v --tb=short

echo "===================="
echo "Tests complete!"
echo "===================="
