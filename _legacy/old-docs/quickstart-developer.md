# Developer Quickstart Guide

Welcome to Multi-Agent on the Web! This guide will get you up and running in **5 minutes**.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Clone and Setup](#clone-and-setup)
3. [Environment Configuration](#environment-configuration)
4. [Database Initialization](#database-initialization)
5. [Running the Backend](#running-the-backend)
6. [Running a Worker Agent](#running-a-worker-agent)
7. [Running the Flutter Frontend](#running-the-flutter-frontend)
8. [Making Your First API Call](#making-your-first-api-call)
9. [Submitting Your First Task](#submitting-your-first-task)
10. [Troubleshooting](#troubleshooting-common-issues)

---

## Prerequisites

### Required Software

Ensure you have the following installed:

| Software | Minimum Version | Check Command | Download Link |
|----------|----------------|---------------|---------------|
| **Python** | 3.11+ | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Docker** | 24.0+ | `docker --version` | [docker.com](https://www.docker.com/get-started) |
| **Docker Compose** | 2.23+ | `docker-compose --version` | Included with Docker Desktop |
| **Git** | 2.30+ | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| **Flutter** (Optional) | 3.16+ | `flutter --version` | [flutter.dev](https://flutter.dev/docs/get-started/install) |
| **Node.js** (Optional) | 18.0+ | `node --version` | [nodejs.org](https://nodejs.org/) |

### Optional (for Development)

- **Make** - For using Makefile commands (Linux/Mac: pre-installed, Windows: via Chocolatey or WSL)
- **VSCode** or **IntelliJ IDEA** - Recommended IDEs
- **Postman** or **curl** - For testing APIs

### AI Tool API Keys

You'll need at least one of these:

- **Anthropic API Key** - For Claude Code integration ([console.anthropic.com](https://console.anthropic.com/))
- **Google AI API Key** - For Gemini CLI ([aistudio.google.com](https://aistudio.google.com/))
- **Ollama** - Local LLM (no API key needed) ([ollama.ai](https://ollama.ai/))

---

## Clone and Setup

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone <your-repository-url> bmad-test
cd bmad-test

# Verify project structure
ls -la
# You should see: backend/, frontend/, worker-agent/, docs/, docker-compose.yml
```

### Step 2: Quick Setup with Docker (Recommended)

**Windows (PowerShell):**
```powershell
# Start all services (PostgreSQL, Redis, Backend)
docker-compose up -d

# Check services are running
docker-compose ps
```

**Linux/Mac (Bash):**
```bash
# Start all services
docker-compose up -d

# Check services are running
docker-compose ps
```

**Expected output:**
```
NAME                      STATUS              PORTS
multi_agent_postgres      Up 30 seconds       0.0.0.0:5432->5432/tcp
multi_agent_redis         Up 30 seconds       0.0.0.0:6379->6379/tcp
multi_agent_backend       Up 10 seconds       0.0.0.0:8002->8000/tcp
```

---

## Environment Configuration

### Backend Configuration

Create `.env` file in the `backend/` directory:

```bash
# Navigate to backend directory
cd backend

# Copy example environment file
cp .env.example .env
```

Edit `backend/.env`:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres_dev_password@localhost:5432/multi_agent_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=true
LOG_LEVEL=INFO

# CORS (allow frontend origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://localhost:5173

# File Storage
FILE_STORAGE_PATH=./data/tasks

# Optional: AI Tool API Keys (for backend testing)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GOOGLE_API_KEY=your-google-api-key-here
```

### Worker Agent Configuration

```bash
# Navigate to worker-agent directory
cd ../worker-agent

# Copy example configuration
cp config/agent.yaml.example config/agent.yaml
```

Edit `worker-agent/config/agent.yaml`:

```yaml
# Worker Identification
machine_name: "dev-machine-1"
machine_id: "auto"  # Auto-generated if not set

# Backend Connection
backend_url: "http://localhost:8002"
api_base_path: "/api/v1"
heartbeat_interval: 30  # seconds

# AI Tools Configuration
ai_tools:
  claude:
    enabled: true
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-3-sonnet-20240229"
    max_tokens: 4096

  gemini:
    enabled: true
    api_key: "${GOOGLE_API_KEY}"
    model: "gemini-pro"

  ollama:
    enabled: false
    base_url: "http://localhost:11434"
    model: "codellama"

# Resource Monitoring
resource_monitoring:
  enabled: true
  cpu_threshold: 90
  memory_threshold: 85
  disk_threshold: 90

# Logging
logging:
  level: "INFO"
  file: "logs/worker-agent.log"
```

### Set Worker Agent Environment Variables

**Windows (PowerShell):**
```powershell
# Create .env file in worker-agent directory
Set-Content -Path ".env" -Value @"
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GOOGLE_API_KEY=your-google-api-key-here
"@
```

**Linux/Mac (Bash):**
```bash
# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GOOGLE_API_KEY=your-google-api-key-here
EOF
```

### Frontend Configuration (Optional)

```bash
# Navigate to frontend directory
cd ../frontend

# Copy example environment file
cp .env.example .env
```

Edit `frontend/.env`:

```bash
# Backend API Configuration
API_BASE_URL=http://localhost:8002/api/v1
WS_BASE_URL=ws://localhost:8002/ws

# Environment
ENVIRONMENT=development
```

---

## Database Initialization

The database is automatically initialized when you start Docker Compose, but here's how to do it manually:

### Automatic (via Docker)

```bash
# Database migrations run automatically on backend startup
docker-compose logs backend

# You should see:
# "Running database migrations..."
# "INFO  [alembic.runtime.migration] Running upgrade -> 001_initial_schema"
```

### Manual (for local development)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Verify migration
alembic current
# Output: 001_initial_schema (head)
```

### Create Test Data (Optional)

```python
# Create a simple script to add test data
# backend/scripts/seed_data.py

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.user import User
from src.models.worker import Worker

async def seed_data():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres_dev_password@localhost:5432/multi_agent_db"
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create test user
        user = User(username="developer", email="dev@example.com")
        session.add(user)
        await session.commit()
        print("✅ Test user created")

if __name__ == "__main__":
    asyncio.run(seed_data())
```

Run seed script:
```bash
python scripts/seed_data.py
```

---

## Running the Backend

### Option 1: Docker (Recommended)

Already running if you completed [Clone and Setup](#clone-and-setup)!

```bash
# Verify backend is running
curl http://localhost:8002/api/v1/health

# View logs
docker-compose logs -f backend
```

### Option 2: Local Development

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies (if not done already)
pip install -r requirements.txt

# Run backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Backend will start on http://localhost:8000
```

### Verify Backend is Running

1. **Health Check:**
   ```bash
   curl http://localhost:8002/api/v1/health
   # Expected: {"status":"ok","timestamp":"2025-12-09T..."}
   ```

2. **API Documentation:**
   Open in browser: [http://localhost:8002/docs](http://localhost:8002/docs)

   You'll see interactive Swagger UI with all available endpoints.

3. **Alternative API Docs (ReDoc):**
   Open in browser: [http://localhost:8002/redoc](http://localhost:8002/redoc)

---

## Running a Worker Agent

Worker agents run on separate machines (or locally for development) and execute AI-powered tasks.

### Step 1: Install Dependencies

```bash
cd worker-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Keys

Make sure you've set up the `.env` file in the `worker-agent` directory (see [Environment Configuration](#environment-configuration)).

### Step 3: Start Worker

```bash
# Start worker agent
python src/main.py --config config/agent.yaml

# You should see:
# INFO - Worker Agent starting...
# INFO - Loaded configuration from config/agent.yaml
# INFO - Connecting to backend at http://localhost:8002
# INFO - Worker registered successfully with ID: worker_abc123
# INFO - Starting heartbeat loop (interval: 30s)
# INFO - Worker agent is running. Press Ctrl+C to stop.
```

### Step 4: Verify Worker Registration

```bash
# Check registered workers
curl http://localhost:8002/api/v1/workers

# Expected output:
# {
#   "workers": [
#     {
#       "id": "worker_abc123",
#       "machine_name": "dev-machine-1",
#       "status": "online",
#       "available_tools": ["claude", "gemini"],
#       "resources": {
#         "cpu_percent": 15.2,
#         "memory_percent": 45.8,
#         "disk_percent": 52.1
#       }
#     }
#   ]
# }
```

### Worker Logs

```bash
# Worker logs are saved to logs/worker-agent.log
tail -f logs/worker-agent.log

# Windows (PowerShell):
Get-Content logs\worker-agent.log -Tail 20 -Wait
```

---

## Running the Flutter Frontend

### Step 1: Install Flutter Dependencies

```bash
cd frontend

# Get dependencies
flutter pub get

# Generate code (for Riverpod)
flutter pub run build_runner build --delete-conflicting-outputs
```

### Step 2: Run Frontend

**Web (Chrome):**
```bash
flutter run -d chrome
```

**Desktop (Windows):**
```bash
flutter run -d windows
```

**Desktop (macOS):**
```bash
flutter run -d macos
```

**Desktop (Linux):**
```bash
flutter run -d linux
```

### Step 3: Access Dashboard

The Flutter app will open automatically. Default views:

- **Dashboard** - Overview of all workers and tasks
- **Workers** - Monitor worker status and resources
- **Tasks** - View and manage tasks
- **Task Detail** - See task progress and subtasks
- **Checkpoints** - Review and approve agent work

---

## Making Your First API Call

### Using curl

**1. Health Check:**
```bash
curl http://localhost:8002/api/v1/health
```

**2. Get Workers:**
```bash
curl http://localhost:8002/api/v1/workers
```

**3. Create a Task:**
```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Python function to calculate the factorial of a number",
    "task_type": "code_generation",
    "requirements": {
      "language": "python",
      "include_tests": true,
      "include_docstring": true
    },
    "checkpoint_frequency": "medium"
  }'
```

**Expected Response:**
```json
{
  "task_id": "task_xyz789",
  "status": "pending",
  "description": "Create a Python function to calculate the factorial of a number",
  "created_at": "2025-12-09T10:30:00Z",
  "estimated_completion": "2025-12-09T10:35:00Z"
}
```

**4. Get Task Status:**
```bash
curl http://localhost:8002/api/v1/tasks/task_xyz789
```

### Using Postman

1. **Import Collection:**
   - Create new collection "Multi-Agent API"
   - Set base URL: `http://localhost:8002/api/v1`

2. **Add Requests:**
   - GET `/health` - Health check
   - GET `/workers` - List workers
   - POST `/tasks` - Create task
   - GET `/tasks/{task_id}` - Get task details
   - GET `/tasks` - List all tasks

3. **Test Endpoints:**
   Run each request and verify responses.

### Using Python

```python
import httpx
import asyncio
import json

async def test_api():
    base_url = "http://localhost:8002/api/v1"

    async with httpx.AsyncClient() as client:
        # Health check
        response = await client.get(f"{base_url}/health")
        print("Health:", response.json())

        # Get workers
        response = await client.get(f"{base_url}/workers")
        print("Workers:", response.json())

        # Create task
        task_data = {
            "description": "Write a FastAPI endpoint for user authentication",
            "task_type": "develop_feature",
            "requirements": {
                "framework": "fastapi",
                "authentication": "JWT",
                "include_tests": True
            },
            "checkpoint_frequency": "high"
        }
        response = await client.post(f"{base_url}/tasks", json=task_data)
        task = response.json()
        print("Created Task:", task)

        # Get task status
        task_id = task["task_id"]
        response = await client.get(f"{base_url}/tasks/{task_id}")
        print("Task Status:", response.json())

if __name__ == "__main__":
    asyncio.run(test_api())
```

Save as `test_api.py` and run:
```bash
python test_api.py
```

---

## Submitting Your First Task

### Task Types

The system supports different task types with specific templates:

| Task Type | Description | Example |
|-----------|-------------|---------|
| `code_generation` | Generate new code from scratch | "Create a REST API for user management" |
| `code_review` | Review existing code for issues | "Review authentication logic for security issues" |
| `bug_fix` | Fix a specific bug | "Fix memory leak in task scheduler" |
| `refactoring` | Improve code structure | "Refactor database queries to use async" |
| `documentation` | Generate documentation | "Write API documentation for all endpoints" |
| `testing` | Create tests | "Write unit tests for task service" |

### Checkpoint Frequency

Control how often human review is required:

- **`low`** - Review only at major milestones (20% of subtasks)
- **`medium`** - Regular review checkpoints (40% of subtasks) - **Recommended**
- **`high`** - Frequent review (60% of subtasks) - Use for critical tasks

### Example 1: Simple Code Generation

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a Python class for a shopping cart with add, remove, and calculate total methods",
    "task_type": "code_generation",
    "requirements": {
      "language": "python",
      "include_tests": true,
      "include_docstring": true,
      "style": "PEP 8"
    },
    "checkpoint_frequency": "medium"
  }'
```

### Example 2: Feature Development with Dependencies

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Implement user authentication with JWT tokens",
    "task_type": "develop_feature",
    "requirements": {
      "framework": "fastapi",
      "database": "postgresql",
      "include_tests": true,
      "include_docs": true,
      "features": [
        "user registration",
        "login with email/password",
        "JWT token generation",
        "token refresh",
        "password reset"
      ]
    },
    "checkpoint_frequency": "high",
    "priority": "high"
  }'
```

### Example 3: Code Review

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Review the task scheduler code for performance and security issues",
    "task_type": "code_review",
    "requirements": {
      "file_paths": [
        "backend/src/services/task_scheduler.py",
        "backend/src/services/task_allocator.py"
      ],
      "review_aspects": [
        "security vulnerabilities",
        "performance bottlenecks",
        "code quality",
        "error handling"
      ],
      "provide_recommendations": true
    },
    "checkpoint_frequency": "low"
  }'
```

### Monitoring Task Progress

**1. WebSocket Connection (Real-time):**

```python
import asyncio
import websockets
import json

async def monitor_task(task_id):
    uri = f"ws://localhost:8002/ws?task_id={task_id}"

    async with websockets.connect(uri) as websocket:
        print(f"Connected to WebSocket for task {task_id}")

        async for message in websocket:
            data = json.loads(message)
            print(f"Update: {data['event']} - {data['message']}")

            if data['event'] == 'task_completed':
                print("Task completed!")
                break

# Run monitor
asyncio.run(monitor_task("task_xyz789"))
```

**2. Polling (Simple):**

```bash
# Check task status every 5 seconds
while true; do
  curl -s http://localhost:8002/api/v1/tasks/task_xyz789 | jq '.status'
  sleep 5
done
```

---

## Troubleshooting Common Issues

### Backend Issues

#### Issue: Database Connection Failed

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**
1. Check PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   # Should show: Up
   ```

2. Verify connection string in `.env`:
   ```bash
   DATABASE_URL=postgresql+asyncpg://postgres:postgres_dev_password@localhost:5432/multi_agent_db
   ```

3. Test connection:
   ```bash
   docker exec -it multi_agent_postgres psql -U postgres -c "\l"
   ```

4. Restart PostgreSQL:
   ```bash
   docker-compose restart postgres
   ```

#### Issue: Redis Connection Failed

**Symptoms:**
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**Solutions:**
1. Check Redis is running:
   ```bash
   docker-compose ps redis
   ```

2. Test Redis connection:
   ```bash
   docker exec -it multi_agent_redis redis-cli ping
   # Should return: PONG
   ```

3. Restart Redis:
   ```bash
   docker-compose restart redis
   ```

#### Issue: Port Already in Use

**Symptoms:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8002: bind: address already in use
```

**Solutions:**

**Windows:**
```powershell
# Find process using port 8002
netstat -ano | findstr :8002

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
# Find process using port 8002
lsof -i :8002

# Kill process
kill -9 <PID>
```

Or change port in `docker-compose.yml`:
```yaml
ports:
  - "8003:8000"  # Use port 8003 instead
```

### Worker Agent Issues

#### Issue: Cannot Connect to Backend

**Symptoms:**
```
ERROR - Failed to connect to backend at http://localhost:8002
```

**Solutions:**
1. Verify backend is running:
   ```bash
   curl http://localhost:8002/api/v1/health
   ```

2. Check `backend_url` in `config/agent.yaml`

3. Check firewall settings (allow port 8002)

4. Try using explicit IP instead of localhost:
   ```yaml
   backend_url: "http://127.0.0.1:8002"
   ```

#### Issue: AI Tool API Key Invalid

**Symptoms:**
```
ERROR - Anthropic API error: Invalid API key
```

**Solutions:**
1. Verify API key is set:
   ```bash
   # Windows (PowerShell)
   $env:ANTHROPIC_API_KEY

   # Linux/Mac
   echo $ANTHROPIC_API_KEY
   ```

2. Check API key in `.env` file has no quotes or extra spaces

3. Reload environment:
   ```bash
   # Linux/Mac
   source .env

   # Windows (PowerShell)
   Get-Content .env | ForEach-Object {
     $name, $value = $_.split('=')
     Set-Content env:\$name $value
   }
   ```

4. Test API key:
   ```python
   import anthropic
   client = anthropic.Anthropic(api_key="your-key-here")
   message = client.messages.create(
       model="claude-3-sonnet-20240229",
       max_tokens=100,
       messages=[{"role": "user", "content": "Hello"}]
   )
   print(message.content)
   ```

#### Issue: Worker Not Registering

**Symptoms:**
```
Worker registered but not showing in /api/v1/workers
```

**Solutions:**
1. Check worker logs:
   ```bash
   tail -f logs/worker-agent.log
   ```

2. Verify registration response:
   ```bash
   grep "registered successfully" logs/worker-agent.log
   ```

3. Check Redis for worker data:
   ```bash
   docker exec -it multi_agent_redis redis-cli
   > KEYS worker:*
   > GET worker:worker_abc123
   ```

4. Restart worker agent

### Frontend Issues

#### Issue: Flutter Dependencies Error

**Symptoms:**
```
Error: Could not resolve package 'flutter_riverpod'
```

**Solutions:**
1. Clean and re-fetch dependencies:
   ```bash
   flutter clean
   flutter pub get
   ```

2. Check Flutter version:
   ```bash
   flutter --version
   # Should be 3.16.0 or higher
   ```

3. Upgrade Flutter:
   ```bash
   flutter upgrade
   ```

#### Issue: Code Generation Failed

**Symptoms:**
```
Error: Could not generate code for Riverpod providers
```

**Solutions:**
1. Clean build artifacts:
   ```bash
   flutter pub run build_runner clean
   ```

2. Regenerate code:
   ```bash
   flutter pub run build_runner build --delete-conflicting-outputs
   ```

3. Check for syntax errors in provider files

#### Issue: Cannot Connect to Backend

**Symptoms:**
```
DioException: Connection refused
```

**Solutions:**
1. Check `API_BASE_URL` in `.env`:
   ```bash
   API_BASE_URL=http://localhost:8002/api/v1
   ```

2. Verify backend is running:
   ```bash
   curl http://localhost:8002/api/v1/health
   ```

3. Check CORS settings in backend `src/main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # For development only
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

### General Issues

#### Issue: Docker Compose Services Not Starting

**Solutions:**
1. Check Docker daemon is running:
   ```bash
   docker info
   ```

2. Check for port conflicts:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

3. View logs for specific service:
   ```bash
   docker-compose logs postgres
   docker-compose logs redis
   docker-compose logs backend
   ```

4. Rebuild containers:
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up -d
   ```

#### Issue: Tests Failing

**Solutions:**
1. Check test database is available:
   ```bash
   cd backend
   pytest tests/integration/test_api_health.py -v
   ```

2. Run specific test:
   ```bash
   pytest tests/unit/test_worker_service.py::test_register_worker -v
   ```

3. Check test coverage:
   ```bash
   pytest --cov=src --cov-report=html
   open htmlcov/index.html  # View coverage report
   ```

---

## Next Steps

Now that you have the platform running:

1. **Explore API Documentation:**
   - Swagger UI: [http://localhost:8002/docs](http://localhost:8002/docs)
   - ReDoc: [http://localhost:8002/redoc](http://localhost:8002/redoc)

2. **Read Architecture Docs:**
   - [Architecture Overview](architecture.md)
   - [Database Schema](database-schema.md)
   - [API Reference](api-reference.md)

3. **Try Advanced Features:**
   - [Error Handling Guide](ERROR-HANDLING-GUIDE.md)
   - [Review Workflow Guide](REVIEW-WORKFLOW-GUIDE.md)
   - [Adding AI Tools](adding-ai-tools.md)

4. **Run Tests:**
   ```bash
   cd backend
   pytest --cov=src --cov-report=html
   ```

5. **Explore Example Tasks:**
   ```bash
   cd backend/examples
   python submit_example_tasks.py
   ```

6. **Join Development:**
   - Read [Contributing Guide](../CONTRIBUTING.md)
   - Check [Open Issues](https://github.com/your-org/bmad-test/issues)
   - Join discussions on GitHub

---

## Quick Reference

### Essential Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart service
docker-compose restart backend

# Run backend tests
cd backend && pytest

# Run worker agent
cd worker-agent && python src/main.py --config config/agent.yaml

# Run Flutter frontend
cd frontend && flutter run -d chrome

# Check API health
curl http://localhost:8002/api/v1/health

# List workers
curl http://localhost:8002/api/v1/workers

# Create task
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Your task here", "task_type": "code_generation"}'
```

### Useful URLs

- **Backend API**: [http://localhost:8002](http://localhost:8002)
- **API Docs (Swagger)**: [http://localhost:8002/docs](http://localhost:8002/docs)
- **API Docs (ReDoc)**: [http://localhost:8002/redoc](http://localhost:8002/redoc)
- **Health Check**: [http://localhost:8002/api/v1/health](http://localhost:8002/api/v1/health)
- **PostgreSQL**: `localhost:5432` (user: postgres, pass: postgres_dev_password)
- **Redis**: `localhost:6379`

### Environment Cheat Sheet

| Component | Directory | Config File | Port |
|-----------|-----------|-------------|------|
| Backend | `backend/` | `.env` | 8002 |
| Worker Agent | `worker-agent/` | `config/agent.yaml` | N/A |
| Frontend | `frontend/` | `.env` | Varies |
| PostgreSQL | Docker | `docker-compose.yml` | 5432 |
| Redis | Docker | `docker-compose.yml` | 6379 |

---

## Support

Need help? Here are your options:

1. **Check Documentation:**
   - [docs/README.md](README.md)
   - [Troubleshooting Guide](troubleshooting.md)
   - [FAQ](faq.md)

2. **Search Issues:**
   - [GitHub Issues](https://github.com/your-org/bmad-test/issues)

3. **Ask Questions:**
   - [GitHub Discussions](https://github.com/your-org/bmad-test/discussions)

4. **Report Bugs:**
   - [Create New Issue](https://github.com/your-org/bmad-test/issues/new)

---

**Congratulations!** You're now ready to build with Multi-Agent on the Web!

Happy coding!
