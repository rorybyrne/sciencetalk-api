# Import local deployment commands
mod local 'deployment/local/local.just'

# Environment configuration
LOCAL_ENV := "--env-file .env"

default:
    @just --list

# Testing commands
test kind="":
    @TEST=1 uv run pytest tests/{{kind}}

test-s kind="unit":
    @TEST=1 uv run pytest -s -o log_cli=True -o log_cli_level=DEBUG "tests/{{kind}}"

test-e2e:
    @uv run pytest "tests/e2e"

# Code quality commands
fix dir="blank":
    uv run ruff format {{dir}}
    uv run ruff check --fix {{dir}}

lint:
    uv run ruff check blank
    uv run pyright blank

lint-file file:
    - uv run ruff check {{file}}
    - uv run pyright {{file}}

# Development commands
dev:
    uv run uvicorn blank.interface.api.app:app --reload --host 0.0.0.0 --port 8000

install:
    uv sync

# Docker commands (standalone)
docker-build:
    docker build -t talk-api:latest .

docker-run PORT="8000":
    docker run -p {{PORT}}:8000 --env-file .env talk-api:latest

docker-serve PORT="8000":
    just docker-build && docker run -p {{PORT}}:8000 --env-file .env talk-api:latest

docker-shell:
    just docker-build
    docker run -it --rm talk-api:latest bash

docker-stop:
    docker stop talk-api && docker rm talk-api || true

# Local development environment (with compose)
local-up:
    just local compose-up

local-down:
    just local compose-down

local-logs:
    just local compose-logs

local-restart:
    just local compose-restart

local-rebuild:
    just local compose-rebuild

local-rebuild-no-cache:
    just local compose-rebuild-no-cache

local-clean:
    just local docker-clean

# Database commands
db-connect:
    just local db-connect

db-reset:
    just local db-reset

# Run database migrations
db-migrate:
    uv run alembic upgrade head

# Create new migration
db-migration name:
    uv run alembic revision -m "{{name}}"

# Show migration history
db-history:
    uv run alembic history

# Show current migration version
db-current:
    uv run alembic current

# Full development workflow
setup: install local-up
    @echo "Development environment ready!"
    @echo "API: http://localhost:8000"
    @echo "Health: http://localhost:8000/health"

clean: local-down local-clean
    @echo "All services stopped and cleaned up"
