# Multi-Agent Backend

FastAPI backend for Multi-Agent on the Web platform.

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Start Development Server

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or using the shortcut:
```bash
python -m uvicorn src.main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_database.py

# Run tests matching pattern
pytest -k "test_worker"
```

## Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
pylint src/

# Type check
mypy src/
```

## Project Structure

```
backend/
├── src/
│   ├── api/              # API endpoints
│   │   └── v1/
│   │       ├── health.py
│   │       ├── workers.py
│   │       ├── tasks.py
│   │       └── checkpoints.py
│   ├── services/         # Business logic
│   │   ├── task_service.py
│   │   ├── worker_service.py
│   │   ├── evaluation_service.py
│   │   └── peer_review_service.py
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── worker.py
│   │   ├── task.py
│   │   └── checkpoint.py
│   ├── repositories/     # Data access layer
│   │   ├── base_repository.py
│   │   ├── task_repository.py
│   │   └── worker_repository.py
│   ├── evaluators/       # Evaluation framework
│   │   ├── base_evaluator.py
│   │   ├── code_quality_evaluator.py
│   │   └── security_evaluator.py
│   ├── config.py         # Configuration
│   ├── database.py       # Database connection
│   ├── redis_client.py   # Redis connection
│   ├── dependencies.py   # Dependency injection
│   └── main.py           # Application entry point
├── tests/
│   ├── conftest.py       # Test fixtures
│   ├── unit/
│   └── integration/
├── alembic/              # Database migrations
│   ├── versions/
│   └── env.py
├── .env.example
├── requirements.txt
└── README.md
```

## Database Migrations

### Create a New Migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>
```

### View Migration History

```bash
alembic history
alembic current
```

## Environment Variables

See `.env.example` for all available configuration options.

Required:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Secret key for JWT tokens

Optional:
- `DEBUG` - Enable debug mode (default: false)
- `LOG_LEVEL` - Logging level (default: INFO)
- `CORS_ORIGINS` - Allowed CORS origins

## Development

### Adding a New API Endpoint

1. Create endpoint in `src/api/v1/<module>.py`
2. Add router to `src/main.py`
3. Create service in `src/services/<module>_service.py`
4. Add tests in `tests/integration/test_api_<module>.py`

### Adding a New Model

1. Create model in `src/models/<model>.py`
2. Create repository in `src/repositories/<model>_repository.py`
3. Generate migration: `alembic revision --autogenerate -m "Add <model> table"`
4. Apply migration: `alembic upgrade head`

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure database exists: `createdb multi_agent_db`

### Redis Connection Issues

- Verify Redis is running: `redis-cli ping`
- Check REDIS_URL in .env

### Import Errors

- Ensure virtual environment is activated
- Re-install dependencies: `pip install -r requirements.txt`
