# Local deployment commands

# Start local development environment with docker compose
up:
    docker compose -f docker-compose.yml up -d

# show status
ps:
    docker compose -f docker-compose.yml ps

# Stop local development environment
down:
    docker compose -f docker-compose.yml down

# View logs from all services
logs SERVICE="":
    docker compose -f docker-compose.yml logs -f {{SERVICE}}

# Restart all services
restart:
    docker compose -f docker-compose.yml restart

rebuild-all:
    docker compose -f docker-compose.yml up -d --build

# Rebuild without cache and restart services
rebuild-all-full:
    docker compose -f docker-compose.yml build --no-cache
    docker compose -f docker-compose.yml up -d

# Clean up Docker resources
clean:
    docker system prune -f
    docker volume prune -f

# Connect to postgres database
db-connect:
    docker compose -f docker-compose.yml exec postgres psql -U talk -d talk

# Reset database (stop, remove volume)
wipe:
    docker compose -f docker-compose.yml down -v

# Run integration tests in Docker
test-integration:
    docker compose -f docker-compose.yml --profile test up --build --abort-on-container-exit test

# Run integration tests and keep containers running for debugging
test-integration-debug:
    docker compose -f docker-compose.yml --profile test up --build test

# Run e2e tests in Docker (requires API to be running)
test-e2e:
    docker compose -f docker-compose.yml --profile test-e2e up --build --abort-on-container-exit test-e2e

# Run e2e tests and keep containers running for debugging
test-e2e-debug:
    docker compose -f docker-compose.yml --profile test-e2e up --build test-e2e

# View test logs
test-logs:
    docker compose -f docker-compose.yml logs test
