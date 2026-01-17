# E2E Tests Quick Start Guide

## Quick Test Commands

### Run All E2E Tests
```bash
# From backend directory
pytest tests/e2e/ -v -m e2e
```

### Run Specific Test File
```bash
pytest tests/e2e/test_worker_lifecycle.py -v
pytest tests/e2e/test_task_execution.py -v
pytest tests/e2e/test_parallel_execution.py -v
pytest tests/e2e/test_review_workflow.py -v
pytest tests/e2e/test_evaluation.py -v
pytest tests/e2e/test_checkpoint.py -v
```

### Run Single Test
```bash
pytest tests/e2e/test_worker_lifecycle.py::test_worker_registration_flow -v
```

### Run with Coverage
```bash
pytest tests/e2e/ -v -m e2e --cov=src --cov-report=html
```

### Run in Docker (Recommended)
```bash
# From project root
docker-compose up -d postgres redis
docker-compose run --rm backend pytest tests/e2e/ -v -m e2e
```

## Test Categories

| Test File | Count | Focus Area |
|-----------|-------|------------|
| test_worker_lifecycle.py | 10 | Worker registration, heartbeat, shutdown |
| test_task_execution.py | 14 | Task submission, decomposition, progress |
| test_parallel_execution.py | 10 | DAG scheduling, multi-worker coordination |
| test_review_workflow.py | 10 | Agent collaboration, auto-fix workflow |
| test_evaluation.py | 12 | Quality scoring, threshold detection |
| test_checkpoint.py | 14 | Human review, user decisions |
| **Total** | **69** | **Complete system workflow** |

## Prerequisites

### Local Development
```bash
# Set database connection (if non-default)
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/multi_agent_test"

# Ensure PostgreSQL is running
# Run tests
pytest tests/e2e/ -v -m e2e
```

### Docker (Recommended)
```bash
# Start services
docker-compose up -d postgres redis

# Run tests in container
docker-compose run --rm backend pytest tests/e2e/ -v -m e2e

# Stop services
docker-compose down
```

## Common Issues

### Database Connection Error
```
ERROR: Connection refused
```
**Solution**: Ensure PostgreSQL is running
```bash
docker-compose up -d postgres
# Wait a few seconds for startup
pytest tests/e2e/ -v -m e2e
```

### Import Errors
```
ERROR: ModuleNotFoundError
```
**Solution**: Run from backend directory
```bash
cd backend
pytest tests/e2e/ -v -m e2e
```

### All Tests Error in Setup
```
ERROR at setup of test_*
```
**Solution**: Database not accessible, use Docker
```bash
docker-compose run --rm backend pytest tests/e2e/ -v -m e2e
```

## Test Output

### Expected Success Output
```
============================= test session starts =============================
...
tests/e2e/test_worker_lifecycle.py::test_worker_registration_flow PASSED
tests/e2e/test_worker_lifecycle.py::test_worker_heartbeat_mechanism PASSED
...
============================= 69 passed in X.XXs ==============================
```

### Coverage Report
```bash
pytest tests/e2e/ -v -m e2e --cov=src --cov-report=term-missing

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: multi_agent_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run E2E tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/multi_agent_test
        run: |
          cd backend
          pytest tests/e2e/ -v -m e2e --cov=src
```

## Next Steps

1. **Read the full documentation**: `README.md`
2. **Explore test scenarios**: Review individual test files
3. **Add new tests**: Use existing factories and patterns
4. **Check coverage**: Aim to maintain > 70% coverage

## Quick Reference

```bash
# Essential commands
pytest tests/e2e/ -v -m e2e                    # Run all E2E tests
pytest tests/e2e/ -v -m e2e -k worker          # Run tests matching "worker"
pytest tests/e2e/ -v -m e2e --lf               # Run last failed tests
pytest tests/e2e/ -v -m e2e --maxfail=1        # Stop after first failure
pytest tests/e2e/ -v -m e2e --tb=short         # Shorter traceback format

# With Docker
docker-compose run --rm backend bash           # Interactive shell
pytest tests/e2e/ -v -m e2e                    # Run tests from shell
```

## Support

For detailed information, see:
- `README.md` - Complete test documentation
- `conftest.py` - Fixture and factory implementations
- Individual test files - Specific test scenarios
- `STORY-9.1-E2E-TESTS-SUMMARY.md` - Complete project summary
