# GarageSwarm - Build and Run Instructions

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ (via Docker)
- Redis 7+ (via Docker)

## Quick Start

### 1. Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d db redis
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server (port 8080)
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. Worker Agent Setup

```bash
cd worker-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure (copy and edit)
cp config/agent.yaml.example config/agent.yaml

# Run worker
python -m src.main
```

### 4. Desktop Worker Setup

```bash
cd worker-desktop

# Install dependencies
npm install

# Development mode
npm start

# Build for production
npm run build:win   # Windows
npm run build:mac   # macOS
npm run build:linux # Linux
```

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=src
```

### Worker Agent Tests

```bash
cd worker-agent
pytest tests/ -v
```

### Integration Tests

```bash
# Start all services first
docker-compose up -d

# Run integration tests
cd backend
pytest tests/integration/ -v
```

## API Endpoints

### Health Check
```bash
curl http://127.0.0.1:8080/api/v1/health
```

### User Registration
```bash
curl -X POST http://127.0.0.1:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "TestPass123"}'
```

### Login
```bash
curl -X POST http://127.0.0.1:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "TestPass123"}'
```

### Worker Registration
```bash
curl -X POST http://127.0.0.1:8080/api/v1/workers/register \
  -H "Content-Type: application/json" \
  -H "X-Worker-API-Key: YOUR_API_KEY" \
  -d '{"machine_id": "unique-id", "machine_name": "MyWorker", "tools": ["claude_code", "ollama"]}'
```

### Create Task
```bash
curl -X POST http://127.0.0.1:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"description": "Hello World", "tool_preference": "ollama"}'
```

## Environment Variables

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/garageswarm

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API
API_HOST=0.0.0.0
API_PORT=8080
```

### Worker Agent (.env)

```env
# Backend connection
BACKEND_URL=http://127.0.0.1:8080
WORKER_API_KEY=your-worker-api-key

# AI Tools
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_AI_API_KEY=your-google-key
OLLAMA_HOST=http://localhost:11434
```

## Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Rebuild and start
docker-compose up -d --build

# Reset database
docker-compose down -v
docker-compose up -d
```

## Troubleshooting

### Port 8000 in use
Backend defaults to port 8080 because port 8000 is often occupied by lemonade_server.

### Connection refused
Use `127.0.0.1` instead of `localhost` for IPv4 connections.

### Database connection error
Ensure PostgreSQL is running:
```bash
docker-compose ps
docker-compose up -d db
```

### Redis connection error
Ensure Redis is running:
```bash
docker-compose up -d redis
```
