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

# Docker commands (standalone)
docker-build:
    docker build -t talk-api:latest .

docker-run PORT="8000":
    docker run -p {{PORT}}:8000 --env-file .env talk-api:latest

docker-serve PORT="8000":
    just docker-build && docker run -p {{PORT}}:8000 --env-file .env talk-api:latest

docker-shell docker-build:
    docker run -it --rm talk-api:latest bash

docker-stop:
    docker stop talk-api && docker rm talk-api || true

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
