# Installation Guide

This guide provides detailed instructions for installing and setting up the Multi-Agent on the Web platform.

## Table of Contents

- [System Requirements](#system-requirements)
- [Backend Installation](#backend-installation)
- [Worker Agent Installation](#worker-agent-installation)
- [Frontend Installation](#frontend-installation)
- [Verification](#verification)
- [Next Steps](#next-steps)

## System Requirements

### Minimum Requirements

- **Operating System**: Linux, macOS, or Windows 10/11
- **Python**: 3.11 or higher
- **Docker**: 24.0 or higher
- **Docker Compose**: 2.23 or higher
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Disk Space**: 10GB free space
- **Internet**: Stable internet connection for AI API access

### Optional Requirements

- **Flutter**: 3.16+ (for frontend development)
- **Git**: 2.30+ (for version control)
- **Make**: For convenient development commands

### AI Tool API Keys

You'll need at least one of the following API keys:

- **Anthropic API Key**: For Claude Code integration
- **Google API Key**: For Gemini CLI integration
- **Ollama**: For local LLM (no API key needed)

## Backend Installation

The backend service includes FastAPI, PostgreSQL, and Redis components.

### Option 1: Docker Compose (Recommended)

This is the fastest way to get started with all services running.

#### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd bmad-test
```

#### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your settings
nano .env  # or use your preferred editor
```

Example `.env` configuration:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres_dev_password@localhost:5432/multi_agent_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Backend
SECRET_KEY=your-random-secret-key-here-change-in-production
DEBUG=true

# AI Tool API Keys (for Worker Agent)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GOOGLE_API_KEY=your-google-api-key-here

# Optional: Ollama (if using local LLM)
# OLLAMA_BASE_URL=http://localhost:11434
```

#### Step 3: Start All Services

```bash
# Start all services in the background
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

The following services will be started:

- **PostgreSQL**: Database on port 5432
- **Redis**: Cache on port 6379
- **Backend**: FastAPI server on port 8002

#### Step 4: Verify Services

```bash
# Check health endpoint
curl http://localhost:8002/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected"
# }

# View API documentation
# Open browser to: http://localhost:8002/docs
```

### Option 2: Manual Installation

For development or if you prefer not to use Docker.

#### Step 1: Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS (Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Windows:**
Download and install from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)

Create the database:
```bash
# Connect to PostgreSQL
psql -U postgres

# In psql console:
CREATE DATABASE multi_agent_db;
CREATE USER multi_agent WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE multi_agent_db TO multi_agent;
\q
```

#### Step 2: Install Redis

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download from [Redis for Windows](https://github.com/microsoftarchive/redis/releases)

#### Step 3: Set Up Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and settings

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`.

## Worker Agent Installation

Worker Agents execute tasks on distributed machines.

### Step 1: Navigate to Worker Agent Directory

```bash
cd worker-agent
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Worker Agent

```bash
# Copy example configuration
cp config/agent.yaml.example config/agent.yaml

# Edit configuration
nano config/agent.yaml  # or use your preferred editor
```

Example `agent.yaml` configuration:

```yaml
# Backend Connection
backend_url: "http://localhost:8002"

# Machine Information
machine_name: "Development Machine"

# Heartbeat Interval (seconds)
heartbeat_interval: 30

# Available AI Tools
tools:
  - claude_code
  - gemini_cli
  # - ollama  # Uncomment if Ollama is installed

# AI Tool Configurations
claude:
  api_key: "${ANTHROPIC_API_KEY}"
  model: "claude-3-sonnet-20240229"
  max_tokens: 4096

gemini:
  api_key: "${GOOGLE_API_KEY}"
  model: "gemini-pro"

ollama:
  base_url: "http://localhost:11434"
  model: "codellama"

# Resource Monitoring
resource_monitoring:
  enabled: true
  cpu_threshold: 90
  memory_threshold: 85
  disk_threshold: 90

# Task Execution
task_execution:
  max_concurrent_tasks: 3
  timeout_seconds: 600
  retry_attempts: 3

# Logging
logging:
  level: INFO
  format: json
  file: logs/worker-agent.log
```

### Step 5: Set Environment Variables

```bash
# On Linux/macOS:
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"

# On Windows (PowerShell):
$env:ANTHROPIC_API_KEY="your-anthropic-key"
$env:GOOGLE_API_KEY="your-google-key"

# Or add to .env file in worker-agent directory
```

### Step 6: Start Worker Agent

```bash
# Create logs directory
mkdir -p logs

# Start the worker
python src/main.py --config config/agent.yaml

# Expected output:
# [INFO] Registering worker with backend...
# [INFO] Worker registered successfully: worker_id=xxx
# [INFO] Starting heartbeat loop...
# [INFO] Worker is ready to accept tasks
```

### Multiple Workers

To set up multiple workers on different machines:

1. Install the worker agent on each machine
2. Use unique `machine_name` in each `agent.yaml`
3. Ensure all workers can reach the backend URL
4. Start each worker with the same backend configuration

## Frontend Installation

The Flutter frontend provides a web-based dashboard for managing tasks and workers.

### Step 1: Install Flutter

Follow the official Flutter installation guide for your platform:
- [Flutter Installation Guide](https://docs.flutter.dev/get-started/install)

Verify installation:
```bash
flutter doctor
```

### Step 2: Set Up Frontend

```bash
cd frontend

# Get dependencies
flutter pub get

# Configure environment
cp .env.example .env

# Edit .env with backend URL
nano .env
```

Example `.env` for frontend:

```bash
BACKEND_URL=http://localhost:8002
WS_URL=ws://localhost:8002/ws
```

### Step 3: Run Frontend

**For Web Development:**
```bash
flutter run -d chrome
```

**For Desktop (Windows/macOS/Linux):**
```bash
# Enable desktop support (first time only)
flutter config --enable-windows-desktop
flutter config --enable-macos-desktop
flutter config --enable-linux-desktop

# Run on desktop
flutter run -d windows  # or macos, linux
```

**Build for Production:**
```bash
# Build web version
flutter build web

# Serve with a web server
cd build/web
python -m http.server 3000
```

The frontend will be available at `http://localhost:3000` (or the port Flutter assigns).

## Verification

### 1. Verify Backend

```bash
# Health check
curl http://localhost:8002/api/v1/health

# List workers (should be empty initially)
curl http://localhost:8002/api/v1/workers

# View API documentation
# Open: http://localhost:8002/docs
```

### 2. Verify Worker Registration

After starting a worker agent, check that it's registered:

```bash
curl http://localhost:8002/api/v1/workers
```

Expected response:
```json
{
  "workers": [
    {
      "worker_id": "uuid-here",
      "machine_name": "Development Machine",
      "status": "online",
      "tools": ["claude_code", "gemini_cli"],
      "last_heartbeat": "2025-12-08T12:00:00Z"
    }
  ],
  "total": 1
}
```

### 3. Verify Frontend

1. Open the frontend in your browser
2. You should see:
   - Dashboard with worker list
   - Task list (empty initially)
   - Navigation menu

### 4. End-to-End Test

Create a test task to verify the full system:

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Test task: Echo hello world",
    "task_type": "testing",
    "checkpoint_frequency": "low"
  }'
```

Check the task status:
```bash
curl http://localhost:8002/api/v1/tasks
```

## Next Steps

After successful installation:

1. **Read the User Guide**: See [user-guide.md](user-guide.md) for how to use the platform
2. **Explore API**: Check [api-reference.md](api-reference.md) for API details
3. **Configure Workers**: Tune worker settings for your hardware
4. **Set Up Additional Workers**: Deploy workers on more machines
5. **Review Architecture**: Understand the system in [architecture.md](architecture.md)

## Troubleshooting

If you encounter issues during installation, see [troubleshooting.md](troubleshooting.md) for common problems and solutions.

## Updating

### Update Backend

```bash
cd backend
git pull
pip install -r requirements.txt
alembic upgrade head
docker-compose restart backend
```

### Update Worker Agent

```bash
cd worker-agent
git pull
pip install -r requirements.txt
# Restart the worker agent
```

### Update Frontend

```bash
cd frontend
git pull
flutter pub get
flutter build web
```

## Uninstalling

### Docker Installation

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: This deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Manual Installation

```bash
# Stop services
# Backend: Ctrl+C in terminal or kill process
# Workers: Ctrl+C in terminal or kill process

# Optionally drop database
psql -U postgres
DROP DATABASE multi_agent_db;
\q

# Remove Redis data
redis-cli FLUSHALL
```

## Support

For additional help:

- **Documentation**: [docs/README.md](README.md)
- **GitHub Issues**: Report bugs or request features
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)
