# Multi-Agent on the Web

**Distributed Multi-Agent Orchestration Platform** - Coordinate multiple AI agents (Claude Code, Gemini, Ollama) across distributed machines to achieve 2-3x speed improvement and 4-layer quality assurance.

## Project Overview

Multi-Agent on the Web is a revolutionary distributed multi-agent orchestration platform that enables developers to:

- 🚀 **Parallel Execution** - Decompose tasks and distribute across multiple machines for 2-3x speed improvement
- 🤝 **Agent Collaboration** - Multiple agents review each other's work, collaborate in parallel, and vote on decisions
- 🔍 **4-Layer Quality Assurance** - Agent peer review + Human checkpoints + Voting mechanism + Evaluation framework
- 📊 **Real-time Visualization** - Monitor all agents and machines with live status updates
- 🎯 **Semi-Automated** - Maintain human control at critical decision points

## Core Features

### 1. Distributed Worker Management
- Support for 10+ machines as workers
- Real-time resource monitoring (CPU, memory, disk)
- Automatic failover and retry mechanisms
- Heartbeat-based health monitoring

### 2. Intelligent Task Orchestration
- Rule-based task decomposition with 6 task type templates
- Smart task allocation (tool matching 50% + resources 30% + privacy 20%)
- DAG dependency management and parallel scheduling
- Automatic subtask dependency resolution

### 3. Multi-AI Tool Integration
- **Claude Code** - MCP protocol integration for advanced coding
- **Gemini CLI** - Google AI SDK for general tasks
- **Local LLM (Ollama)** - Privacy-sensitive task execution
- Tool preference system for optimal AI selection

### 4. Agent Collaboration & Review
- Peer review: Agent B reviews Agent A's work
- Automatic correction (up to 3 revision cycles)
- Escalation to human review when quality threshold exceeded
- Multi-agent voting for critical decisions

### 5. Quantitative Evaluation Framework
- **5-Dimension Assessment**: Code Quality, Completeness, Security, Architecture Alignment, Testability
- Automated tools: pylint, ESLint, Bandit, radon
- Score < 7.0 automatically triggers checkpoint
- Real-time quality tracking and reporting

### 6. Human Checkpoint & Correction System
- Configurable checkpoint frequency (low/medium/high)
- Evaluation-driven intelligent triggering
- Structured feedback with accept/correct/reject decisions
- Contextual review with full work history

## Technology Stack

### Frontend
- **Flutter 3.16+** - Cross-platform UI (Desktop + Web)
- **Riverpod 2.4+** - State management
- **Material Design 3** - Design system
- **WebSocket Client** - Real-time updates

### Backend
- **FastAPI 0.104+** - Async API framework with automatic OpenAPI docs
- **PostgreSQL 15+** - Primary database with async support (asyncpg)
- **Redis 7+** - Real-time state, caching, and message storage
- **WebSocket** - Real-time bidirectional communication for log streaming
- **Alembic** - Database migration management
- **SQLAlchemy 2.0+** - Async ORM with declarative models
- **Pydantic 2.5+** - Data validation and settings management
- **python-jose** - JWT token handling
- **passlib + bcrypt** - Password hashing
- **structlog** - Structured logging
- **prometheus-client** - Metrics and monitoring

### Worker Agent
- **Python 3.11+** - Worker SDK
- **asyncio** - Asynchronous task execution
- **psutil** - Resource monitoring (CPU, memory, disk)
- **httpx** - Async HTTP client for API communication
- **websockets** - WebSocket client for real-time communication
- **anthropic** - Claude Code integration
- **google-generativeai** - Gemini CLI integration
- **pyyaml** - Configuration file parsing
- **aiofiles** - Async file operations

## 項目結構

```
bmad-test/
├── backend/              # FastAPI 後端
│   ├── src/
│   │   ├── api/         # REST API 端點
│   │   ├── services/    # 業務邏輯
│   │   ├── models/      # SQLAlchemy ORM
│   │   ├── repositories/# 數據訪問層
│   │   └── main.py      # 應用入口
│   ├── tests/           # 測試
│   ├── alembic/         # 數據庫遷移
│   └── requirements.txt
│
├── frontend/            # Flutter 前端
│   ├── lib/
│   │   ├── screens/     # UI頁面
│   │   ├── widgets/     # 自定義組件
│   │   ├── providers/   # Riverpod providers
│   │   └── services/    # API服務
│   └── pubspec.yaml
│
├── worker-agent/        # Worker Agent SDK
│   ├── src/
│   │   ├── agent/       # Agent核心
│   │   ├── tools/       # AI工具適配器
│   │   └── main.py      # CLI入口
│   └── config/          # 配置文件
│
├── docs/                # 項目文檔
│   ├── architecture.md  # 架構設計
│   ├── PRD.md          # 產品需求
│   ├── epics.md        # Epic拆分
│   └── sprint-1-plan.md# Sprint計劃
│
├── docker/              # Docker配置
└── scripts/             # 工具腳本
```

## Quick Start

### Prerequisites

- Docker 24+ & Docker Compose 2.23+
- Python 3.11+
- Flutter 3.16+ (optional, for frontend development)
- Git
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)
- API keys for AI tools (Anthropic, Google, or Ollama)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bmad-test
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys and settings
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Verify services are running**
   ```bash
   # Check health
   curl http://localhost:8002/api/v1/health

   # View API documentation
   # Open: http://localhost:8002/docs
   ```

5. **View logs**
   ```bash
   docker-compose logs -f
   ```

### Running Worker Agent

```bash
cd worker-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure worker
cp config/agent.yaml.example config/agent.yaml
# Edit config/agent.yaml with your settings

# Set API keys
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"

# Start worker
python src/main.py --config config/agent.yaml
```

### Running Frontend (Optional)

```bash
cd frontend

# Get dependencies
flutter pub get

# Run on web
flutter run -d chrome

# Or build for production
flutter build web
```

### Creating Your First Task

```bash
# Submit a task via API
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a simple REST API with user authentication",
    "task_type": "develop_feature",
    "checkpoint_frequency": "medium"
  }'

# Check task status
curl http://localhost:8002/api/v1/tasks
```

## 開發指南

### 運行測試

```bash
# 後端測試
cd backend
pytest

# 帶覆蓋率報告
pytest --cov=src --cov-report=html
```

### 代碼風格

項目使用 pre-commit hooks 自動格式化代碼：

```bash
# 安裝 pre-commit
pip install pre-commit
pre-commit install

# 手動運行
pre-commit run --all-files
```

### 數據庫遷移

```bash
cd backend

# 創建新遷移
alembic revision --autogenerate -m "描述"

# 執行遷移
alembic upgrade head

# 回滾
alembic downgrade -1
```

## Documentation

### User Documentation

- **[Installation Guide](docs/installation.md)** - Detailed installation instructions for all components
- **[User Guide](docs/user-guide.md)** - Complete tutorial on using the platform
- **[API Reference](docs/api-reference.md)** - Full API documentation with examples
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

### Technical Documentation

- **[Architecture Design](docs/architecture.md)** - Complete technical architecture
- **[Database Schema](docs/database-schema.md)** - Database structure and relationships
- **[Redis Schema](docs/redis-schema.md)** - Redis caching strategy
- **[Error Handling Guide](docs/ERROR-HANDLING-GUIDE.md)** - Error handling patterns
- **[Review Workflow Guide](docs/REVIEW-WORKFLOW-GUIDE.md)** - Agent review workflow

### Project Documentation

- **[Product Requirements](docs/PRD.md)** - Product requirements document
- **[Epic Breakdown](docs/epics.md)** - 9 Epics, 58 User Stories
- **[UX Design Specification](docs/ux-design-specification.md)** - UI/UX design guidelines
- **[Sprint Plans](docs/sprint-1-plan.md)** - Sprint planning and execution

## 性能目標

- ⚡ 任務提交響應時間: < 2s
- 🔄 WebSocket延遲: < 500ms
- 📊 儀表板加載時間: < 3s
- 👥 並發用戶: 100+
- 🖥️ Worker容量: 10+ 機器
- ⚙️ 並行任務: 20+

## 路線圖

### ✅ Phase 0-2: 已完成
- [x] Brainstorming & Product Brief
- [x] PRD & Epic Breakdown
- [x] UX Design Specification
- [x] Architecture Design & Validation
- [x] Sprint Planning

### 🚀 Phase 3: 實作中 (當前)
- [ ] Sprint 1: Foundation & Infrastructure (2 weeks)
- [ ] Sprint 2: Worker Management (2-3 weeks)
- [ ] Sprint 3: Task Coordination (2-3 weeks)
- [ ] Sprint 4: Flutter UI (3 weeks)
- [ ] Sprint 5: AI Integration (3-4 weeks)
- [ ] Sprint 6-8: Quality & Collaboration (6-7 weeks)
- [ ] Sprint 9: Testing & Launch (2-3 weeks)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on:

- Development environment setup
- Code style guidelines
- Testing requirements
- Pull request process
- Git commit conventions

## License

[To be determined]

## Support

- **Documentation**: [docs/README.md](docs/README.md)
- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions and share ideas

## Project Information

- **Author**: sir
- **Created**: 2025-11-11
- **Current Status**: Sprint 1 Development
- **Version**: 1.0.0-beta

## Acknowledgments

Built with the BMAD-METHOD (Brainstorm → Mockup → Architect → Develop) for systematic product development.

## Roadmap

- ✅ Sprint 1-2: Foundation & Worker Management (Completed)
- ✅ Epic 6: Agent Collaboration & Review (Completed)
- ✅ Epic 9: Error Handling & Testing (Completed)
- 🚀 Epic 10: Security & Stability (In Progress)
- 📋 Sprint 3-4: Task Coordination & Flutter UI
- 🤖 Sprint 5: AI Integration Enhancement
- 🔍 Sprint 6-8: Advanced Quality & Collaboration
- 🚢 Sprint 9: Production Launch

For detailed roadmap, see [docs/epics.md](docs/epics.md)

---

**Multi-Agent on the Web** - Orchestrate AI agents at scale
