# CLAUDE.md

This file provides context for Claude Code when working on this project.

## Project Overview

**GarageSwarm** is a multi-AI agent orchestration platform that runs on regular consumer hardware. The goal is to coordinate multiple AI CLI tools (Claude Code, Gemini CLI, Ollama) across distributed workers.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.11+) |
| Frontend | Flutter Web |
| Desktop Worker | Electron + Node.js |
| Docker Worker | Python |
| Database | PostgreSQL |
| Cache/Queue | Redis |
| Auth | JWT (Access + Refresh tokens) |

## Project Structure

```
.
├── backend/           # FastAPI backend
│   ├── src/
│   │   ├── api/v1/    # API endpoints
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   └── auth/      # Authentication
│   └── alembic/       # Database migrations
├── frontend/          # Flutter web dashboard
├── worker-agent/      # Python worker (Docker)
│   └── src/
│       ├── agent/     # Core agent logic
│       ├── tools/     # AI tool integrations
│       └── auth/      # Tool authentication
├── worker-desktop/    # Electron desktop worker
│   └── src/
│       ├── main.js    # Electron main process
│       ├── preload.js # IPC bridge
│       ├── worker-service.js  # Backend communication
│       └── pages/     # UI pages
└── docker-compose.yml
```

## Key Concepts

### Workers
Workers are machines that execute AI tasks. They can be:
- **Desktop**: Electron app for Windows/Mac/Linux
- **Docker**: Python container for servers
- **Mobile**: Flutter app (planned)

### Tasks
Tasks are units of work assigned to workers. Each task includes:
- Description/instructions
- Required tool (e.g., claude_code, gemini_cli)
- Status tracking

### Workflows (Planned)
DAG-based workflow engine for complex multi-step tasks with dependencies.

## API Authentication

Two auth methods:
1. **User Auth**: JWT tokens for web dashboard users
2. **Worker Auth**: API keys (`X-Worker-API-Key` header) for workers

## Development Guidelines

### Backend
- Use async/await for all database operations
- Follow FastAPI dependency injection patterns
- Use Pydantic for request/response validation

### Worker Desktop (Electron)
- Main process handles backend communication
- Renderer process is isolated (contextBridge)
- Use IPv4 (`127.0.0.1`) instead of `localhost` for connections

### Worker Agent (Python)
- Supports multiple AI CLI tools
- Tool authentication handled per-tool
- WebSocket + HTTP polling for task retrieval

## Common Commands

```bash
# Backend
cd backend
uvicorn src.main:app --reload --port 8000

# Desktop Worker
cd worker-desktop
npm start           # Development
npm run build:win   # Build Windows exe

# Docker Worker
cd worker-agent
docker-compose up -d
```

## MCP Integration

Gemini MCP server is configured for Claude Code integration:
- Location: `~/mcp-servers/gemini-mcp/`
- Config: `.claude/mcp.json`

Available MCP tools:
- `gemini_quick_query` - Quick questions
- `gemini_analyze_code` - Code analysis
- `gemini_codebase_analysis` - Full project analysis (1M token context)

## Current Version

`0.0.1` - Early development stage

## Notes

- Default backend URL: `http://127.0.0.1:8000` (or 8080 if 8000 is occupied)
- WebSocket endpoint: `/api/v1/workers/{worker_id}/ws`
- Worker heartbeat interval: 30 seconds
- See `SESSION_PROGRESS.md` for latest development status
