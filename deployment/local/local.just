# Local deployment commands

# Build Docker image
docker-build:
    docker build -t talk-api:latest .

# Run Docker container
docker-run:
    docker run -p 8000:8000 --env-file .env talk-api:latest

# Stop and remove Docker container
docker-stop:
    docker stop talk-api || true
    docker rm talk-api || true

# Start local development environment with docker compose
compose-up:
    docker compose -f docker-compose.yml up -d

# Stop local development environment
compose-down:
    docker compose -f docker-compose.yml down

# View logs from all services
compose-logs:
    docker compose -f docker-compose.yml logs -f

# View logs from specific service
compose-logs-api:
    docker compose -f docker-compose.yml logs -f api

compose-logs-db:
    docker compose -f docker-compose.yml logs -f postgres

# Restart all services
compose-restart:
    docker compose -f docker-compose.yml restart

# Rebuild and restart services
compose-rebuild:
    docker compose -f docker-compose.yml up -d --build

# Rebuild without cache and restart services
compose-rebuild-no-cache:
    docker compose -f docker-compose.yml build --no-cache
    docker compose -f docker-compose.yml up -d

# Clean up Docker resources
docker-clean:
    docker system prune -f
    docker volume prune -f

# Connect to postgres database
db-connect:
    docker compose -f docker-compose.yml exec postgres psql -U talk -d talk

# Reset database (stop, remove volume, restart)
db-reset:
    docker compose -f docker-compose.yml down -v
    docker compose -f docker-compose.yml up -d postgres
    sleep 5
    docker compose -f docker-compose.yml up -d api
