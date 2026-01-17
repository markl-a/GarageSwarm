# GarageSwarm

A cross-platform multi-AI agent collaboration platform. Run your own AI swarm on whatever machines you have lying around - old laptops, desktop PCs, even that dusty server in the corner.

## Overview

Coordinate multiple AI CLI tools (Claude Code, Gemini CLI, Ollama) across distributed workers with a centralized control panel. No fancy infrastructure needed - just your garage-tier hardware.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Web Control Panel                            │
│                    (Flutter Web Dashboard)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                         │
│         Auth | Tasks | Workers | Workflows | WebSocket          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│Desktop Worker │   │ Docker Worker │   │ Mobile Worker │
│  (Electron)   │   │   (Python)    │   │  (Flutter)    │
│ Claude Code   │   │ Claude Code   │   │   API-based   │
│ Gemini CLI    │   │ Gemini CLI    │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

## Features

- **Multi-platform Workers**: Desktop (Electron), Docker (Python), Mobile (Flutter)
- **Multiple AI Tools**: Claude Code, Gemini CLI, Ollama, Aider, GitHub Copilot, Amazon Q, OpenAI API, and more
- **Extensible Tool System**: Plugin architecture for custom AI tool integration
- **DAG Workflows**: Complex task dependencies with parallel execution
- **User Authentication**: JWT-based auth with user-worker binding
- **Real-time Updates**: WebSocket for live status and task push
- **Hybrid Task Assignment**: Push + Pull modes for flexible distribution

## Project Structure

```
.
├── backend/           # FastAPI backend server
├── frontend/          # Flutter web control panel
├── worker-agent/      # Python worker agent (Docker)
├── worker-desktop/    # Electron desktop worker (Windows/Mac/Linux)
├── docker-compose.yml # Docker deployment
└── ARCHITECTURE.md    # Detailed architecture documentation
```

## Quick Start

### 1. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

Or with Docker:

```bash
docker-compose up -d
```

### 2. Start Desktop Worker

```bash
cd worker-desktop
npm install
npm start
```

### 3. Start Docker Worker

```bash
cd worker-agent
docker-compose up -d
```

## Development Status

**Current Version: v0.0.1**

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design.

### Phase 1: MVP (Current)

#### Backend ✅
- [x] User authentication (JWT)
- [x] Basic Task/Worker CRUD
- [x] Worker registration and heartbeat
- [x] WebSocket connection

#### Desktop Worker 🔄 In Progress
- [x] Electron app structure
- [x] Login page (API Key auth)
- [x] Dashboard UI
- [x] Windows testing
- [ ] Mac testing
- [ ] Linux testing
- [ ] End-to-end task execution flow

#### AI Tools 🔄 In Progress
- [x] Tool registry architecture
- [x] Claude Code - Anthropic CLI (basic)
- [ ] Gemini CLI - Google AI
- [ ] Ollama - Local LLM
- [ ] Aider - AI pair programming
- [ ] GitHub Copilot CLI
- [ ] Amazon Q Developer
- [ ] Cody - Sourcegraph AI
- [ ] OpenAI API (GPT-4, o1)
- [ ] Tool auto-detection
- [ ] Custom tool plugins

#### Frontend ⏸️ Planned
- [ ] Flutter Web Dashboard

### Phase 2: Workflow Engine
- [ ] Workflow data models
- [ ] DAG executor
- [ ] Workflow editor UI

### Phase 3: Mobile Workers
- [ ] Flutter app (Android/iOS)
- [ ] API-based AI tools

## License

MIT License - see [LICENSE](LICENSE) for details.
