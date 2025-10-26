#!/bin/bash
# Script to run tests with database migrations
# This ensures the database is properly set up before running tests
# Usage: ./run-integration-tests.sh [test_path]
# Example: ./run-integration-tests.sh tests/integration
# Example: ./run-integration-tests.sh tests/e2e

set -e  # Exit on error

# Get test path from argument or default to integration tests
TEST_PATH="${1:-tests/integration}"

echo "===================="
echo "Test Runner"
echo "===================="
echo "Test path: $TEST_PATH"

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

# Run tests
echo "Running tests from $TEST_PATH..."
pytest "$TEST_PATH" -v --tb=short

echo "===================="
echo "Tests complete!"
echo "===================="
