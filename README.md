# Science Talk Backend

A forum platform for sharing scientific results, methods, tools, and discussions. Built with Domain-Driven Design (DDD) and clean architecture principles.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

<p align="center">
  <img src="https://github.com/user-attachments/assets/ebde38a0-abdb-4d78-8b37-21eba459721b" alt="Science Talk Screenshot" width="800">
</p>

## Features

- **Six Post Types**: Result, Method, Review, Discussion, Ask, Tool
- **Bluesky Authentication**: Login with AT Protocol using your Bluesky account
- **Threaded Comments**: Unlimited nesting depth for rich discussions
- **Karma System**: Community-driven reputation based on upvotes
- **RESTful API**: Clean, documented endpoints built with FastAPI

## Architecture

This project follows **Clean Architecture** with strict separation of concerns:

```
talk/
├── domain/         # Business logic and entities
├── application/    # Use cases and orchestration
├── persistence/    # Database repositories
├── adapter/        # External service integrations (AT Protocol)
└── interface/      # HTTP API (FastAPI)
```

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Docker & Docker Compose
- [just](https://github.com/casey/just) (command runner)

### Installation

```bash
# Install dependencies
uv sync

# Start local environment (PostgreSQL + API)
just local up

# Verify everything works
curl http://localhost:8000/health
```

### Development

```bash
# View available commands
just --list

# Run tests
just test

# Run specific test types
just test unit
just test integration
just test-e2e

# Format code
just fix

# Run linter and type checker
just lint
```

## Configuration

Configuration is managed through environment variables. See `talk/config.py` for all available settings.

Key settings:
- `DATABASE__URL` - PostgreSQL connection string
- `AUTH__JWT_SECRET` - Secret key for JWT tokens
- `HOST` - API server hostname
- `FRONTEND_HOST` - Frontend application hostname

For local development, defaults are configured for `localhost`.

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Additional Commands

```bash
# Database migrations
just db-migrate              # Run migrations
just db-migration "name"     # Create new migration

# Local environment management
just local down              # Stop services
just local logs              # View logs
just local db-connect        # Connect to database
just local wipe              # Reset database

# Docker standalone
just docker-build            # Build image
just docker-serve            # Build and run container
```


## Project Structure

```
talk-backend/
├── talk/                   # Main application package
│   ├── domain/            # Business logic (entities, services)
│   ├── application/       # Use cases
│   ├── persistence/       # Database layer
│   ├── adapter/           # External integrations
│   ├── interface/         # API routes
│   └── util/              # Cross-cutting concerns
├── tests/                 # Test suite
├── migrations/            # Database migrations (Alembic)
├── deployment/            # Deployment configurations
└── scripts/               # Utility scripts
```

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 17
- **ORM**: SQLAlchemy (async)
- **Authentication**: AT Protocol (Bluesky)
- **DI Container**: dishka
- **Testing**: pytest
- **Linting**: ruff
- **Type Checking**: pyright
- **Package Manager**: uv

## Contributing

Contributions are welcome! This project demonstrates production-grade DDD patterns and clean architecture in Python.

Please ensure:
- All tests pass (`just test`)
- Code is formatted (`just fix`)
- No linting errors (`just lint`)
- Type checks pass (`just lint`)

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## Learn More

- [CLAUDE.md](CLAUDE.md) - Comprehensive architecture and development guide
- [backend-requirements.md](backend-requirements.md) - API specifications and data models

---

Built with clean architecture principles for maintainability and testability.
