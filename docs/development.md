# Development Environment Setup Guide

This guide will walk you through setting up a complete development environment for the Multi-Agent on the Web project.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Backend Development Setup](#backend-development-setup)
- [Worker Agent Development Setup](#worker-agent-development-setup)
- [Frontend Development Setup](#frontend-development-setup)
- [IDE Configuration](#ide-configuration)
- [Running Tests](#running-tests)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

Before starting, ensure you have the following software installed:

- **Python**: 3.11 or higher
  - Check version: `python --version`
  - Download: https://www.python.org/downloads/

- **Node.js**: 18 or higher (for tooling)
  - Check version: `node --version`
  - Download: https://nodejs.org/

- **Flutter**: 3.16 or higher
  - Check version: `flutter --version`
  - Download: https://flutter.dev/docs/get-started/install

- **Docker**: 24.0 or higher
  - Check version: `docker --version`
  - Download: https://www.docker.com/get-started

- **Docker Compose**: 2.23 or higher
  - Check version: `docker-compose --version`
  - Included with Docker Desktop

- **PostgreSQL**: 15 or higher (optional for local development without Docker)
  - Check version: `psql --version`
  - Download: https://www.postgresql.org/download/

- **Redis**: 7 or higher (optional for local development without Docker)
  - Check version: `redis-cli --version`
  - Download: https://redis.io/download

- **Git**: 2.30 or higher
  - Check version: `git --version`
  - Download: https://git-scm.com/downloads

- **Make**: For running Makefile commands
  - Windows: Install via Chocolatey (`choco install make`)
  - macOS: Pre-installed with Xcode Command Line Tools
  - Linux: Usually pre-installed (`sudo apt install make`)

### System Requirements

- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Disk Space**: 10GB free space
- **CPU**: Multi-core processor (4+ cores recommended)

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd bmad-test
```

### 2. Environment Configuration

Copy the example environment files and configure them:

```bash
# Backend environment
cp .env.example .env

# Edit .env with your configuration
# Required variables:
# - DATABASE_URL: PostgreSQL connection string
# - REDIS_URL: Redis connection string
# - SECRET_KEY: Random secret key for JWT tokens
# - ANTHROPIC_API_KEY: Your Anthropic API key (for Claude Code)
# - GOOGLE_API_KEY: Your Google API key (for Gemini)
```

Example `.env` configuration:

```ini
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres_dev_password@localhost:5432/multi_agent_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Backend
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=true

# AI Tool API Keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
GOOGLE_API_KEY=your-google-api-key-here

# Optional: Ollama (for local LLM)
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Install Pre-commit Hooks

Install pre-commit hooks for automatic code formatting:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Test hooks (optional)
pre-commit run --all-files
```

## Backend Development Setup

### 1. Create Virtual Environment

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### 3. Database Setup

#### Option A: Using Docker (Recommended)

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be ready (about 10 seconds)
docker-compose ps
```

#### Option B: Local Installation

If you prefer running PostgreSQL and Redis locally:

```bash
# Create database
createdb multi_agent_db

# Start Redis
redis-server
```

### 4. Run Database Migrations

```bash
# Make sure you're in the backend directory with venv activated
cd backend

# Run migrations
alembic upgrade head

# Verify migrations
alembic current
```

### 5. Run Development Server

```bash
# Start FastAPI development server with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or use the Makefile
make dev-backend
```

The backend API will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative API Docs: http://localhost:8000/redoc

### 6. Verify Backend Health

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2025-12-08T..."}
```

## Worker Agent Development Setup

### 1. Create Virtual Environment

```bash
cd worker-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### 3. Configuration File

Create and configure the agent configuration file:

```bash
# Create config directory if it doesn't exist
mkdir -p config

# Copy example config
cp config/agent.yaml.example config/agent.yaml
```

Edit `config/agent.yaml`:

```yaml
# Worker Agent Configuration

# Backend connection
backend_url: "http://localhost:8000"
use_websocket: true
use_polling_fallback: true
polling_interval: 10  # seconds

# Worker identification
machine_name: "dev-laptop-1"  # Change to your machine name

# Heartbeat
heartbeat_interval: 30  # seconds

# Shutdown
shutdown_timeout: 60  # seconds

# Resource monitoring
resource_monitoring:
  enabled: true
  cpu_threshold: 90
  memory_threshold: 85
  disk_threshold: 90

# AI Tools configuration
tools:
  claude_code:
    enabled: true
    api_key: "${ANTHROPIC_API_KEY}"  # From environment

  gemini_cli:
    enabled: true
    api_key: "${GOOGLE_API_KEY}"  # From environment

  ollama:
    enabled: false
    base_url: "http://localhost:11434"
    model: "llama2"

# Logging
logging:
  level: "INFO"
  file: "logs/worker-agent.log"
```

### 4. API Keys Setup

Set up your API keys as environment variables:

```bash
# On Windows (PowerShell):
$env:ANTHROPIC_API_KEY="your-anthropic-key"
$env:GOOGLE_API_KEY="your-google-key"

# On macOS/Linux:
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"

# Or create a .env file in worker-agent directory
echo "ANTHROPIC_API_KEY=your-key" > .env
echo "GOOGLE_API_KEY=your-key" >> .env
```

### 5. Run Worker Agent

```bash
# Make sure backend is running first!

# Run worker agent
python src/main.py --config config/agent.yaml

# Or use the Makefile
make dev-worker
```

You should see output like:

```
2025-12-08 15:30:00 [info] WorkerAgent initialized machine_id=abc123... machine_name=dev-laptop-1
2025-12-08 15:30:01 [info] Starting Worker Agent...
2025-12-08 15:30:02 [info] Worker Agent started worker_id=... tools=['claude_code', 'gemini_cli']
2025-12-08 15:30:02 [info] Starting heartbeat loop interval=30
2025-12-08 15:30:02 [info] WebSocket task receiving enabled
```

## Frontend Development Setup

### 1. Install Flutter

If you haven't installed Flutter yet:

```bash
# Verify Flutter installation
flutter doctor

# This will show you any missing dependencies
# Follow the instructions to install them
```

### 2. Install Dependencies

```bash
cd frontend

# Get Flutter dependencies
flutter pub get

# Verify dependencies
flutter pub deps
```

### 3. Generate Code (if needed)

The project uses code generation for Riverpod and JSON serialization:

```bash
# Generate code
flutter pub run build_runner build --delete-conflicting-outputs

# Or watch for changes during development
flutter pub run build_runner watch --delete-conflicting-outputs
```

### 4. Configuration

Create environment configuration:

```bash
# Copy example .env
cp .env.example .env
```

Edit `frontend/.env`:

```ini
API_BASE_URL=http://localhost:8000
WS_BASE_URL=ws://localhost:8000
```

### 5. Run Development Server

```bash
# Run on web (Chrome)
flutter run -d chrome

# Run on desktop (Windows/macOS/Linux)
flutter run -d windows  # or macos, linux

# Or use hot reload with specific device
flutter run -d chrome --web-renderer html
```

### 6. Development with Hot Reload

Flutter supports hot reload for fast development:

- Press `r` in terminal to hot reload
- Press `R` to hot restart
- Press `q` to quit

## IDE Configuration

### VS Code Setup

Recommended extensions:

1. **Python Extensions**
   - Python (`ms-python.python`)
   - Pylance (`ms-python.vscode-pylance`)
   - Python Debugger (`ms-python.debugpy`)

2. **Flutter Extensions**
   - Flutter (`Dart-Code.flutter`)
   - Dart (`Dart-Code.dart-code`)

3. **General Extensions**
   - Docker (`ms-azuretools.vscode-docker`)
   - Git Graph (`mhutchie.git-graph`)
   - Thunder Client (`rangav.vscode-thunder-client`) - API testing
   - YAML (`redhat.vscode-yaml`)

#### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "backend/tests"
  ],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "[dart]": {
    "editor.formatOnSave": true,
    "editor.rulers": [100]
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

#### Launch Configurations

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "src.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      }
    },
    {
      "name": "Worker Agent",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/worker-agent/src/main.py",
      "args": [
        "--config",
        "config/agent.yaml"
      ],
      "cwd": "${workspaceFolder}/worker-agent",
      "console": "integratedTerminal"
    },
    {
      "name": "Flutter: Web",
      "type": "dart",
      "request": "launch",
      "program": "lib/main.dart",
      "cwd": "${workspaceFolder}/frontend",
      "args": [
        "-d",
        "chrome"
      ]
    }
  ]
}
```

### PyCharm Configuration

1. **Create Python Interpreters**
   - File > Settings > Project > Python Interpreter
   - Add new interpreter pointing to `backend/venv/bin/python`
   - Add another for `worker-agent/venv/bin/python`

2. **Configure Code Style**
   - File > Settings > Editor > Code Style > Python
   - Set line length to 100
   - Enable "Optimize imports on the fly"

3. **Enable pytest**
   - File > Settings > Tools > Python Integrated Tools
   - Set Default test runner to "pytest"

4. **Database Tool**
   - View > Tool Windows > Database
   - Add PostgreSQL data source
   - Connection URL: `jdbc:postgresql://localhost:5432/multi_agent_db`

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_task_decomposer.py

# Run specific test
pytest tests/unit/test_task_decomposer.py::test_decompose_task

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with verbose output
pytest -v

# Run with print statements
pytest -s
```

View coverage report:
```bash
# Open coverage report in browser
open backend/htmlcov/index.html  # macOS
start backend/htmlcov/index.html  # Windows
xdg-open backend/htmlcov/index.html  # Linux
```

### Worker Agent Tests

```bash
cd worker-agent

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Frontend Tests

```bash
cd frontend

# Run all tests
flutter test

# Run with coverage
flutter test --coverage

# View coverage (requires lcov)
genhtml coverage/lcov.info -o coverage/html
open coverage/html/index.html
```

### Running All Tests

Use the Makefile from project root:

```bash
# Run all tests (backend + worker + frontend)
make test

# Run specific component tests
make test-backend
make test-worker
make test-frontend
```

## Development Workflow

### 1. Daily Development Flow

```bash
# Start services
make up  # Starts all Docker services

# In separate terminals:
make dev-backend  # Terminal 1: Backend
make dev-worker   # Terminal 2: Worker Agent
make dev-frontend # Terminal 3: Frontend

# View logs
make logs
```

### 2. Making Changes

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes to code
# ...

# Format code
make format

# Run linting
make lint

# Run tests
make test

# Commit changes (pre-commit hooks will run automatically)
git add .
git commit -m "feat: add new feature"

# Push changes
git push origin feature/your-feature-name
```

### 3. Database Changes

When modifying models:

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "description of changes"

# Review the generated migration file in backend/alembic/versions/

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### 4. Code Quality Checks

```bash
# Format Python code
black backend/src backend/tests
isort backend/src backend/tests

# Lint Python code
pylint backend/src

# Type check Python code
mypy backend/src

# Format Dart code
cd frontend
flutter format lib/

# Analyze Dart code
flutter analyze
```

### 5. Using Docker for Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild services after code changes
docker-compose up -d --build

# Access container shells
docker-compose exec backend bash
docker-compose exec postgres psql -U postgres -d multi_agent_db
docker-compose exec redis redis-cli

# View resource usage
docker stats
```

## Troubleshooting

### Backend Issues

#### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
psql -h localhost -U postgres -d multi_agent_db

# Reset database
docker-compose down -v  # Warning: This deletes all data!
docker-compose up -d postgres
cd backend && alembic upgrade head
```

#### Redis Connection Errors

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli ping  # Should return "PONG"

# Clear Redis cache
redis-cli FLUSHALL
```

#### Import Errors

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PWD}/backend:${PYTHONPATH}"

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### Worker Agent Issues

#### Agent Won't Connect to Backend

```bash
# Check backend is running
curl http://localhost:8000/health

# Check backend URL in config
cat worker-agent/config/agent.yaml

# Check API keys
echo $ANTHROPIC_API_KEY
echo $GOOGLE_API_KEY
```

#### Tool Execution Errors

```bash
# Test Claude Code availability
python -c "import anthropic; print(anthropic.__version__)"

# Test Gemini availability
python -c "import google.generativeai as genai; print('OK')"

# Check Ollama (if using)
curl http://localhost:11434/api/tags
```

### Frontend Issues

#### Flutter Build Errors

```bash
# Clean and rebuild
flutter clean
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs

# Update Flutter
flutter upgrade

# Check for issues
flutter doctor -v
```

#### API Connection Errors

```bash
# Check .env file exists
cat frontend/.env

# Verify backend is accessible
curl http://localhost:8000/health

# Check CORS settings in backend
```

### Pre-commit Hook Failures

```bash
# Re-install hooks
pre-commit uninstall
pre-commit install

# Run manually to see detailed errors
pre-commit run --all-files

# Skip hooks temporarily (not recommended)
git commit --no-verify -m "message"
```

### Docker Issues

```bash
# Reset Docker
docker-compose down -v
docker system prune -a

# Check disk space
docker system df

# View Docker logs
docker-compose logs -f [service-name]
```

### Performance Issues

```bash
# Check system resources
# Backend
cd backend && python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%, Memory: {psutil.virtual_memory().percent}%')"

# Check database performance
docker-compose exec postgres psql -U postgres -d multi_agent_db -c "SELECT * FROM pg_stat_activity;"

# Check Redis performance
redis-cli info stats
```

## Next Steps

Now that your development environment is set up:

1. Read the [Architecture Deep Dive](./architecture-deep-dive.md) to understand the system
2. Review the [Contributing Guide](./contributing.md) for development guidelines
3. Check the [Sprint Plan](./sprint-1-plan.md) to see current development priorities
4. Explore the [API Documentation](http://localhost:8000/docs) once backend is running

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Flutter Documentation](https://flutter.dev/docs)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [pytest Documentation](https://docs.pytest.org/)
