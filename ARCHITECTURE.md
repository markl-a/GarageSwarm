# Multi-Agent Platform Architecture

## Overview

A cross-platform (Windows, macOS, Linux, Android, iOS) multi-AI agent collaboration platform.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Web Control Panel                                  │
│                        (Flutter Web - Dashboard)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │
│  │ Dashboard │  │   Tasks   │  │ Workflows │  │  Workers  │  │  Settings │ │
│  │  (Overview)│  │  (CRUD)   │  │ (DAG Edit)│  │ (Manage)  │  │  (Config) │ │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ HTTPS / WebSocket
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Backend API (FastAPI)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────── Core Services ─────────────────────────────┐   │
│  │                                                                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐      │   │
│  │  │AuthService │  │UserService │  │TaskService │  │WorkerService│     │   │
│  │  │ - Login    │  │ - CRUD     │  │ - CRUD     │  │ - Register  │     │   │
│  │  │ - Register │  │ - Profile  │  │ - Assign   │  │ - Heartbeat │     │   │
│  │  │ - JWT      │  │ - Workers  │  │ - Status   │  │ - Status    │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘      │   │
│  │                                                                       │   │
│  │  ┌────────────┐  ┌────────────┐                                      │   │
│  │  │WorkflowSvc │  │ToolRegistry│                                      │   │
│  │  │ - DAG Exec │  │ - Claude   │                                      │   │
│  │  │ - Schedule │  │ - Gemini   │                                      │   │
│  │  │ - Monitor  │  │ - Ollama   │                                      │   │
│  │  └────────────┘  └────────────┘                                      │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────── Workflow Engine ───────────────────────────────┐   │
│  │                                                                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐      │   │
│  │  │DAGExecutor │  │TaskQueue   │  │Allocator   │  │Scheduler   │      │   │
│  │  │ - Topo Sort│  │ - Redis    │  │ - Scoring  │  │ - Cron     │      │   │
│  │  │ - Parallel │  │ - Priority │  │ - Balance  │  │ - Retry    │      │   │
│  │  │ - Retry    │  │ - Timeout  │  │ - Affinity │  │ - Timeout  │      │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘      │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────── Real-time Layer ───────────────────────────────┐   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │   │
│  │  │WebSocket Manager│  │Event Publisher  │  │Status Broadcaster│      │   │
│  │  │ - Connections   │  │ - Task Events   │  │ - Worker Status │       │   │
│  │  │ - Heartbeat     │  │ - Workflow Events│  │ - Progress      │       │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
           ▼                     ▼                     ▼
    ┌────────────┐        ┌────────────┐        ┌────────────┐
    │ PostgreSQL │        │   Redis    │        │  Storage   │
    │  Database  │        │Cache/Queue │        │   Files    │
    │            │        │            │        │            │
    │ - Users    │        │ - Sessions │        │ - Logs     │
    │ - Workers  │        │ - Queues   │        │ - Outputs  │
    │ - Tasks    │        │ - PubSub   │        │ - Artifacts│
    │ - Workflows│        │ - Blacklist│        │            │
    └────────────┘        └────────────┘        └────────────┘
           │                     │                     │
           └─────────────────────┼─────────────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
           ▼                     ▼                     ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   Desktop Worker    │ │   Desktop Worker    │ │   Mobile Worker     │
│  (Win/Mac/Linux)    │ │  (Win/Mac/Linux)    │ │  (Android/iOS)      │
│                     │ │                     │ │                     │
│ ┌─────────────────┐ │ │ ┌─────────────────┐ │ │ ┌─────────────────┐ │
│ │   Agent Core    │ │ │ │   Agent Core    │ │ │ │   Agent Core    │ │
│ │ - Connection    │ │ │ │ - Connection    │ │ │ │ - Connection    │ │
│ │ - Task Executor │ │ │ │ - Task Executor │ │ │ │ - Task Executor │ │
│ │ - Resource Mon  │ │ │ │ - Resource Mon  │ │ │ │ - Resource Mon  │ │
│ └─────────────────┘ │ │ └─────────────────┘ │ │ └─────────────────┘ │
│                     │ │                     │ │                     │
│ ┌─────────────────┐ │ │ ┌─────────────────┐ │ │ ┌─────────────────┐ │
│ │   AI Tools      │ │ │ │   AI Tools      │ │ │ │   AI Tools      │ │
│ │ - Claude Code   │ │ │ │ - Gemini CLI    │ │ │ │ - Claude API    │ │
│ │ - Gemini CLI    │ │ │ │ - Claude Code   │ │ │ │ - Gemini API    │ │
│ │ - Ollama        │ │ │ │ - Ollama        │ │ │ │                 │ │
│ └─────────────────┘ │ │ └─────────────────┘ │ │ └─────────────────┘ │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

---

## Directory Structure

```
bmad-test/
├── backend/                        # FastAPI Backend
│   ├── src/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py         # Auth endpoints
│   │   │       ├── users.py        # User management
│   │   │       ├── tasks.py        # Task CRUD
│   │   │       ├── workers.py      # Worker management
│   │   │       ├── workflows.py    # Workflow management
│   │   │       ├── websocket.py    # WebSocket endpoints
│   │   │       └── health.py       # Health checks
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── jwt_handler.py      # JWT creation/verification
│   │   │   ├── password.py         # Password hashing
│   │   │   └── dependencies.py     # Auth dependencies
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # SQLAlchemy base
│   │   │   ├── user.py             # User model
│   │   │   ├── worker.py           # Worker model
│   │   │   ├── user_worker.py      # User-Worker relationship
│   │   │   ├── task.py             # Task model
│   │   │   └── workflow.py         # Workflow, Node, Edge models
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Auth request/response
│   │   │   ├── user.py             # User schemas
│   │   │   ├── task.py             # Task schemas
│   │   │   ├── worker.py           # Worker schemas
│   │   │   └── workflow.py         # Workflow schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py     # Authentication logic
│   │   │   ├── user_service.py     # User management
│   │   │   ├── task_service.py     # Task operations
│   │   │   ├── worker_service.py   # Worker management
│   │   │   └── redis_service.py    # Redis operations
│   │   ├── workflow/
│   │   │   ├── __init__.py
│   │   │   ├── executor.py         # Workflow execution engine
│   │   │   ├── dag.py              # DAG utilities
│   │   │   ├── scheduler.py        # Task scheduling
│   │   │   └── allocator.py        # Task allocation
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── error_handler.py    # Global error handling
│   │   │   ├── request_id.py       # Request ID tracking
│   │   │   └── cors.py             # CORS configuration
│   │   ├── config.py               # Application settings
│   │   ├── database.py             # Database connection
│   │   ├── logging_config.py       # Logging setup
│   │   └── main.py                 # FastAPI application
│   ├── alembic/
│   │   └── versions/               # Database migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                       # Flutter Web Dashboard
│   ├── lib/
│   │   ├── config/                 # App configuration
│   │   ├── models/                 # Data models
│   │   ├── providers/              # Riverpod state
│   │   ├── services/               # API services
│   │   ├── screens/
│   │   │   ├── auth/               # Login/Register
│   │   │   ├── dashboard/          # Overview
│   │   │   ├── tasks/              # Task management
│   │   │   ├── workflows/          # Workflow editor
│   │   │   ├── workers/            # Worker management
│   │   │   └── settings/           # Settings
│   │   ├── widgets/                # Reusable components
│   │   ├── router/                 # Navigation
│   │   └── main.dart
│   ├── pubspec.yaml
│   └── web/
│
├── worker-agent/                   # Python Worker Agent
│   ├── src/
│   │   ├── agent/
│   │   │   ├── core.py             # Main agent class
│   │   │   ├── connection.py       # HTTP/WebSocket
│   │   │   ├── executor.py         # Task execution
│   │   │   └── monitor.py          # Resource monitoring
│   │   ├── tools/
│   │   │   ├── base.py             # Tool interface
│   │   │   ├── claude_code.py      # Claude Code CLI
│   │   │   ├── gemini_cli.py       # Gemini CLI
│   │   │   └── ollama.py           # Ollama local LLM
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── main.py
│   ├── config/
│   │   └── agent.yaml
│   └── requirements.txt
│
├── docker/
│   ├── prometheus/                 # Monitoring
│   └── init-db.sh
│
├── docker-compose.yml
├── ARCHITECTURE.md                 # This file
└── README.md
```

---

## Data Models

### Core Entities

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User                                       │
├─────────────────────────────────────────────────────────────────────┤
│ user_id: UUID (PK)                                                   │
│ username: String (unique)                                            │
│ email: String (unique)                                               │
│ password_hash: String                                                │
│ is_active: Boolean                                                   │
│ created_at: DateTime                                                 │
│ last_login: DateTime                                                 │
└─────────────────────────────────────────────────────────────────────┘
           │ 1:N                                    │ M:N
           ▼                                        ▼
┌──────────────────────┐                 ┌──────────────────────┐
│        Task          │                 │     UserWorker       │
├──────────────────────┤                 ├──────────────────────┤
│ task_id: UUID (PK)   │                 │ id: UUID (PK)        │
│ user_id: UUID (FK)   │                 │ user_id: UUID (FK)   │
│ worker_id: UUID (FK) │                 │ worker_id: UUID (FK) │
│ workflow_id: UUID    │                 │ role: Enum           │
│ description: Text    │                 │ is_active: Boolean   │
│ status: Enum         │                 │ added_at: DateTime   │
│ progress: Integer    │                 └──────────────────────┘
│ priority: Integer    │                            │
│ result: JSONB        │                            │
│ error: Text          │                            ▼
│ created_at: DateTime │                 ┌──────────────────────┐
│ started_at: DateTime │                 │       Worker         │
│ completed_at: DateTime                 ├──────────────────────┤
└──────────────────────┘                 │ worker_id: UUID (PK) │
           │                             │ machine_id: String   │
           │ N:1                         │ machine_name: String │
           ▼                             │ status: Enum         │
┌──────────────────────┐                 │ tools: JSONB         │
│      Workflow        │                 │ cpu_percent: Float   │
├──────────────────────┤                 │ memory_percent: Float│
│ workflow_id: UUID    │                 │ disk_percent: Float  │
│ user_id: UUID (FK)   │                 │ last_heartbeat: DateTime
│ name: String         │                 │ registered_at: DateTime
│ description: Text    │                 └──────────────────────┘
│ workflow_type: Enum  │
│ status: Enum         │
│ dag_definition: JSONB│
│ context: JSONB       │
│ result: JSONB        │
└──────────────────────┘
           │ 1:N
           ▼
┌──────────────────────┐        ┌──────────────────────┐
│    WorkflowNode      │───────▶│    WorkflowEdge      │
├──────────────────────┤        ├──────────────────────┤
│ node_id: UUID (PK)   │        │ edge_id: UUID (PK)   │
│ workflow_id: UUID    │        │ workflow_id: UUID    │
│ name: String         │        │ from_node_id: UUID   │
│ node_type: Enum      │        │ to_node_id: UUID     │
│ status: Enum         │        │ condition: JSONB     │
│ agent_config: JSONB  │        │ label: String        │
│ dependencies: UUID[] │        └──────────────────────┘
│ input_data: JSONB    │
│ output: JSONB        │
│ error: Text          │
│ retry_count: Integer │
└──────────────────────┘
```

---

## Workflow Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Sequential** | Linear pipeline, output → input | Code gen → Review → Test |
| **Concurrent** | Parallel execution, same task | Multiple workers process |
| **Graph (DAG)** | Complex dependencies | Complex project build |
| **Hierarchical** | Director + Workers | AI plans, workers execute |
| **Mixture** | Multi-expert parallel | Compare multiple AI tools |

### DAG Execution Flow

```
     ┌─────────┐
     │  Start  │
     └────┬────┘
          │
     ┌────▼────┐
     │ Node A  │ (Task: Generate code)
     └────┬────┘
          │
    ┌─────┴─────┐
    │           │
┌───▼───┐   ┌───▼───┐
│Node B │   │Node C │  (Parallel: Review & Test)
└───┬───┘   └───┬───┘
    │           │
    └─────┬─────┘
          │
     ┌────▼────┐
     │ Node D  │ (Condition: Pass?)
     └────┬────┘
          │
    ┌─────┴─────┐
    │ true      │ false
┌───▼───┐   ┌───▼───┐
│Node E │   │Node F │
│ Deploy│   │ Fix   │
└───────┘   └───┬───┘
                │
          (back to A)
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | User registration |
| POST | `/auth/login` | User login |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | User logout |
| GET | `/auth/me` | Get current user |
| POST | `/auth/change-password` | Change password |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks` | List tasks |
| POST | `/tasks` | Create task |
| GET | `/tasks/{id}` | Get task |
| PUT | `/tasks/{id}` | Update task |
| DELETE | `/tasks/{id}` | Delete task |
| POST | `/tasks/{id}/cancel` | Cancel task |

### Workers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/workers` | List workers |
| POST | `/workers/register` | Register worker |
| GET | `/workers/{id}` | Get worker |
| POST | `/workers/{id}/heartbeat` | Worker heartbeat |
| GET | `/workers/{id}/pull-task` | Pull task (worker) |

### Workflows
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/workflows` | List workflows |
| POST | `/workflows` | Create workflow |
| GET | `/workflows/{id}` | Get workflow |
| PUT | `/workflows/{id}` | Update workflow |
| DELETE | `/workflows/{id}` | Delete workflow |
| POST | `/workflows/{id}/execute` | Execute workflow |
| POST | `/workflows/{id}/pause` | Pause workflow |
| POST | `/workflows/{id}/resume` | Resume workflow |

### WebSocket
| Endpoint | Description |
|----------|-------------|
| `/ws/worker/{worker_id}` | Worker connection |
| `/ws/client/{user_id}` | Client real-time updates |

---

## Task Assignment Flow

### Hybrid Mode (Push + Pull)

```
                     ┌─────────────┐
                     │   Backend   │
                     └──────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐
        │Global Q │   │User Q   │   │Worker Q │
        └────┬────┘   └────┬────┘   └────┬────┘
             │             │             │
             └─────────────┼─────────────┘
                           │
                    ┌──────▼──────┐
                    │  Allocator  │
                    │             │
                    │ 1. Filter   │
                    │    - Tools  │
                    │    - Resources
                    │    - Permissions
                    │             │
                    │ 2. Score    │
                    │    - Match 40%
                    │    - Avail 30%
                    │    - Balance 20%
                    │    - Affinity 10%
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │ PUSH       │ PULL       │
              ▼            │            ▼
        ┌─────────┐        │      ┌─────────┐
        │WebSocket│        │      │  HTTP   │
        │ Push    │        │      │  GET    │
        └────┬────┘        │      └────┬────┘
             │             │           │
             └─────────────┼───────────┘
                           │
                    ┌──────▼──────┐
                    │   Worker    │
                    │  (Execute)  │
                    └─────────────┘
```

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | FastAPI | 0.104+ |
| **Database** | PostgreSQL | 15+ |
| **Cache/Queue** | Redis | 7+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Validation** | Pydantic | 2.5+ |
| **Auth** | python-jose | 3.3+ |
| **Frontend** | Flutter Web | 3.16+ |
| **State Mgmt** | Riverpod | 2.4+ |
| **Worker** | Python | 3.11+ |
| **AI Tools** | Claude Code, Gemini CLI, Ollama | - |
| **Container** | Docker | 24+ |
| **Monitoring** | Prometheus + Grafana | - |

---

## Implementation Phases

### Phase 1: MVP (Current)
- [x] Backend directory structure
- [x] Database models (User, Worker, Task, Workflow)
- [x] Auth module (JWT, Password hashing)
- [ ] Auth API endpoints
- [ ] Task CRUD API
- [ ] Worker registration API
- [ ] WebSocket connection
- [ ] Frontend login/register

### Phase 2: Workflow Engine
- [ ] Workflow execution engine
- [ ] DAG executor
- [ ] Sequential/Concurrent modes
- [ ] Workflow API
- [ ] Frontend workflow editor

### Phase 3: Multi-Tool Support
- [ ] Tool registry
- [ ] Gemini CLI integration
- [ ] Ollama integration
- [ ] Tool health checks

### Phase 4: Mobile Workers
- [ ] Flutter Worker App
- [ ] API-based tools
- [ ] Background service
- [ ] Battery optimization

### Phase 5: Production
- [ ] Task templates
- [ ] Monitoring/Alerting
- [ ] Audit logs
- [ ] Auto-scaling
