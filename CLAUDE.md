# Talk DDD Project - CLAUDE.md

## 🎯 Project Overview

This is a **Domain-Driven Design (DDD) project** following clean architecture principles with a 4-layer structure. It provides a production-ready foundation for building business applications with clear separation of concerns, comprehensive testing, and modern development tooling.

## 🔬 Business Domain: Science Talk

**Science Talk** is a forum for sharing scientific results, methods, tools, and discussions. The platform enables researchers and scientists to share their work, discuss findings, and build on each other's contributions.

### Domain Concepts

#### Core Entities
- **Users**: Authenticated via AT Protocol (Bluesky), with karma tracking based on community engagement
- **Posts**: Scientific content submissions with six distinct types
- **Comments**: Threaded discussions with unlimited nesting depth
- **Votes**: Community-driven upvote system for quality curation

#### Post Types
The platform supports six specialized post types, each serving a different scientific communication need:

1. **Result** - Share published findings or experimental results (URL-based)
2. **Method** - Share experimental protocols, analytical methods, or techniques (URL-based)
3. **Review** - Share literature reviews, paper summaries, or critiques (URL-based)
4. **Discussion** - Start text-based discussions on scientific topics (text-based)
5. **Ask** - Ask questions to the scientific community (text-based)
6. **Tool** - Share software tools, datasets, or computational resources (URL-based)

#### Key Business Rules
- **Authentication**: All users authenticate via Bluesky using AT Protocol
- **Voting**: Upvote-only system (no downvotes) to encourage positive engagement
- **Karma**: Users accumulate karma from votes on their posts and comments
- **Comments**: Unlimited nesting with depth tracking for display optimization
- **Content Validation**: Title required (max 300 chars), URLs validated for URL-based posts
- **Soft Deletes**: Posts and comments are soft-deleted to preserve discussion context

#### Feed Sorting
- **Recent**: Chronological ordering by creation time
- **Active**: Sorted by recent comment activity for discovering ongoing discussions

### Technical Integration Points

#### External Services
- **AT Protocol (Bluesky)**: Primary authentication mechanism using DIDs and session tokens
- **PostgreSQL**: Relational database with support for recursive comment trees

#### API Surface
The application exposes RESTful endpoints for:
- Authentication flows (login, callback, refresh, logout)
- Post management (CRUD operations, voting)
- Comment management (nested replies, voting)
- User profiles (karma, activity history)

For detailed API specifications, data models, and technical requirements, see [backend-requirements.md](backend-requirements.md).

## 🏗️ Architecture Summary

**Clean Architecture** with dependency inversion and clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                          │
│  FastAPI • HTTP Routes • Request/Response Models           │
│  📁 talk/interface/                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer                          │
│  Use Cases • Orchestration • Transaction Boundaries        │
│  📁 talk/application/                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer (Core)                      │
│  Business Logic • Entities • Value Objects                 │
│  Repository Interfaces • Domain Services                   │
│  📁 talk/domain/                                           │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    ┌─────────┴─────────┐
                    │                   │
┌───────────────────────────┐ ┌─────────────────────────────┐
│   Persistence Layer       │ │     Adapter Layer           │
│  Repository Implementations│ │  External Integrations      │
│  Database • ORM Mapping   │ │  AT Protocol • APIs         │
│  📁 talk/persistence/     │ │  📁 talk/adapter/           │
└───────────────────────────┘ └─────────────────────────────┘
```

### 🎯 Key Architectural Principles

#### Use Case Design Pattern

**Use Cases are 1:1 with Routes** - Each HTTP route has exactly one use case that performs its business operation.

**Use Cases Call Services, NOT Other Use Cases** - Use cases orchestrate domain services to accomplish their goal. They do not call other use cases.

**Dependency Flow:**
```
Routes (Interface Layer)
  ↓ calls
Use Cases (Application Layer)
  ↓ calls
Domain Services (Domain Layer)
  ↓ calls
Repositories (via interfaces)
```

**Example:**
```python
# ✅ CORRECT: Use case calls services
class CreatePostUseCase:
    def __init__(
        self,
        post_service: PostService,      # Domain service
        tag_service: TagService,        # Domain service
        user_service: UserService,      # Domain service for loading user
    ):
        ...

    async def execute(self, request: CreatePostRequest):
        # Load user via service (1 DB query)
        user = await self.user_service.get_by_id(request.author_id)

        # Use domain services for business operations
        await self.tag_service.validate_tags_exist(request.tag_names)
        post = await self.post_service.create_post(
            author_id=user.id,
            author_handle=user.handle,
            ...
        )

# ❌ WRONG: Use case calls another use case
class CreatePostUseCase:
    def __init__(
        self,
        post_service: PostService,
        get_current_user_use_case: GetCurrentUserUseCase,  # ❌ Don't do this
    ):
        ...
```

**Why This Pattern?**

1. **Single Responsibility**: Each use case does one business operation
2. **No Tight Coupling**: Use cases are independent, not calling each other
3. **Services Are Reusable**: Domain services provide reusable logic (e.g., `UserService.get_by_id()`)
4. **Clear Boundaries**: Routes orchestrate, use cases execute, services provide domain logic
5. **Testability**: Use cases can be tested in isolation by mocking services

**Special Case - GetCurrentUserUseCase:**

`GetCurrentUserUseCase` is designed specifically for the `/auth/me` endpoint which returns full user profile with invitations and identities (3 DB queries). It should **NOT** be used by other use cases. Instead:

- For user_id only: Use `JWTService.get_user_id_from_token()` (0 DB queries)
- For user data: Use `UserService.get_by_id()` (1 DB query)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- uv (package manager)
- Docker & Docker Compose
- just (command runner)

### Setup Development Environment
```bash
# 1. Install dependencies
just install

# 2. Start local environment (PostgreSQL + API)
just setup

# 3. Verify everything works
curl http://localhost:8000/health
```

### Key Commands
```bash
# Development
just dev                    # Start development server
just test                   # Run all tests
just test unit             # Run unit tests only
just test integration      # Run integration tests
just lint                  # Check code quality
just fix                   # Format and fix code

# Local Environment
just local-up              # Start PostgreSQL + API
just local-down            # Stop all services
just local-logs            # View service logs
just db-connect            # Connect to database

# Docker
just docker-build          # Build Docker image
just docker-serve          # Build and serve container
```

## 📁 Project Structure

```
talk/
├── talk/                          # Main application package
│   ├── domain/                     # 🏛️ Business logic (CORE)
│   │   ├── model/                  # Entities and aggregates (Pydantic)
│   │   ├── repository/             # Repository interfaces
│   │   ├── service/                # Domain services
│   │   ├── value/                  # Value objects and IDs
│   │   ├── error.py                # Domain exceptions
│   │   └── CLAUDE.md               # Domain layer guide
│   │
│   ├── application/                # 🎭 Use case orchestration
│   │   ├── usecase/                # Business operations
│   │   ├── base.py                 # Base use case patterns
│   │   └── CLAUDE.md               # Application layer guide
│   │
│   ├── persistence/                # 💾 Data persistence
│   │   ├── repository/             # Repository implementations
│   │   ├── database.py             # Database connection
│   │   ├── tables.py               # SQLAlchemy table definitions
│   │   ├── mappers.py              # Domain model ↔ DB mapping
│   │   └── CLAUDE.md               # Persistence layer guide
│   │
│   ├── adapter/                    # 🔌 External integrations
│   │   ├── atproto/                # AT Protocol / Bluesky
│   │   └── CLAUDE.md               # Adapter layer guide
│   │
│   ├── interface/                  # 🌐 External communication
│   │   ├── api/                    # HTTP API (FastAPI)
│   │   ├── error.py                # Interface exceptions
│   │   └── CLAUDE.md               # Interface layer guide
│   │
│   ├── util/                       # 🛠️ Cross-cutting concerns
│   │   ├── di/                     # Dependency injection
│   │   └── CLAUDE.md               # Utility layer guide
│   │
│   └── config.py                   # ⚙️ Application settings
│
├── migrations/                     # 🗄️ Database migrations (Alembic)
│   ├── versions/                   # Migration files
│   └── env.py                      # Alembic environment
│
├── tests/                          # 🧪 Test suite
│   ├── unit/                       # Fast, isolated tests
│   ├── integration/                # Component interaction tests
│   ├── e2e/                        # End-to-end API tests
│   ├── conftest.py                 # Test configuration
│   └── CLAUDE.md                   # Testing strategy guide
│
├── deployment/                     # 🚀 Deployment configurations
│   └── local/                      # Local development
│       ├── docker-compose.yml      # Services orchestration
│       ├── local.just              # Local commands
│       └── init.sql                # Quick bootstrap SQL
│
├── alembic.ini                     # Alembic configuration
├── Dockerfile                      # 🐳 Container definition
├── Justfile                        # ⚡ Command definitions
├── pyproject.toml                  # Project dependencies
├── GUIDE.md                        # 📖 Domain modeling guide
└── CLAUDE.md                       # 📚 This overview
```

## 🎯 Core Principles

### Domain-Driven Design
- **Ubiquitous Language** - Use domain expert terminology consistently
- **Bounded Contexts** - Clear boundaries around related concepts
- **Aggregate Roots** - Consistency boundaries and transaction scopes
- **Rich Domain Models** - Business logic in entities, not services
- **Dependency Inversion** - Domain depends on nothing, everything depends on domain

### Clean Architecture
- **Separation of Concerns** - Each layer has a specific responsibility
- **Dependency Rule** - Dependencies point inward toward domain
- **Interface Segregation** - Small, focused interfaces
- **Testability** - Easy to test each layer in isolation

### Development Practices
- **Test-Driven Development** - Write tests first, code second
- **Continuous Integration** - Automated testing and quality checks
- **Type Safety** - Full type annotations with pyright
- **Code Quality** - Linting with ruff, formatting with black
- **Documentation** - Self-documenting code with clear intent

## 🔄 Development Workflow

### 1. Understanding the Domain
**Before writing ANY code:**
- Read `GUIDE.md` for detailed domain modeling instructions
- Understand the business problem and requirements
- Identify key domain concepts and relationships
- Ask clarifying questions if anything is unclear

### 2. Layer-by-Layer Development
**Follow this order:**

1. **Domain Layer First** (`talk/domain/CLAUDE.md`)
   - Define value objects and identifiers
   - Create entities and aggregates (Pydantic models)
   - Define repository interfaces
   - Implement domain services for cross-entity operations

2. **Application Layer** (`talk/application/CLAUDE.md`)
   - Create use cases that orchestrate domain operations
   - Define request/response models for use cases
   - Handle transaction boundaries and error mapping

3. **Persistence Layer** (`talk/persistence/CLAUDE.md`)
   - Implement repository interfaces with PostgreSQL
   - Create SQLAlchemy table definitions
   - Build domain model ↔ database mappers
   - Configure database connection and session management

4. **Adapter Layer** (`talk/adapter/CLAUDE.md`)
   - Integrate external services (AT Protocol/Bluesky)
   - Create adapter implementations
   - Handle external API communication

5. **Interface Layer** (`talk/interface/CLAUDE.md`)
   - Create HTTP routes and endpoints
   - Define API request/response models
   - Add input validation and error handling

### 3. Testing Strategy
**Test at every layer** (`tests/CLAUDE.md`):
- **Unit Tests** - Fast, isolated domain logic tests
- **Integration Tests** - Layer interaction with real dependencies
- **E2E Tests** - Full API workflows with realistic scenarios

### 4. Quality Assurance
```bash
# Before committing
just test                   # All tests pass
just lint                   # No linting errors
just fix                    # Code is formatted
```

## 🧭 Layer-Specific Guidelines

Each layer has detailed implementation guidance:

### 📖 Layer Guides
- **[Domain Layer](talk/domain/CLAUDE.md)** - Business logic and domain modeling
- **[Application Layer](talk/application/CLAUDE.md)** - Use case orchestration
- **[Persistence Layer](talk/persistence/CLAUDE.md)** - Database and repository implementations
- **[Adapter Layer](talk/adapter/CLAUDE.md)** - External service integrations
- **[Interface Layer](talk/interface/CLAUDE.md)** - HTTP API and communication
- **[Util Layer](talk/util/CLAUDE.md)** - Cross-cutting concerns and DI
- **[Testing Strategy](tests/CLAUDE.md)** - Comprehensive testing approach

### 📚 Additional Resources
- **[backend-requirements.md](backend-requirements.md)** - Complete API specifications and data models for Science Talk
- **[GUIDE.md](GUIDE.md)** - Step-by-step domain modeling instructions
- **[Architecture Documentation](../ARCHITECTURE.md)** - Detailed architectural decisions

## 🛠️ Technology Stack

### Core Framework
- **FastAPI** - Modern, fast web framework with automatic API docs
- **Pydantic** - Data validation and settings management
- **dishka** - Dependency injection container

### Development Tools
- **uv** - Fast Python package manager
- **pytest** - Testing framework with async support
- **ruff** - Fast Python linter and formatter
- **pyright** - Static type checker
- **just** - Command runner for development tasks

### Infrastructure
- **PostgreSQL 17.5** - Primary database
- **Docker** - Containerization and local development
- **Docker Compose** - Multi-service orchestration

## 🚨 Important Reminders

### Before You Start Coding
1. **Read the GUIDE.md** - Essential for proper domain modeling
2. **Understand the business domain** - Ask questions if unclear
3. **Focus on the domain layer first** - Get the core business logic right
4. **Don't rush to implementation** - Plan the domain model carefully

### Code Quality Standards
- **Type everything** - Use full type annotations
- **Test everything** - Aim for high coverage, especially domain logic
- **Document decisions** - Explain why, not just what
- **Follow naming conventions** - Use domain terminology consistently

### Common Pitfalls to Avoid
- **Anemic domain models** - Put business logic in entities, not services
- **Leaky abstractions** - Don't let infrastructure concerns leak into domain
- **God objects** - Keep classes focused and cohesive
- **Missing tests** - Every piece of business logic should be tested
- **Skipping domain modeling** - Don't jump straight to implementation

## 🎯 Success Criteria

You'll know you're succeeding when:

### Domain Model Quality
- ✅ Domain experts can read and understand your code
- ✅ Business rules are clearly expressed in the domain layer
- ✅ Changes to requirements only affect the domain layer
- ✅ New features extend existing concepts naturally

### Code Quality
- ✅ All tests pass and provide good coverage
- ✅ No linting errors or type checking issues
- ✅ Clean, readable code with meaningful names
- ✅ Clear separation between layers

### Development Experience
- ✅ Easy to add new features and modify existing ones
- ✅ Fast feedback loop with comprehensive testing
- ✅ Reliable local development environment
- ✅ Clear understanding of where code belongs

## 🆘 Getting Help

### When You're Stuck
1. **Check the layer-specific CLAUDE.md** - Detailed guidance for each layer
2. **Review the GUIDE.md** - Step-by-step domain modeling process
3. **Look at the existing code** - See how patterns are implemented
4. **Ask specific questions** - Don't guess, clarify requirements

### Questions to Ask Yourself
- **Does this belong in this layer?** - Check the layer's CLAUDE.md guide
- **Is this business logic or infrastructure?** - Business logic goes in domain
- **Am I following DDD principles?** - Rich models, clear boundaries, ubiquitous language
- **Are my tests comprehensive?** - Cover behavior, not just happy paths
- **Is my code self-documenting?** - Use domain terminology and clear names

Remember: **This template is designed to grow with your domain. Start simple, follow the principles, and let the architecture guide your decisions.**

---

**Happy coding! 🚀**

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at specs/005-chore-migrate-deployment/plan.md
<!-- SPECKIT END -->
