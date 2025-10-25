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

# Reset database (stop, remove volume, restart)
db-reset:
    docker compose -f docker-compose.yml down -v
    docker compose -f docker-compose.yml up -d postgres
    sleep 5
    docker compose -f docker-compose.yml up -d api
