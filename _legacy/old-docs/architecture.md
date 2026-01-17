# Multi-Agent on the Web - Solution Architecture

**Author:** sir
**Date:** 2025-11-11
**Version:** 1.0
**Status:** Draft

---

## Executive Summary

This document defines the technical architecture for **Multi-Agent on the Web**, a distributed multi-agent orchestration platform that enables professional developers to coordinate multiple AI tools (Claude Code, Gemini CLI, Local LLM) across distributed machines with real-time visualization and human-supervised quality control.

**Architecture Goals:**

1. **Distributed Scalability** - Support 10+ Worker machines with 20+ parallel tasks
2. **Real-Time Responsiveness** - WebSocket latency < 500ms, task submission < 2s
3. **High Availability** - Worker uptime > 99%, automatic failover and retry
4. **Flexibility** - Easy to add new AI tools and extend functionality
5. **Developer Experience** - Clear APIs, comprehensive documentation, easy local development

**Key Architectural Decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Frontend** | Flutter 3.16+ (Desktop + Web) | Cross-platform, Material 3, excellent performance, single codebase |
| **Backend** | Python FastAPI 0.100+ | Async support, modern Python, excellent WebSocket support, automatic OpenAPI docs |
| **Worker Agent** | Python 3.11+ asyncio | Same language as backend, excellent async libraries, easy AI tool integration |
| **Database** | PostgreSQL 15+ | Robust ACID transactions, JSONB support, proven at scale |
| **Cache/Queue** | Redis 7+ | Fast in-memory operations, Pub/Sub for WebSocket fanout, task queue support |
| **Communication** | REST API + WebSocket | REST for CRUD, WebSocket for real-time updates (task progress, worker heartbeats, logs) |
| **Deployment** | Docker Compose (local/dev) | Consistent environments, easy multi-container orchestration |

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Component Architecture](#3-component-architecture)
4. [API Design](#4-api-design)
5. [Data Architecture](#5-data-architecture)
6. [Communication Protocols](#6-communication-protocols)
7. [Security Architecture](#7-security-architecture)
8. [Deployment Architecture](#8-deployment-architecture)
9. [Performance & Scalability](#9-performance--scalability)
10. [Implementation Patterns](#10-implementation-patterns)
11. [Appendices](#11-appendices)

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Multi-Agent on the Web                      │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐                    ┌──────────────────┐
│  Flutter Client  │◄──── WebSocket ───►│  FastAPI Backend │
│  (Desktop/Web)   │    + REST API      │   (Python 3.11+) │
│                  │                    │                  │
│ • Dashboard      │                    │ • Task Manager   │
│ • Task Submit    │                    │ • Worker Manager │
│ • Worker Monitor │                    │ • Scheduler      │
│ • Checkpoint UI  │                    │ • Evaluator      │
└──────────────────┘                    └────────┬─────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
         ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
         │  PostgreSQL 15+  │        │    Redis 7+      │        │ Worker Agents    │
         │   (Persistent)   │        │  (In-Memory)     │        │  (Python 3.11+)  │
         │                  │        │                  │        │                  │
         │ • Tasks          │        │ • Task Queue     │        │ Machine 1:       │
         │ • Workers        │        │ • WebSocket      │        │  • Claude Code   │
         │ • Subtasks       │        │   Connections    │        │  • Gemini CLI    │
         │ • Checkpoints    │        │ • Worker Status  │        │                  │
         │ • Evaluations    │        │ • Pub/Sub        │        │ Machine 2:       │
         └──────────────────┘        └──────────────────┘        │  • Ollama        │
                                                                  │  • Codex         │
                                                                  └──────────────────┘
```

### 1.2 Architecture Patterns

**Primary Pattern:** **Distributed Worker Pattern (Master-Worker)**
- **Master (Backend):** Orchestrates task distribution, monitors worker health, coordinates execution
- **Workers (Agents):** Execute AI tool tasks, report status, handle local failures

**Supporting Patterns:**
- **Event-Driven Architecture:** WebSocket events for real-time updates
- **CQRS (Simplified):** Separate read (GET) and write (POST/PUT) paths for performance
- **Repository Pattern:** Abstract data access for testability
- **Strategy Pattern:** AI tool execution strategies (Claude, Gemini, Ollama)

### 1.3 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Flutter)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Dashboard   │  │ Task Manager │  │    Worker    │  │  Checkpoint  │   │
│  │    Screen    │  │    Screen    │  │   Manager    │  │   Review     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │             │
│  ┌──────▼──────────────────▼─────────────────▼─────────────────▼────────┐  │
│  │              State Management (Riverpod)                              │  │
│  └──────┬─────────────────────────────────────────────────────────┬──────┘  │
│         │                                                           │         │
│  ┌──────▼──────────┐                                        ┌──────▼──────┐ │
│  │  REST Client    │                                        │  WebSocket  │ │
│  │  (dio/http)     │                                        │   Client    │ │
│  └─────────────────┘                                        └─────────────┘ │
└────────────────────────────────┬────────────────┬──────────────────────────┘
                                 │                │
                    REST API     │                │     WebSocket
                    (JSON)       │                │     (JSON Events)
                                 │                │
┌────────────────────────────────▼────────────────▼──────────────────────────┐
│                            BACKEND (FastAPI)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                       FastAPI Application                               │ │
│  └────────┬───────────────────────────────────────────────────┬───────────┘ │
│           │                                                    │              │
│  ┌────────▼────────┐  ┌────────────────┐  ┌─────────────────▼───────────┐ │
│  │   Task Manager  │  │ Worker Manager │  │   WebSocket Manager         │ │
│  │                 │  │                │  │                             │ │
│  │ • Submit Task   │  │ • Registration │  │ • Connection Pool           │ │
│  │ • Decompose     │  │ • Heartbeat    │  │ • Event Broadcasting        │ │
│  │ • Allocate      │  │ • Health Check │  │ • Client State Tracking     │ │
│  └────────┬────────┘  └────────┬───────┘  └─────────────────────────────┘ │
│           │                    │                                            │
│  ┌────────▼────────────────────▼──────────────────────────────┐            │
│  │                   Scheduler (APScheduler)                    │            │
│  │  • Task Queue Management                                    │            │
│  │  • Worker Health Monitoring (every 60s)                    │            │
│  │  • Checkpoint Trigger Logic                                 │            │
│  └────────┬─────────────────────────────────────────────────────┘            │
│           │                                                                   │
│  ┌────────▼───────────────────────────────────────────────────────────────┐ │
│  │                    Data Access Layer (Repositories)                    │ │
│  │  • TaskRepository  • WorkerRepository  • SubtaskRepository             │ │
│  └────────┬────────────────────────────────────────────┬───────────────────┘ │
│           │                                              │                    │
│  ┌────────▼───────────┐                        ┌────────▼───────────┐       │
│  │  SQLAlchemy ORM    │                        │   Redis Client     │       │
│  │  (Async Session)   │                        │   (aioredis)       │       │
│  └────────┬───────────┘                        └────────┬───────────┘       │
└───────────┼──────────────────────────────────────────────┼──────────────────┘
            │                                              │
            ▼                                              ▼
    ┌───────────────┐                            ┌─────────────────┐
    │ PostgreSQL 15+│                            │    Redis 7+     │
    │               │                            │                 │
    │ • ACID        │                            │ • Task Queue    │
    │ • JSONB       │                            │ • Pub/Sub       │
    │ • Full-Text   │                            │ • Session Store │
    └───────────────┘                            └─────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         WORKER AGENT (Python)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Worker Agent Core                              │   │
│  └────────┬────────────────────────────────────────────┬────────────────┘   │
│           │                                              │                    │
│  ┌────────▼──────────┐  ┌────────────────┐  ┌─────────▼──────────────────┐ │
│  │ Connection Manager│  │ Task Executor  │  │ Resource Monitor           │ │
│  │                   │  │                │  │                            │ │
│  │ • Register        │  │ • Receive Task │  │ • CPU Usage (psutil)       │ │
│  │ • Heartbeat (30s) │  │ • Execute AI   │  │ • Memory Usage             │ │
│  │ • WebSocket       │  │ • Report Result│  │ • Disk Usage               │ │
│  └────────┬──────────┘  └────────┬───────┘  └────────────────────────────┘ │
│           │                      │                                           │
│           │              ┌───────▼───────────────────────────────────────┐  │
│           │              │          AI Tool Adapters                     │  │
│           │              ├───────────────────────────────────────────────┤  │
│           │              │                                               │  │
│           │              │  ┌───────────────┐  ┌───────────────┐        │  │
│           │              │  │ Claude Code   │  │  Gemini CLI   │        │  │
│           │              │  │  (MCP Client) │  │ (Google AI SDK)│        │  │
│           │              │  └───────────────┘  └───────────────┘        │  │
│           │              │                                               │  │
│           │              │  ┌───────────────┐  ┌───────────────┐        │  │
│           │              │  │ Ollama (Local)│  │    Codex      │        │  │
│           │              │  │  (REST API)   │  │ (OpenAI API)  │        │  │
│           │              │  └───────────────┘  └───────────────┘        │  │
│           │              └───────────────────────────────────────────────┘  │
│           │                                                                  │
│           └──────────────────────► Backend (FastAPI)                        │
│                                    (WebSocket + REST)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

### 2.1 Frontend Stack

**Framework:** **Flutter 3.16+**

**Rationale:**
- ✅ **Cross-platform:** Single codebase for Desktop (Windows, macOS, Linux), Web, Mobile
- ✅ **Material Design 3:** First-class support, built-in components
- ✅ **Performance:** Compiled to native code (Desktop/Mobile), near-native web performance
- ✅ **Hot Reload:** Fast development iteration
- ✅ **Strong ecosystem:** pub.dev packages for all needs (HTTP, WebSocket, state management)

**Starter Template:** `momentous-developments/flutter-starter-app`
- Repository: https://github.com/momentous-developments/flutter-starter-app
- Features: Riverpod + GoRouter + Material 3 + Clean Architecture + Responsive Design
- Demo: https://flutter-material3-starter.web.app

**Core Dependencies:**

```yaml
dependencies:
  flutter: sdk: flutter

  # State Management
  flutter_riverpod: ^2.4.0          # State management + dependency injection
  riverpod_annotation: ^2.3.0       # Code generation for Riverpod

  # Routing
  go_router: ^12.0.0                # Declarative routing, deep linking

  # HTTP & WebSocket
  dio: ^5.4.0                       # HTTP client with interceptors
  web_socket_channel: ^2.4.0       # WebSocket client

  # UI & Design
  material: ^3.0.0                  # Material Design 3
  flutter_animate: ^4.3.0           # Smooth animations

  # Utilities
  intl: ^0.18.1                     # Internationalization, date formatting
  logger: ^2.0.2                    # Structured logging
  uuid: ^4.2.0                      # UUID generation

dev_dependencies:
  flutter_test: sdk: flutter
  flutter_lints: ^3.0.0             # Dart linting rules
  build_runner: ^2.4.0              # Code generation
  riverpod_generator: ^2.3.0        # Riverpod code generation
```

**Project Initialization Command:**

```bash
# Clone starter template
git clone https://github.com/momentous-developments/flutter-starter-app.git multi-agent-flutter

# Or create from scratch with Flutter CLI
flutter create --platforms=web,linux,windows,macos multi-agent-flutter
cd multi-agent-flutter
flutter pub add flutter_riverpod go_router dio web_socket_channel
```

### 2.2 Backend Stack

**Framework:** **Python FastAPI 0.100+**

**Rationale:**
- ✅ **Async-first:** Built on Starlette, excellent async/await support
- ✅ **WebSocket support:** First-class WebSocket handling
- ✅ **Modern Python:** Type hints, Pydantic validation, automatic OpenAPI docs
- ✅ **Performance:** Comparable to Node.js/Go for I/O-bound workloads
- ✅ **Developer experience:** Automatic API docs (Swagger UI), excellent error messages

**Starter Template:** `benavlabs/FastAPI-boilerplate`
- Repository: https://github.com/benavlabs/FastAPI-boilerplate
- Features: Pydantic V2 + SQLAlchemy 2.0 + PostgreSQL + Redis + Docker + Async

**Core Dependencies:**

```python
# requirements.txt
fastapi==0.104.1                  # Web framework
uvicorn[standard]==0.24.0         # ASGI server
pydantic==2.5.0                   # Data validation
pydantic-settings==2.1.0          # Settings management

# Database
sqlalchemy[asyncio]==2.0.23       # ORM with async support
asyncpg==0.29.0                   # PostgreSQL async driver
alembic==1.13.0                   # Database migrations

# Redis
redis[hiredis]==5.0.1             # Redis client with C extension
aioredis==2.0.1                   # Async Redis client

# WebSocket
websockets==12.0                  # WebSocket protocol
python-socketio==5.10.0           # Socket.IO (optional, for advanced use)

# Scheduling
apscheduler==3.10.4               # Background job scheduler

# Utilities
python-dotenv==1.0.0              # Environment variable loading
python-multipart==0.0.6           # File upload support
httpx==0.25.2                     # Async HTTP client (for testing, external APIs)
structlog==23.2.0                 # Structured logging

# Development
pytest==7.4.3                     # Testing framework
pytest-asyncio==0.21.1            # Async test support
httpx==0.25.2                     # Test client
```

**Project Initialization Command:**

```bash
# Clone starter template
git clone https://github.com/benavlabs/FastAPI-boilerplate.git multi-agent-backend
cd multi-agent-backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
alembic upgrade head
```

### 2.3 Worker Agent Stack

**Language:** **Python 3.11+**

**Rationale:**
- ✅ **Consistency:** Same language as backend, shared code possible
- ✅ **AI integration:** Excellent libraries for Claude (MCP), Gemini (Google AI SDK), Ollama (REST API)
- ✅ **Async support:** asyncio for non-blocking I/O
- ✅ **Rich ecosystem:** psutil for resource monitoring, websockets for communication

**Core Dependencies:**

```python
# requirements.txt (Worker Agent)
# HTTP & WebSocket
httpx==0.25.2                     # Async HTTP client
websockets==12.0                  # WebSocket client

# AI Tool Integration
anthropic==0.8.0                  # Claude API (for MCP alternative)
google-generativeai==0.3.0        # Gemini API
ollama-python==0.1.0              # Ollama Python client

# Resource Monitoring
psutil==5.9.6                     # Cross-platform system monitoring

# Utilities
python-dotenv==1.0.0              # Environment variable loading
pydantic==2.5.0                   # Data validation
structlog==23.2.0                 # Structured logging
aiofiles==23.2.1                  # Async file I/O

# Development
pytest==7.4.3                     # Testing framework
pytest-asyncio==0.21.1            # Async test support
```

**Project Structure:**

```
worker-agent/
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py              # WorkerAgent main class
│   │   ├── connection.py        # Connection management
│   │   ├── executor.py          # Task execution
│   │   └── monitor.py           # Resource monitoring
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseTool abstract class
│   │   ├── claude.py            # Claude Code integration
│   │   ├── gemini.py            # Gemini CLI integration
│   │   └── ollama.py            # Ollama integration
│   └── config.py                # Configuration management
├── tests/
├── config/
│   └── agent.yaml               # Worker configuration
├── requirements.txt
└── README.md
```

### 2.4 Database & Cache

**Primary Database:** **PostgreSQL 15+**

**Rationale:**
- ✅ **ACID compliance:** Critical for task state consistency
- ✅ **JSONB support:** Flexible storage for task metadata, evaluation scores
- ✅ **Full-text search:** Searchable task logs and descriptions
- ✅ **Proven at scale:** Battle-tested in production

**Version:** PostgreSQL 15.5 (latest stable as of 2025-11)

**Cache & Queue:** **Redis 7+**

**Rationale:**
- ✅ **Fast in-memory operations:** Worker status, task queue
- ✅ **Pub/Sub:** WebSocket event broadcasting (fanout pattern)
- ✅ **TTL support:** Automatic expiration for temporary data
- ✅ **Simple:** Easy to set up and use

**Version:** Redis 7.2.3 (latest stable as of 2025-11)

### 2.5 Development & Deployment Tools

**Containerization:** **Docker 24+ & Docker Compose 2.23+**
- Multi-container orchestration (Backend, PostgreSQL, Redis, Worker Agents)
- Consistent development environments

**CI/CD:** **GitHub Actions** (MVP), **GitLab CI** (enterprise alternative)
- Automated testing, linting, build, deployment

**Monitoring (Post-MVP):**
- **Prometheus + Grafana:** Metrics collection and visualization
- **Sentry:** Error tracking and performance monitoring

---

## 3. Component Architecture

### 3.1 Frontend Architecture (Flutter)

**Architecture Pattern:** **Clean Architecture + MVVM (via Riverpod)**

**Layer Separation:**

```
┌──────────────────────────────────────────────────────────────┐
│                    Presentation Layer                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Screens & Widgets (UI)                                │  │
│  │  • DashboardScreen                                     │  │
│  │  • TaskListScreen                                      │  │
│  │  • WorkerManagementScreen                              │  │
│  │  • CheckpointReviewDialog                              │  │
│  └────────────────────┬───────────────────────────────────┘  │
│                       │                                       │
│  ┌────────────────────▼───────────────────────────────────┐  │
│  │  State Management (Riverpod Providers)                 │  │
│  │  • dashboardStateProvider                              │  │
│  │  • taskListStateProvider                               │  │
│  │  • workerListStateProvider                             │  │
│  │  • webSocketProvider                                   │  │
│  └────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│                    Domain Layer                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Models (Pure Dart Objects)                          │ │
│  │  • Task                                              │ │
│  │  • Worker                                            │ │
│  │  • Subtask                                           │ │
│  │  • Checkpoint                                        │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│                    Data Layer                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Repositories (Abstract Interfaces)                  │ │
│  │  • TaskRepository                                    │ │
│  │  • WorkerRepository                                  │ │
│  └────────────────────┬─────────────────────────────────┘ │
│                       │                                    │
│  ┌────────────────────▼─────────────────────────────────┐ │
│  │  Data Sources                                        │ │
│  │  • ApiDataSource (REST API via dio)                 │ │
│  │  • WebSocketDataSource (Real-time events)           │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**

#### 3.1.1 State Management (Riverpod)

**Why Riverpod:**
- Compile-time safety (no runtime errors from Provider)
- Testability (easy to mock providers)
- Composability (providers can depend on other providers)
- No BuildContext required

**Example Providers:**

```dart
// providers/task_providers.dart

@riverpod
class TaskListNotifier extends _$TaskListNotifier {
  @override
  Future<List<Task>> build() async {
    // Fetch initial tasks
    final repo = ref.watch(taskRepositoryProvider);
    return repo.getTasks();
  }

  Future<void> submitTask(TaskSubmission submission) async {
    final repo = ref.read(taskRepositoryProvider);
    await repo.submitTask(submission);
    ref.invalidateSelf(); // Refresh task list
  }
}

@riverpod
Stream<TaskUpdate> taskUpdatesStream(TaskUpdatesStreamRef ref) {
  final ws = ref.watch(webSocketProvider);
  return ws.stream
      .where((event) => event.type == 'task_update')
      .map((event) => TaskUpdate.fromJson(event.data));
}
```

#### 3.1.2 WebSocket Management

**Connection Strategy:**
- Single WebSocket connection per client
- Automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- Heartbeat ping/pong every 30 seconds to detect stale connections
- Event-based message handling (subscribe to event types)

**Example Implementation:**

```dart
// services/websocket_service.dart

class WebSocketService {
  IOWebSocketChannel? _channel;
  final _eventController = StreamController<WebSocketEvent>.broadcast();
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  int _reconnectAttempts = 0;

  Stream<WebSocketEvent> get stream => _eventController.stream;

  Future<void> connect(String url, String token) async {
    try {
      _channel = IOWebSocketChannel.connect(
        Uri.parse(url),
        headers: {'Authorization': 'Bearer $token'},
      );

      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleClose,
      );

      _startHeartbeat();
      _reconnectAttempts = 0;
    } catch (e) {
      _scheduleReconnect();
    }
  }

  void _handleMessage(dynamic message) {
    final event = WebSocketEvent.fromJson(jsonDecode(message));
    _eventController.add(event);
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(Duration(seconds: 30), (_) {
      send({'type': 'ping'});
    });
  }

  void _scheduleReconnect() {
    _heartbeatTimer?.cancel();
    final delay = min(pow(2, _reconnectAttempts) * 1000, 30000);
    _reconnectAttempts++;

    _reconnectTimer = Timer(Duration(milliseconds: delay), () {
      connect(_lastUrl, _lastToken);
    });
  }
}
```

### 3.2 Backend Architecture (FastAPI)

**Architecture Pattern:** **Layered Architecture + Repository Pattern**

**Layer Separation:**

```
┌──────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI Routers)                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  REST API Endpoints                                    │  │
│  │  • /api/v1/tasks                                       │  │
│  │  • /api/v1/workers                                     │  │
│  │  • /api/v1/checkpoints                                 │  │
│  │  ┌──────────────────────────────────────────────────┐ │  │
│  │  │  WebSocket Endpoint                               │ │  │
│  │  │  • /ws (single endpoint, event-based routing)    │ │  │
│  │  └──────────────────────────────────────────────────┘ │  │
│  └────────────────────┬───────────────────────────────────┘  │
└───────────────────────┼──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                    Service Layer                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Business Logic Services                               │  │
│  │  • TaskService (task decomposition, allocation)       │  │
│  │  • WorkerService (registration, health monitoring)    │  │
│  │  • SchedulerService (task scheduling, retry logic)    │  │
│  │  • EvaluationService (quality scoring)                │  │
│  │  • CheckpointService (trigger logic, decision proc.)  │  │
│  └────────────────────┬───────────────────────────────────┘  │
└───────────────────────┼──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                    Repository Layer                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Data Access Repositories (Abstract DB operations)    │  │
│  │  • TaskRepository                                      │  │
│  │  • WorkerRepository                                    │  │
│  │  • SubtaskRepository                                   │  │
│  │  • CheckpointRepository                                │  │
│  └────────────────────┬───────────────────────────────────┘  │
└───────────────────────┼──────────────────────────────────────┘
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
┌───▼───────────────┐ ┌─▼──────────────┐ ┌─▼──────────────┐
│ PostgreSQL        │ │ Redis          │ │ WebSocket Mgr  │
│ (SQLAlchemy)      │ │ (aioredis)     │ │ (connections)  │
└───────────────────┘ └────────────────┘ └────────────────┘
```

**Key Components:**

#### 3.2.1 Task Service (Business Logic)

**Responsibilities:**
- Task submission and validation
- Task decomposition (AI-powered using LLM)
- Intelligent task allocation (scoring algorithm)
- Task state management
- Checkpoint trigger logic

**Task Decomposition Algorithm:**

```python
# services/task_service.py

class TaskService:
    async def decompose_task(
        self,
        task_description: str,
        task_requirements: dict
    ) -> List[Subtask]:
        """
        Uses LLM to intelligently decompose task into subtasks
        with dependencies and tool recommendations.
        """
        prompt = f"""
        Decompose the following software development task into atomic subtasks:

        Task: {task_description}
        Requirements: {json.dumps(task_requirements, indent=2)}

        For each subtask, provide:
        1. Subtask name (concise, action-oriented)
        2. Description (what needs to be accomplished)
        3. Dependencies (list of subtask indices that must complete first)
        4. Recommended tool (claude_code, gemini_cli, or ollama)
        5. Estimated complexity (1-5)

        Output as JSON array.
        """

        # Call decomposition LLM (e.g., Claude or Gemini)
        llm_response = await self.llm_client.complete(prompt)
        subtasks_json = json.loads(llm_response)

        # Convert to Subtask objects with DAG validation
        subtasks = []
        for idx, st_data in enumerate(subtasks_json):
            subtask = Subtask(
                id=uuid4(),
                task_id=task.id,
                name=st_data["name"],
                description=st_data["description"],
                dependencies=[subtasks[i].id for i in st_data["dependencies"]],
                recommended_tool=st_data["recommended_tool"],
                status=SubtaskStatus.PENDING,
            )
            subtasks.append(subtask)

        # Validate DAG (no cycles)
        self._validate_dag(subtasks)

        return subtasks
```

**Task Allocation Algorithm:**

```python
# services/task_service.py

async def allocate_subtask(self, subtask: Subtask) -> Optional[str]:
    """
    智能分配 subtask 到最合適的 worker
    評分規則：
    - 工具匹配 (50%)
    - 資源可用性 (30%)
    - 隱私需求 (20%)
    """
    available_workers = await self.worker_repo.get_available_workers()

    if not available_workers:
        return None

    scores = []
    for worker in available_workers:
        tool_score = self._calculate_tool_match_score(
            subtask.recommended_tool,
            worker.tools
        )  # 0-1

        resource_score = self._calculate_resource_score(
            worker.cpu_percent,
            worker.memory_percent,
            worker.disk_percent
        )  # 0-1

        privacy_score = self._calculate_privacy_score(
            subtask.privacy_level,
            worker.location  # local vs cloud
        )  # 0-1

        total_score = (
            tool_score * 0.5 +
            resource_score * 0.3 +
            privacy_score * 0.2
        )

        scores.append((worker.id, total_score))

    # Select worker with highest score
    best_worker_id = max(scores, key=lambda x: x[1])[0]
    return best_worker_id
```

#### 3.2.2 WebSocket Manager

**Connection Management:**

```python
# api/websocket.py

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # client_id -> WebSocket
        self.subscriptions: Dict[str, Set[str]] = {}  # event_type -> set of client_ids

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            # Remove from all subscriptions
            for event_type in self.subscriptions:
                self.subscriptions[event_type].discard(client_id)
            logger.info(f"Client {client_id} disconnected")

    async def subscribe(self, client_id: str, event_type: str):
        """Client subscribes to specific event types"""
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = set()
        self.subscriptions[event_type].add(client_id)

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast event to all subscribed clients"""
        if event_type not in self.subscriptions:
            return

        message = json.dumps({"type": event_type, "data": data})

        for client_id in self.subscriptions[event_type]:
            if client_id in self.active_connections:
                await self.active_connections[client_id].send_text(message)

# FastAPI WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),  # Authentication
    manager: ConnectionManager = Depends(get_connection_manager)
):
    # Verify token
    client_id = verify_token(token)

    await manager.connect(client_id, websocket)

    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            data = json.loads(message)

            # Handle message based on type
            if data["type"] == "subscribe":
                await manager.subscribe(client_id, data["event_type"])
            elif data["type"] == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        await manager.disconnect(client_id)
```

**Event Broadcasting (via Redis Pub/Sub):**

```python
# For multi-instance backend scaling (future)
# services/event_broadcaster.py

class RedisEventBroadcaster:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()

    async def publish(self, event_type: str, data: dict):
        """Publish event to Redis channel"""
        message = json.dumps({"type": event_type, "data": data})
        await self.redis.publish(f"events:{event_type}", message)

    async def subscribe(self, event_type: str, handler):
        """Subscribe to Redis channel and handle events"""
        await self.pubsub.subscribe(f"events:{event_type}")

        async for message in self.pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await handler(data)
```

### 3.3 Worker Agent Architecture

**Main Components:**

```
WorkerAgent
├── ConnectionManager     # WebSocket connection to backend
├── TaskExecutor          # Execute AI tool tasks
├── ResourceMonitor       # Monitor CPU, memory, disk
└── ToolRegistry          # Registered AI tools (Claude, Gemini, Ollama)
```

**WorkerAgent Core:**

```python
# agent/core.py

class WorkerAgent:
    def __init__(self, config_path: str = "config/agent.yaml"):
        self.config = self._load_config(config_path)
        self.machine_id = self._get_or_create_machine_id()
        self.connection_manager = ConnectionManager(
            backend_url=self.config.backend_url,
            worker_id=self.machine_id
        )
        self.task_executor = TaskExecutor(self.config.tools)
        self.resource_monitor = ResourceMonitor()
        self._running = False

    async def start(self):
        """Start worker agent"""
        logger.info(f"Starting Worker Agent {self.machine_id}")
        self._running = True

        # Connect to backend
        await self.connection_manager.connect()

        # Register with backend
        await self._register()

        # Start background tasks
        await asyncio.gather(
            self._heartbeat_loop(),
            self._resource_monitor_loop(),
            self._task_receiver_loop(),
        )

    async def _register(self):
        """Register worker with backend"""
        system_info = self.resource_monitor.get_system_info()
        tools = self.task_executor.get_available_tools()

        await self.connection_manager.send({
            "type": "worker_register",
            "data": {
                "machine_id": self.machine_id,
                "machine_name": self.config.machine_name,
                "system_info": system_info,
                "tools": tools,
            }
        })

    async def _heartbeat_loop(self):
        """Send heartbeat every 30 seconds"""
        while self._running:
            resources = self.resource_monitor.get_current_resources()
            await self.connection_manager.send({
                "type": "heartbeat",
                "data": {
                    "machine_id": self.machine_id,
                    "cpu_percent": resources["cpu"],
                    "memory_percent": resources["memory"],
                    "disk_percent": resources["disk"],
                }
            })
            await asyncio.sleep(30)

    async def _task_receiver_loop(self):
        """Receive and execute tasks from backend"""
        async for message in self.connection_manager.receive():
            if message["type"] == "execute_task":
                task_data = message["data"]
                asyncio.create_task(self._execute_task(task_data))

    async def _execute_task(self, task_data: dict):
        """Execute a task"""
        try:
            result = await self.task_executor.execute(
                tool=task_data["tool"],
                instructions=task_data["instructions"],
                context=task_data.get("context", {})
            )

            await self.connection_manager.send({
                "type": "task_result",
                "data": {
                    "subtask_id": task_data["subtask_id"],
                    "status": "completed",
                    "result": result,
                }
            })
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            await self.connection_manager.send({
                "type": "task_result",
                "data": {
                    "subtask_id": task_data["subtask_id"],
                    "status": "failed",
                    "error": str(e),
                }
            })
```

**Tool Executor (Strategy Pattern):**

```python
# agent/executor.py

class TaskExecutor:
    def __init__(self, tool_configs: dict):
        self.tools: Dict[str, BaseTool] = {}
        self._initialize_tools(tool_configs)

    def _initialize_tools(self, tool_configs: dict):
        """Initialize available AI tools"""
        if "claude_code" in tool_configs:
            self.tools["claude_code"] = ClaudeTool(tool_configs["claude_code"])
        if "gemini_cli" in tool_configs:
            self.tools["gemini_cli"] = GeminiTool(tool_configs["gemini_cli"])
        if "ollama" in tool_configs:
            self.tools["ollama"] = OllamaTool(tool_configs["ollama"])

    async def execute(
        self,
        tool: str,
        instructions: str,
        context: dict
    ) -> dict:
        """Execute task with specified tool"""
        if tool not in self.tools:
            raise ValueError(f"Tool {tool} not available")

        tool_instance = self.tools[tool]
        result = await tool_instance.execute(instructions, context)
        return result

    def get_available_tools(self) -> List[str]:
        return list(self.tools.keys())


# tools/base.py

class BaseTool(ABC):
    """Abstract base class for AI tools"""

    @abstractmethod
    async def execute(self, instructions: str, context: dict) -> dict:
        """Execute task and return result"""
        pass

# tools/claude.py

class ClaudeTool(BaseTool):
    def __init__(self, config: dict):
        # Initialize MCP client or Anthropic API client
        self.client = anthropic.AsyncAnthropic(api_key=config["api_key"])

    async def execute(self, instructions: str, context: dict) -> dict:
        response = await self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"Context:\n{json.dumps(context, indent=2)}\n\nTask:\n{instructions}"
            }]
        )

        return {
            "tool": "claude_code",
            "output": response.content[0].text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        }
```

### 3.4 Evaluation Service Architecture

**Purpose:** Automatically evaluate subtask outputs across 5 dimensions to ensure code quality and trigger checkpoints when quality thresholds are not met.

**Architecture Pattern:** **Registry Pattern + Strategy Pattern**

#### 3.4.1 Evaluation Pipeline

The evaluation service runs asynchronously after each subtask completion:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Evaluation Pipeline                          │
└─────────────────────────────────────────────────────────────────┘

Subtask Completed
      │
      ▼
┌──────────────────────┐
│ Trigger Evaluation   │
│ (Background Job)     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐         ┌────────────────────────────┐
│ EvaluatorRegistry    │────────►│ Select Evaluators          │
│ • Get all evaluators │         │ (Based on subtask type)    │
└──────────────────────┘         └──────┬─────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
         ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐
         │ CodeQuality      │  │ Completeness    │  │ Security         │
         │ Evaluator        │  │ Evaluator       │  │ Evaluator        │
         └────────┬─────────┘  └────────┬────────┘  └────────┬─────────┘
                  │                     │                     │
                  └──────────────┬──────┴─────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ Aggregate Scores       │
                    │ • Weight by dimension  │
                    │ • Calculate overall    │
                    └────────┬───────────────┘
                             │
                             ▼
                    ┌────────────────────────┐
                    │ Store Evaluation       │
                    │ (evaluations table)    │
                    └────────┬───────────────┘
                             │
                    ┌────────▼────────┐
                    │ Check Threshold │
                    │ (overall < 7?)  │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
    ┌───────────────────┐     ┌──────────────────┐
    │ Trigger Checkpoint│     │ Continue Task    │
    │ (Low score)       │     │ (Good score)     │
    └───────────────────┘     └──────────────────┘
```

#### 3.4.2 EvaluatorRegistry Pattern

**Backend Service:**

```python
# backend/src/services/evaluation_service.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum

class EvaluationDimension(str, Enum):
    CODE_QUALITY = "code_quality"
    COMPLETENESS = "completeness"
    SECURITY = "security"
    ARCHITECTURE_ALIGNMENT = "architecture_alignment"
    TESTABILITY = "testability"

class BaseEvaluator(ABC):
    """Abstract base class for all evaluators"""

    dimension: EvaluationDimension
    weight: float = 1.0  # Default weight, can be overridden

    @abstractmethod
    async def evaluate(self, subtask: Subtask) -> EvaluationResult:
        """
        Evaluate subtask output and return score + details

        Returns:
            EvaluationResult with:
            - score: float (0-10)
            - issues: List[Issue] (problems found)
            - suggestions: List[str] (improvement recommendations)
        """
        pass

    @abstractmethod
    def is_applicable(self, subtask: Subtask) -> bool:
        """Check if this evaluator applies to the subtask"""
        pass


class EvaluatorRegistry:
    """Registry of all available evaluators"""

    def __init__(self):
        self._evaluators: Dict[EvaluationDimension, BaseEvaluator] = {}

    def register(self, evaluator: BaseEvaluator):
        """Register an evaluator"""
        self._evaluators[evaluator.dimension] = evaluator

    def get_applicable_evaluators(self, subtask: Subtask) -> List[BaseEvaluator]:
        """Get evaluators applicable to this subtask"""
        return [
            evaluator
            for evaluator in self._evaluators.values()
            if evaluator.is_applicable(subtask)
        ]


class EvaluationService:
    """Orchestrates evaluation pipeline"""

    def __init__(
        self,
        registry: EvaluatorRegistry,
        subtask_repo: SubtaskRepository,
        evaluation_repo: EvaluationRepository,
        checkpoint_service: CheckpointService
    ):
        self.registry = registry
        self.subtask_repo = subtask_repo
        self.evaluation_repo = evaluation_repo
        self.checkpoint_service = checkpoint_service

    async def evaluate_subtask(self, subtask_id: UUID) -> Evaluation:
        """
        Run evaluation pipeline for a subtask

        Steps:
        1. Get applicable evaluators
        2. Run evaluators in parallel
        3. Aggregate scores
        4. Store evaluation
        5. Trigger checkpoint if score < threshold
        """
        subtask = await self.subtask_repo.get_by_id(subtask_id)

        # Get applicable evaluators
        evaluators = self.registry.get_applicable_evaluators(subtask)

        if not evaluators:
            logger.info(f"No evaluators applicable for subtask {subtask_id}")
            return None

        # Run evaluators in parallel
        results = await asyncio.gather(*[
            evaluator.evaluate(subtask)
            for evaluator in evaluators
        ])

        # Aggregate scores with weights
        dimension_scores = {}
        all_issues = []
        all_suggestions = []

        total_weight = sum(e.weight for e in evaluators)
        weighted_sum = 0

        for evaluator, result in zip(evaluators, results):
            dimension_scores[evaluator.dimension] = result.score
            all_issues.extend(result.issues)
            all_suggestions.extend(result.suggestions)
            weighted_sum += result.score * evaluator.weight

        overall_score = weighted_sum / total_weight if total_weight > 0 else 0

        # Store evaluation
        evaluation = await self.evaluation_repo.create(
            subtask_id=subtask_id,
            overall_score=overall_score,
            code_quality_score=dimension_scores.get(EvaluationDimension.CODE_QUALITY),
            completeness_score=dimension_scores.get(EvaluationDimension.COMPLETENESS),
            security_score=dimension_scores.get(EvaluationDimension.SECURITY),
            architecture_score=dimension_scores.get(EvaluationDimension.ARCHITECTURE_ALIGNMENT),
            testability_score=dimension_scores.get(EvaluationDimension.TESTABILITY),
            details={
                "issues": [issue.dict() for issue in all_issues],
                "suggestions": all_suggestions
            }
        )

        # Update subtask with evaluation score
        await self.subtask_repo.update(
            subtask_id,
            evaluation_score=overall_score
        )

        # Trigger checkpoint if score below threshold
        if overall_score < 7.0:
            logger.warning(
                f"Subtask {subtask_id} scored {overall_score:.1f} < 7.0, "
                f"triggering checkpoint"
            )
            await self.checkpoint_service.trigger_evaluation_checkpoint(
                subtask.task_id,
                subtask_id,
                evaluation
            )

        return evaluation
```

#### 3.4.3 Concrete Evaluator Implementations

**1. Code Quality Evaluator**

Uses static analysis tools (pylint, radon) to assess code quality:

```python
# backend/src/evaluators/code_quality_evaluator.py

import asyncio
import subprocess
import json
from pathlib import Path

class CodeQualityEvaluator(BaseEvaluator):
    dimension = EvaluationDimension.CODE_QUALITY
    weight = 1.5  # Higher weight for code quality

    def is_applicable(self, subtask: Subtask) -> bool:
        """Applicable if subtask generated code files"""
        output = subtask.output or {}
        files = output.get("files_created", [])
        return any(
            f.endswith((".py", ".js", ".ts", ".java", ".go"))
            for f in files
        )

    async def evaluate(self, subtask: Subtask) -> EvaluationResult:
        """Evaluate code quality using pylint and radon"""
        output = subtask.output or {}
        files = output.get("files_created", [])

        issues = []
        total_score = 0
        file_count = 0

        for file_path in files:
            if file_path.endswith(".py"):
                # Run pylint
                pylint_score = await self._run_pylint(file_path)
                # Run radon (cyclomatic complexity)
                complexity_score = await self._run_radon(file_path)

                file_score = (pylint_score * 0.7 + complexity_score * 0.3)
                total_score += file_score
                file_count += 1

                if pylint_score < 7:
                    issues.append(Issue(
                        severity="warning",
                        file=file_path,
                        message=f"Pylint score {pylint_score:.1f} below threshold"
                    ))

                if complexity_score < 7:
                    issues.append(Issue(
                        severity="warning",
                        file=file_path,
                        message="High cyclomatic complexity detected"
                    ))

            elif file_path.endswith((".js", ".ts")):
                # Run ESLint for JavaScript/TypeScript
                eslint_score = await self._run_eslint(file_path)
                total_score += eslint_score
                file_count += 1

        final_score = total_score / file_count if file_count > 0 else 8.0

        suggestions = []
        if final_score < 7:
            suggestions.append("Review code quality issues and refactor")
            suggestions.append("Reduce function complexity")
            suggestions.append("Follow coding standards (PEP 8, ESLint rules)")

        return EvaluationResult(
            score=final_score,
            issues=issues,
            suggestions=suggestions
        )

    async def _run_pylint(self, file_path: str) -> float:
        """Run pylint and return score (0-10)"""
        try:
            result = await asyncio.create_subprocess_exec(
                "pylint", file_path, "--output-format=json",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await result.communicate()

            # Parse pylint JSON output
            data = json.loads(stdout.decode())
            # pylint score is 0-10, return directly
            return data.get("score", 5.0)

        except Exception as e:
            logger.error(f"Pylint failed for {file_path}: {e}")
            return 5.0  # Neutral score on failure

    async def _run_radon(self, file_path: str) -> float:
        """Run radon complexity analysis and return score (0-10)"""
        try:
            result = await asyncio.create_subprocess_exec(
                "radon", "cc", file_path, "-j",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await result.communicate()

            data = json.loads(stdout.decode())
            # Average complexity: A=10, B=8, C=6, D=4, E=2, F=0
            complexity_map = {"A": 10, "B": 8, "C": 6, "D": 4, "E": 2, "F": 0}

            total = 0
            count = 0
            for func_data in data.values():
                for func in func_data:
                    rank = func.get("rank", "C")
                    total += complexity_map.get(rank, 6)
                    count += 1

            return total / count if count > 0 else 8.0

        except Exception as e:
            logger.error(f"Radon failed for {file_path}: {e}")
            return 8.0  # Good score on failure (benefit of doubt)

    async def _run_eslint(self, file_path: str) -> float:
        """Run ESLint and return score (0-10)"""
        try:
            result = await asyncio.create_subprocess_exec(
                "eslint", file_path, "--format=json",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await result.communicate()

            data = json.loads(stdout.decode())
            # Count errors and warnings
            error_count = sum(r["errorCount"] for r in data)
            warning_count = sum(r["warningCount"] for r in data)

            # Score: 10 - (errors * 0.5 + warnings * 0.2), min 0
            score = max(0, 10 - (error_count * 0.5 + warning_count * 0.2))
            return score

        except Exception as e:
            logger.error(f"ESLint failed for {file_path}: {e}")
            return 5.0
```

**2. Completeness Evaluator**

Uses LLM to assess if subtask fully addresses requirements:

```python
# backend/src/evaluators/completeness_evaluator.py

class CompletenessEvaluator(BaseEvaluator):
    dimension = EvaluationDimension.COMPLETENESS
    weight = 1.5  # High importance

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def is_applicable(self, subtask: Subtask) -> bool:
        """Always applicable"""
        return True

    async def evaluate(self, subtask: Subtask) -> EvaluationResult:
        """Use LLM to evaluate completeness"""

        prompt = f"""
You are a code reviewer evaluating if a subtask was completed fully.

**Subtask Description:**
{subtask.description}

**Subtask Output:**
{json.dumps(subtask.output, indent=2)}

**Requirements:**
{subtask.requirements or "No explicit requirements"}

**Evaluation Task:**
Assess if the subtask output fully addresses the description and requirements.

Rate completeness on a scale of 0-10:
- 10: Fully complete, all requirements met
- 7-9: Mostly complete, minor gaps
- 4-6: Partially complete, significant gaps
- 0-3: Incomplete, major requirements missing

Return JSON:
{{
  "score": <float 0-10>,
  "missing_items": [<list of missing features/requirements>],
  "suggestions": [<list of improvements>]
}}
"""

        response = await self.llm_client.complete(prompt)
        result_data = json.loads(response)

        issues = [
            Issue(
                severity="error" if result_data["score"] < 5 else "warning",
                file=None,
                message=f"Missing: {item}"
            )
            for item in result_data.get("missing_items", [])
        ]

        return EvaluationResult(
            score=result_data["score"],
            issues=issues,
            suggestions=result_data.get("suggestions", [])
        )
```

**3. Security Evaluator**

Uses Bandit (Python) and other security scanners:

```python
# backend/src/evaluators/security_evaluator.py

class SecurityEvaluator(BaseEvaluator):
    dimension = EvaluationDimension.SECURITY
    weight = 2.0  # Highest weight - security is critical

    def is_applicable(self, subtask: Subtask) -> bool:
        """Applicable if code files were created"""
        output = subtask.output or {}
        files = output.get("files_created", [])
        return len(files) > 0

    async def evaluate(self, subtask: Subtask) -> EvaluationResult:
        """Run security scanners (Bandit for Python)"""
        output = subtask.output or {}
        files = output.get("files_created", [])

        issues = []
        total_issues = 0
        high_severity_count = 0
        medium_severity_count = 0

        for file_path in files:
            if file_path.endswith(".py"):
                bandit_issues = await self._run_bandit(file_path)
                issues.extend(bandit_issues)

                for issue in bandit_issues:
                    total_issues += 1
                    if issue.severity == "high":
                        high_severity_count += 1
                    elif issue.severity == "medium":
                        medium_severity_count += 1

        # Scoring: Start at 10, deduct points for issues
        # High severity: -2 points each
        # Medium severity: -0.5 points each
        # Low severity: -0.2 points each
        score = 10.0
        score -= high_severity_count * 2.0
        score -= medium_severity_count * 0.5
        score -= (total_issues - high_severity_count - medium_severity_count) * 0.2
        score = max(0, score)  # Floor at 0

        suggestions = []
        if high_severity_count > 0:
            suggestions.append("Address high-severity security vulnerabilities immediately")
        if score < 7:
            suggestions.append("Review and fix security issues")
            suggestions.append("Follow OWASP security best practices")

        return EvaluationResult(
            score=score,
            issues=issues,
            suggestions=suggestions
        )

    async def _run_bandit(self, file_path: str) -> List[Issue]:
        """Run Bandit security scanner"""
        try:
            result = await asyncio.create_subprocess_exec(
                "bandit", "-f", "json", file_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await result.communicate()

            data = json.loads(stdout.decode())

            issues = []
            for result in data.get("results", []):
                issues.append(Issue(
                    severity=result["issue_severity"].lower(),
                    file=file_path,
                    line=result.get("line_number"),
                    message=f"[{result['test_id']}] {result['issue_text']}"
                ))

            return issues

        except Exception as e:
            logger.error(f"Bandit failed for {file_path}: {e}")
            return []
```

**4. Architecture Alignment Evaluator**

Uses LLM to check if code follows architecture guidelines:

```python
# backend/src/evaluators/architecture_evaluator.py

class ArchitectureAlignmentEvaluator(BaseEvaluator):
    dimension = EvaluationDimension.ARCHITECTURE_ALIGNMENT
    weight = 1.0

    def __init__(self, llm_client, architecture_doc: str):
        self.llm_client = llm_client
        self.architecture_doc = architecture_doc  # Load from docs/architecture.md

    def is_applicable(self, subtask: Subtask) -> bool:
        """Applicable for subtasks creating new components"""
        return subtask.complexity >= 3  # Only for medium-high complexity

    async def evaluate(self, subtask: Subtask) -> EvaluationResult:
        """Check architecture alignment using LLM"""

        output = subtask.output or {}
        files_content = output.get("files_content", {})

        prompt = f"""
You are reviewing code for architecture alignment.

**Architecture Guidelines:**
{self.architecture_doc[:3000]}  # Truncated for token limits

**Subtask:**
{subtask.description}

**Generated Code:**
{json.dumps(files_content, indent=2)[:2000]}

**Evaluation Task:**
Check if the code follows the architecture patterns and guidelines.

Rate on 0-10:
- 10: Perfect alignment with architecture
- 7-9: Good alignment, minor deviations
- 4-6: Some deviations
- 0-3: Major architectural violations

Return JSON:
{{
  "score": <float 0-10>,
  "violations": [<list of architecture violations>],
  "suggestions": [<list of improvements>]
}}
"""

        response = await self.llm_client.complete(prompt)
        result_data = json.loads(response)

        issues = [
            Issue(
                severity="warning",
                file=None,
                message=f"Architecture violation: {violation}"
            )
            for violation in result_data.get("violations", [])
        ]

        return EvaluationResult(
            score=result_data["score"],
            issues=issues,
            suggestions=result_data.get("suggestions", [])
        )
```

**5. Testability Evaluator**

Checks if code has tests and is testable:

```python
# backend/src/evaluators/testability_evaluator.py

class TestabilityEvaluator(BaseEvaluator):
    dimension = EvaluationDimension.TESTABILITY
    weight = 1.0

    def is_applicable(self, subtask: Subtask) -> bool:
        """Applicable if code files were created"""
        output = subtask.output or {}
        files = output.get("files_created", [])
        return any(
            not f.endswith("_test.py") and not f.endswith(".test.js")
            for f in files
        )

    async def evaluate(self, subtask: Subtask) -> EvaluationResult:
        """Evaluate testability"""
        output = subtask.output or {}
        files = output.get("files_created", [])

        # Check if test files exist
        code_files = [f for f in files if not self._is_test_file(f)]
        test_files = [f for f in files if self._is_test_file(f)]

        has_tests = len(test_files) > 0
        test_coverage_ratio = len(test_files) / len(code_files) if code_files else 0

        # Base score from test existence
        if not has_tests:
            score = 3.0  # Poor score if no tests
            issues = [Issue(
                severity="error",
                file=None,
                message="No test files created"
            )]
            suggestions = [
                "Add unit tests for the code",
                "Aim for >80% test coverage"
            ]
        elif test_coverage_ratio < 0.5:
            score = 6.0
            issues = [Issue(
                severity="warning",
                file=None,
                message="Low test coverage"
            )]
            suggestions = ["Increase test coverage"]
        else:
            score = 9.0
            issues = []
            suggestions = []

        return EvaluationResult(
            score=score,
            issues=issues,
            suggestions=suggestions
        )

    def _is_test_file(self, filename: str) -> bool:
        """Check if file is a test file"""
        return (
            filename.endswith("_test.py") or
            filename.endswith(".test.js") or
            filename.endswith(".test.ts") or
            "/tests/" in filename or
            "/test/" in filename
        )
```

#### 3.4.4 Integration with Task Workflow

**Background Job Trigger:**

```python
# backend/src/services/task_service.py

class TaskService:
    async def complete_subtask(self, subtask_id: UUID):
        """Called when subtask completes"""
        # Update subtask status
        await self.subtask_repo.update(subtask_id, status="completed")

        # Trigger evaluation asynchronously (non-blocking)
        scheduler.add_job(
            func=self.evaluation_service.evaluate_subtask,
            args=[subtask_id],
            trigger='date',
            run_date=datetime.now() + timedelta(seconds=5)  # 5s delay
        )

        # Continue with task coordination
        await self.check_dependencies_and_schedule_next(subtask_id)
```

**Evaluation-Triggered Checkpoint:**

```python
# backend/src/services/checkpoint_service.py

class CheckpointService:
    async def trigger_evaluation_checkpoint(
        self,
        task_id: UUID,
        subtask_id: UUID,
        evaluation: Evaluation
    ):
        """Create checkpoint due to low evaluation score"""

        checkpoint = await self.checkpoint_repo.create(
            task_id=task_id,
            trigger_reason="low_evaluation_score",
            evaluation_id=evaluation.evaluation_id,
            checkpoint_data={
                "failed_subtask_id": subtask_id,
                "evaluation_score": evaluation.overall_score,
                "issues": evaluation.details.get("issues", []),
                "suggestions": evaluation.details.get("suggestions", [])
            }
        )

        # Pause task execution
        await self.task_repo.update(task_id, status="checkpoint_pending")

        # Notify user via WebSocket
        await self.ws_manager.broadcast_event({
            "type": "checkpoint_ready",
            "data": {
                "checkpoint_id": checkpoint.checkpoint_id,
                "task_id": task_id,
                "reason": "Quality score below threshold",
                "evaluation_score": evaluation.overall_score
            }
        })
```

#### 3.4.5 Evaluator Registration (Startup)

```python
# backend/src/main.py

@app.on_event("startup")
async def startup_event():
    # Initialize evaluator registry
    evaluator_registry = EvaluatorRegistry()

    # Load architecture document
    with open("docs/architecture.md", "r") as f:
        architecture_doc = f.read()

    # Register evaluators
    llm_client = get_llm_client()

    evaluator_registry.register(CodeQualityEvaluator())
    evaluator_registry.register(CompletenessEvaluator(llm_client))
    evaluator_registry.register(SecurityEvaluator())
    evaluator_registry.register(ArchitectureAlignmentEvaluator(llm_client, architecture_doc))
    evaluator_registry.register(TestabilityEvaluator())

    # Store in app state
    app.state.evaluator_registry = evaluator_registry
```

### 3.5 Peer Review Service Architecture

**Purpose:** Implement agent collaboration through automatic peer review where Agent B reviews Agent A's work, ensuring quality through cross-validation before human checkpoints.

**Architecture Pattern:** **State Machine Pattern + Strategy Pattern**

#### 3.5.1 Peer Review Workflow

The peer review process occurs after subtask completion and evaluation:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Peer Review Workflow                         │
└─────────────────────────────────────────────────────────────────┘

Subtask Completed
      │
      ▼
Evaluation Runs (Section 3.4)
      │
      ▼
┌─────────────────────────┐
│ Check if Review Needed  │
│ (complexity >= 3 OR     │
│  evaluation_score < 8)  │
└──────┬─────────┬────────┘
       │         │
    No │         │ Yes
       │         ▼
       │   ┌────────────────────────┐
       │   │ Create Review Task     │
       │   │ (subtask_type=review)  │
       │   └──────┬─────────────────┘
       │          │
       │          ▼
       │   ┌────────────────────────┐
       │   │ Allocate to Different  │
       │   │ Worker (not original)  │
       │   └──────┬─────────────────┘
       │          │
       │          ▼
       │   ┌────────────────────────┐
       │   │ Reviewer Agent         │
       │   │ Analyzes Code          │
       │   └──────┬─────────────────┘
       │          │
       │          ▼
       │   ┌────────────────────────┐
       │   │ Parse Review Result    │
       │   │ (JSON with issues)     │
       │   └──────┬─────────────────┘
       │          │
       │   ┌──────▼────────┐
       │   │ Review Score? │
       │   └──┬─────┬──────┘
       │      │     │
       │  < 7 │     │ >= 7
       │      │     │
       │      │     ▼
       │      │   ┌─────────────────┐
       │      │   │ Minor Issues?   │
       │      │   └──┬──────────┬───┘
       │      │      │          │
       │      │   Yes│          │No
       │      │      │          │
       │      │      ▼          ▼
       │      │   ┌──────┐  ┌────────────┐
       │      │   │Auto- │  │ Accept     │
       │      │   │Fix?  │  │ (Approved) │
       │      │   └──┬───┘  └────────────┘
       │      │      │
       │      │   Yes│
       │      │      ▼
       │      │   ┌───────────────────┐
       │      │   │ Apply Auto-Fix    │
       │      │   │ Resubmit Original │
       │      │   └────────┬──────────┘
       │      │            │
       │      │   ┌────────▼──────────┐
       │      │   │ Review Again?     │
       │      │   │ (cycle_count < 3) │
       │      │   └────────┬──────────┘
       │      │            │
       │      └────────────┼─────────────┐
       │                   │             │
       │                < 3│          >=3│
       │                   │             │
       │                   ▼             ▼
       │           ┌──────────────┐  ┌──────────────────┐
       │           │ Review Again │  │ Escalate to      │
       │           │ (Iteration)  │  │ Human Checkpoint │
       │           └──────────────┘  └──────────────────┘
       │
       ▼
Continue to Next Subtask
```

#### 3.5.2 Review Task Data Model

**Extended Subtask Model:**

```python
# Add to subtasks table schema

class Subtask(Base):
    # ... existing fields ...

    # Peer review fields
    subtask_type: str = "task"  # "task" | "review" | "correction"
    review_target_id: UUID = None  # If type=review, points to original subtask
    review_cycle_count: int = 0  # Number of review iterations
    review_result: dict = None  # Parsed review result (issues, severity, suggestions)

# Separate reviews table for tracking

class Review(Base):
    __tablename__ = "reviews"

    review_id: UUID = Column(UUID, primary_key=True, default=uuid.uuid4)
    original_subtask_id: UUID = Column(UUID, ForeignKey("subtasks.subtask_id"))
    review_subtask_id: UUID = Column(UUID, ForeignKey("subtasks.subtask_id"))
    reviewer_worker_id: UUID = Column(UUID, ForeignKey("workers.worker_id"))
    original_worker_id: UUID = Column(UUID, ForeignKey("workers.worker_id"))

    # Review result
    review_score: float = Column(Float)  # 0-10
    issues_found: List[dict] = Column(JSONB, default=[])
    severity_distribution: dict = Column(JSONB)  # {critical: 0, high: 2, medium: 5, low: 3}
    auto_fix_applied: bool = Column(Boolean, default=False)
    auto_fix_diff: str = Column(Text, nullable=True)

    # Decision
    decision: str = Column(String(20))  # "approved" | "needs_revision" | "escalate"
    decision_reason: str = Column(Text)

    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

#### 3.5.3 Peer Review Service Implementation

```python
# backend/src/services/peer_review_service.py

from enum import Enum
from typing import Optional, List

class ReviewDecision(str, Enum):
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    ESCALATE_TO_HUMAN = "escalate"

class IssueSeverity(str, Enum):
    CRITICAL = "critical"  # Blocking issues (security, data loss)
    HIGH = "high"          # Major issues (bugs, incorrect logic)
    MEDIUM = "medium"      # Quality issues (code smells, performance)
    LOW = "low"            # Minor issues (formatting, naming)

class PeerReviewService:
    """Manages peer review workflow"""

    MAX_REVIEW_CYCLES = 3  # Maximum auto-fix iterations
    AUTO_FIX_SCORE_THRESHOLD = 6.0  # Only auto-fix if score >= 6

    def __init__(
        self,
        subtask_repo: SubtaskRepository,
        review_repo: ReviewRepository,
        worker_repo: WorkerRepository,
        task_service: TaskService,
        checkpoint_service: CheckpointService,
        llm_client
    ):
        self.subtask_repo = subtask_repo
        self.review_repo = review_repo
        self.worker_repo = worker_repo
        self.task_service = task_service
        self.checkpoint_service = checkpoint_service
        self.llm_client = llm_client

    async def trigger_peer_review(self, original_subtask_id: UUID):
        """
        Trigger peer review for a completed subtask

        Called after subtask completion and evaluation.
        """
        original_subtask = await self.subtask_repo.get_by_id(original_subtask_id)

        # Check if review is needed
        if not self._should_trigger_review(original_subtask):
            logger.info(f"Peer review not needed for subtask {original_subtask_id}")
            return

        # Prevent infinite review loops
        if original_subtask.review_cycle_count >= self.MAX_REVIEW_CYCLES:
            logger.warning(
                f"Max review cycles ({self.MAX_REVIEW_CYCLES}) reached for "
                f"subtask {original_subtask_id}, escalating to human"
            )
            await self.checkpoint_service.trigger_review_escalation(
                original_subtask.task_id,
                original_subtask_id,
                reason="max_review_cycles_exceeded"
            )
            return

        # Create review task
        review_subtask = await self._create_review_task(original_subtask)

        # Allocate to different worker
        reviewer_worker = await self._allocate_reviewer(
            original_subtask,
            exclude_worker_id=original_subtask.assigned_worker
        )

        if not reviewer_worker:
            logger.error("No available reviewer worker, skipping peer review")
            return

        # Assign review task
        await self.subtask_repo.update(
            review_subtask.subtask_id,
            assigned_worker=reviewer_worker.worker_id,
            assigned_tool=reviewer_worker.tools[0],  # Use first available tool
            status="assigned"
        )

        # Notify reviewer worker via WebSocket
        await self._notify_worker(reviewer_worker.worker_id, review_subtask)

    def _should_trigger_review(self, subtask: Subtask) -> bool:
        """Determine if peer review is needed"""
        # Skip review for review tasks themselves
        if subtask.subtask_type == "review":
            return False

        # Always review high-complexity tasks
        if subtask.complexity >= 4:
            return True

        # Review if evaluation score is good but not perfect
        if subtask.evaluation_score and 7.0 <= subtask.evaluation_score < 9.0:
            return True

        # Review if medium complexity
        if subtask.complexity == 3:
            return True

        return False

    async def _create_review_task(self, original_subtask: Subtask) -> Subtask:
        """Create a peer review subtask"""

        review_prompt = self._generate_review_prompt(original_subtask)

        review_subtask = await self.subtask_repo.create(
            task_id=original_subtask.task_id,
            name=f"Review: {original_subtask.name}",
            description=review_prompt,
            subtask_type="review",
            review_target_id=original_subtask.subtask_id,
            complexity=2,  # Reviews are medium complexity
            dependencies=[],  # No dependencies
            status="pending"
        )

        return review_subtask

    def _generate_review_prompt(self, original_subtask: Subtask) -> str:
        """Generate review prompt for the reviewing agent"""

        output = original_subtask.output or {}
        files_content = output.get("files_content", {})
        files_created = output.get("files_created", [])

        prompt = f"""
# Code Review Task

You are performing a peer review of code generated by another agent.

## Original Task
**Description:** {original_subtask.description}
**Complexity:** {original_subtask.complexity}/5
**Evaluation Score:** {original_subtask.evaluation_score or "N/A"}

## Files to Review
{chr(10).join(f"- {file}" for file in files_created)}

## Code Content
```
{json.dumps(files_content, indent=2)[:4000]}
```

## Review Instructions

Analyze the code for the following:

1. **Correctness**: Does the code fulfill the task requirements?
2. **Code Quality**: Is the code clean, readable, and maintainable?
3. **Best Practices**: Does it follow language-specific best practices?
4. **Edge Cases**: Are edge cases handled properly?
5. **Performance**: Are there obvious performance issues?
6. **Security**: Are there security vulnerabilities?

## Output Format

Return a JSON object with this exact structure:

{{
  "review_score": <float 0-10>,
  "issues": [
    {{
      "severity": "critical" | "high" | "medium" | "low",
      "file": "<filename>",
      "line": <line number or null>,
      "description": "<issue description>",
      "suggestion": "<how to fix>"
    }}
  ],
  "summary": "<1-2 sentence overall assessment>",
  "decision": "approved" | "needs_revision",
  "auto_fix_possible": <boolean>,
  "auto_fix_instructions": "<instructions for auto-fix if possible>"
}}

**Decision Guidelines:**
- "approved": No critical/high issues, code is acceptable
- "needs_revision": Has critical/high issues that need fixing

**Review Score Guidelines:**
- 9-10: Excellent, no significant issues
- 7-8: Good, minor issues only
- 5-6: Acceptable with revisions
- 0-4: Needs major revisions
"""

        return prompt

    async def _allocate_reviewer(
        self,
        original_subtask: Subtask,
        exclude_worker_id: UUID
    ) -> Optional[Worker]:
        """Allocate a different worker for review"""

        # Get all online workers except the original one
        available_workers = await self.worker_repo.get_online_workers()
        available_workers = [
            w for w in available_workers
            if w.worker_id != exclude_worker_id
        ]

        if not available_workers:
            return None

        # Prefer workers with same tool as original (for consistency)
        original_tool = original_subtask.assigned_tool
        same_tool_workers = [
            w for w in available_workers
            if original_tool in w.tools
        ]

        if same_tool_workers:
            # Choose worker with lowest current load
            return min(same_tool_workers, key=lambda w: w.current_load or 0)
        else:
            # Fallback: any available worker
            return min(available_workers, key=lambda w: w.current_load or 0)

    async def process_review_result(self, review_subtask_id: UUID):
        """Process completed peer review and take action"""

        review_subtask = await self.subtask_repo.get_by_id(review_subtask_id)
        original_subtask = await self.subtask_repo.get_by_id(
            review_subtask.review_target_id
        )

        # Parse review result from subtask output
        review_output = review_subtask.output or {}
        review_result = review_output.get("review_result")

        if not review_result:
            logger.error(f"Review subtask {review_subtask_id} has no result")
            return

        # Store review result
        review_score = review_result.get("review_score", 0)
        issues = review_result.get("issues", [])
        decision = review_result.get("decision", "needs_revision")
        auto_fix_possible = review_result.get("auto_fix_possible", False)

        # Calculate severity distribution
        severity_dist = {
            "critical": len([i for i in issues if i["severity"] == "critical"]),
            "high": len([i for i in issues if i["severity"] == "high"]),
            "medium": len([i for i in issues if i["severity"] == "medium"]),
            "low": len([i for i in issues if i["severity"] == "low"]),
        }

        # Create review record
        review_record = await self.review_repo.create(
            original_subtask_id=original_subtask.subtask_id,
            review_subtask_id=review_subtask_id,
            reviewer_worker_id=review_subtask.assigned_worker,
            original_worker_id=original_subtask.assigned_worker,
            review_score=review_score,
            issues_found=issues,
            severity_distribution=severity_dist,
            decision=decision
        )

        # Decision logic
        has_critical = severity_dist["critical"] > 0
        has_high = severity_dist["high"] > 0

        if decision == "approved" and review_score >= 8.0:
            # Accept the code
            logger.info(f"Review approved for subtask {original_subtask.subtask_id}")
            await self.subtask_repo.update(
                original_subtask.subtask_id,
                review_result=review_result,
                review_cycle_count=original_subtask.review_cycle_count + 1
            )
            # Continue task execution
            await self.task_service.check_dependencies_and_schedule_next(
                original_subtask.subtask_id
            )

        elif (
            auto_fix_possible and
            not has_critical and
            review_score >= self.AUTO_FIX_SCORE_THRESHOLD and
            original_subtask.review_cycle_count < self.MAX_REVIEW_CYCLES - 1
        ):
            # Apply auto-fix
            logger.info(f"Applying auto-fix for subtask {original_subtask.subtask_id}")
            await self._apply_auto_fix(
                original_subtask,
                review_result.get("auto_fix_instructions")
            )

        else:
            # Escalate to human checkpoint
            logger.warning(
                f"Review found issues for subtask {original_subtask.subtask_id}, "
                f"escalating to human"
            )
            await self.checkpoint_service.trigger_peer_review_checkpoint(
                original_subtask.task_id,
                original_subtask.subtask_id,
                review_record
            )

    async def _apply_auto_fix(
        self,
        original_subtask: Subtask,
        fix_instructions: str
    ):
        """Apply automatic fixes and resubmit for review"""

        # Create correction subtask (same worker, with fix instructions)
        correction_subtask = await self.subtask_repo.create(
            task_id=original_subtask.task_id,
            name=f"Fix: {original_subtask.name}",
            description=f"""
# Correction Task

Apply the following fixes to your previous work:

**Original Task:** {original_subtask.description}

**Issues Found by Peer Review:**
{fix_instructions}

**Instructions:**
1. Review the issues identified
2. Apply the suggested fixes
3. Return the corrected code with the same file structure

**Previous Output:**
{json.dumps(original_subtask.output, indent=2)}
""",
            subtask_type="correction",
            review_target_id=original_subtask.subtask_id,
            complexity=original_subtask.complexity,
            dependencies=[],
            status="pending"
        )

        # Allocate to SAME worker (let them fix their own work)
        await self.subtask_repo.update(
            correction_subtask.subtask_id,
            assigned_worker=original_subtask.assigned_worker,
            assigned_tool=original_subtask.assigned_tool,
            status="assigned"
        )

        # Increment review cycle count
        await self.subtask_repo.update(
            original_subtask.subtask_id,
            review_cycle_count=original_subtask.review_cycle_count + 1
        )

        # When correction completes, it will trigger another peer review
        # (handled by task_service.complete_subtask → trigger_peer_review)
```

#### 3.5.4 Integration with Task Service

```python
# backend/src/services/task_service.py

class TaskService:
    async def complete_subtask(self, subtask_id: UUID):
        """Called when subtask completes"""
        subtask = await self.subtask_repo.get_by_id(subtask_id)

        # Update subtask status
        await self.subtask_repo.update(subtask_id, status="completed")

        # 1. Trigger evaluation asynchronously (non-blocking)
        scheduler.add_job(
            func=self.evaluation_service.evaluate_subtask,
            args=[subtask_id],
            trigger='date',
            run_date=datetime.now() + timedelta(seconds=5)
        )

        # 2. Trigger peer review if needed (for task/correction subtasks)
        if subtask.subtask_type in ["task", "correction"]:
            scheduler.add_job(
                func=self.peer_review_service.trigger_peer_review,
                args=[subtask_id],
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=10)  # After evaluation
            )

        # 3. If this is a review subtask, process the review result
        if subtask.subtask_type == "review":
            scheduler.add_job(
                func=self.peer_review_service.process_review_result,
                args=[subtask_id],
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=5)
            )

        # 4. Continue with task coordination (if not waiting for review)
        if subtask.subtask_type not in ["task", "correction"]:
            await self.check_dependencies_and_schedule_next(subtask_id)
```

#### 3.5.5 Checkpoint Integration

```python
# backend/src/services/checkpoint_service.py

class CheckpointService:
    async def trigger_peer_review_checkpoint(
        self,
        task_id: UUID,
        subtask_id: UUID,
        review: Review
    ):
        """Create checkpoint due to peer review finding issues"""

        checkpoint = await self.checkpoint_repo.create(
            task_id=task_id,
            trigger_reason="peer_review_issues",
            review_id=review.review_id,
            checkpoint_data={
                "subtask_id": subtask_id,
                "review_score": review.review_score,
                "issues_found": review.issues_found,
                "severity_distribution": review.severity_distribution,
                "reviewer_summary": review.decision_reason
            }
        )

        # Pause task execution
        await self.task_repo.update(task_id, status="checkpoint_pending")

        # Notify user via WebSocket
        await self.ws_manager.broadcast_event({
            "type": "checkpoint_ready",
            "data": {
                "checkpoint_id": checkpoint.checkpoint_id,
                "task_id": task_id,
                "reason": "Peer review found issues",
                "review_score": review.review_score,
                "critical_issues": review.severity_distribution["critical"],
                "high_issues": review.severity_distribution["high"]
            }
        })

    async def trigger_review_escalation(
        self,
        task_id: UUID,
        subtask_id: UUID,
        reason: str
    ):
        """Escalate to human after max review cycles"""

        checkpoint = await self.checkpoint_repo.create(
            task_id=task_id,
            trigger_reason="review_escalation",
            checkpoint_data={
                "subtask_id": subtask_id,
                "escalation_reason": reason,
                "message": f"Subtask requires human review after {self.peer_review_service.MAX_REVIEW_CYCLES} review cycles"
            }
        )

        await self.task_repo.update(task_id, status="checkpoint_pending")

        await self.ws_manager.broadcast_event({
            "type": "checkpoint_ready",
            "data": {
                "checkpoint_id": checkpoint.checkpoint_id,
                "task_id": task_id,
                "reason": "Review escalation - human decision needed"
            }
        })
```

#### 3.5.6 Review Result Schema

**Expected JSON structure from reviewing agent:**

```json
{
  "review_score": 7.5,
  "issues": [
    {
      "severity": "high",
      "file": "src/auth/login.py",
      "line": 45,
      "description": "Password is stored in plaintext in logs",
      "suggestion": "Remove password from log statements, use sanitized logs"
    },
    {
      "severity": "medium",
      "file": "src/auth/login.py",
      "line": 12,
      "description": "Function too long (50 lines), violates SRP",
      "suggestion": "Extract token generation logic into separate function"
    },
    {
      "severity": "low",
      "file": "src/auth/login.py",
      "line": 8,
      "description": "Missing type hints for function parameters",
      "suggestion": "Add type hints: def login(username: str, password: str) -> TokenResponse:"
    }
  ],
  "summary": "Code is functional but has security and maintainability issues. Needs revision before approval.",
  "decision": "needs_revision",
  "auto_fix_possible": true,
  "auto_fix_instructions": "1. Remove password from log statement on line 45\n2. Extract token generation into _generate_token() helper\n3. Add type hints to all functions"
}
```

### 3.6 File Storage Service Architecture

**Purpose:** Manage generated code files from AI agents, providing storage, retrieval, and tracking for deliverables.

**Architecture Pattern:** **Local Filesystem + Path Tracking**

#### 3.6.1 File Storage Structure

```
/data/tasks/
├── {task_id}/
│   ├── metadata.json          # Task metadata
│   └── subtasks/
│       ├── {subtask_id}/
│       │   ├── files/
│       │   │   ├── src/
│       │   │   │   └── auth.py
│       │   │   ├── tests/
│       │   │   │   └── test_auth.py
│       │   │   └── README.md
│       │   └── metadata.json  # Subtask file manifest
│       └── {subtask_id}/
│           └── files/
```

#### 3.6.2 FileStorageService Implementation

```python
# backend/src/services/file_storage_service.py

import os
import shutil
from pathlib import Path
from typing import List, Optional
import aiofiles

class FileStorageService:
    """Manages file storage for agent-generated code"""

    BASE_PATH = Path("/data/tasks")  # Configurable via env

    async def store_subtask_files(
        self,
        task_id: UUID,
        subtask_id: UUID,
        files: Dict[str, str]  # {relative_path: content}
    ) -> List[str]:
        """
        Store files generated by subtask

        Args:
            task_id: Task UUID
            subtask_id: Subtask UUID
            files: Dict mapping relative file paths to content

        Returns:
            List of absolute file paths stored
        """
        subtask_dir = self.BASE_PATH / str(task_id) / "subtasks" / str(subtask_id) / "files"
        subtask_dir.mkdir(parents=True, exist_ok=True)

        stored_paths = []

        for relative_path, content in files.items():
            # Sanitize path to prevent directory traversal
            safe_path = self._sanitize_path(relative_path)
            file_path = subtask_dir / safe_path

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file asynchronously
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)

            stored_paths.append(str(file_path))
            logger.info(f"Stored file: {file_path}")

        # Update subtask metadata
        await self._update_file_manifest(task_id, subtask_id, stored_paths)

        return stored_paths

    async def get_subtask_files(
        self,
        task_id: UUID,
        subtask_id: UUID
    ) -> Dict[str, str]:
        """Retrieve all files for a subtask"""
        subtask_dir = self.BASE_PATH / str(task_id) / "subtasks" / str(subtask_id) / "files"

        if not subtask_dir.exists():
            return {}

        files = {}
        for file_path in subtask_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(subtask_dir)
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                files[str(relative_path)] = content

        return files

    async def get_file_content(
        self,
        task_id: UUID,
        subtask_id: UUID,
        filename: str
    ) -> Optional[str]:
        """Get content of a specific file"""
        safe_filename = self._sanitize_path(filename)
        file_path = (
            self.BASE_PATH / str(task_id) / "subtasks" /
            str(subtask_id) / "files" / safe_filename
        )

        if not file_path.exists():
            return None

        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()

    async def create_task_archive(
        self,
        task_id: UUID
    ) -> Path:
        """Create a ZIP archive of all task files"""
        task_dir = self.BASE_PATH / str(task_id)
        archive_path = self.BASE_PATH / f"{task_id}.zip"

        # Create ZIP archive
        shutil.make_archive(
            str(archive_path.with_suffix('')),
            'zip',
            task_dir
        )

        return archive_path

    async def cleanup_task_files(
        self,
        task_id: UUID,
        older_than_days: int = 30
    ):
        """Delete task files older than specified days"""
        task_dir = self.BASE_PATH / str(task_id)

        if not task_dir.exists():
            return

        # Check task metadata for creation date
        metadata_file = task_dir / "metadata.json"
        if metadata_file.exists():
            async with aiofiles.open(metadata_file, 'r') as f:
                metadata = json.loads(await f.read())

            created_at = datetime.fromisoformat(metadata["created_at"])
            age_days = (datetime.now() - created_at).days

            if age_days > older_than_days:
                shutil.rmtree(task_dir)
                logger.info(f"Cleaned up task files for {task_id} ({age_days} days old)")

    def _sanitize_path(self, path: str) -> str:
        """Sanitize file path to prevent directory traversal"""
        # Remove leading slashes and parent directory references
        safe_path = path.lstrip('/')
        safe_path = safe_path.replace('..', '')
        return safe_path

    async def _update_file_manifest(
        self,
        task_id: UUID,
        subtask_id: UUID,
        file_paths: List[str]
    ):
        """Update file manifest for subtask"""
        manifest_path = (
            self.BASE_PATH / str(task_id) / "subtasks" /
            str(subtask_id) / "metadata.json"
        )

        manifest = {
            "subtask_id": str(subtask_id),
            "files": file_paths,
            "created_at": datetime.now().isoformat(),
            "file_count": len(file_paths)
        }

        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(json.dumps(manifest, indent=2))
```

#### 3.6.3 API Integration

**Add to REST API:**

```python
# GET /api/v1/subtasks/{subtask_id}/files
@app.get("/api/v1/subtasks/{subtask_id}/files")
async def list_subtask_files(subtask_id: UUID):
    """List all files for a subtask"""
    subtask = await subtask_repo.get_by_id(subtask_id)
    files = await file_storage_service.get_subtask_files(
        subtask.task_id,
        subtask_id
    )

    return {
        "subtask_id": subtask_id,
        "file_count": len(files),
        "files": list(files.keys())
    }

# GET /api/v1/subtasks/{subtask_id}/files/{filename:path}
@app.get("/api/v1/subtasks/{subtask_id}/files/{filename:path}")
async def get_file_content(subtask_id: UUID, filename: str):
    """Get content of a specific file"""
    subtask = await subtask_repo.get_by_id(subtask_id)
    content = await file_storage_service.get_file_content(
        subtask.task_id,
        subtask_id,
        filename
    )

    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    return Response(content=content, media_type="text/plain")

# GET /api/v1/tasks/{task_id}/download
@app.get("/api/v1/tasks/{task_id}/download")
async def download_task_archive(task_id: UUID):
    """Download ZIP archive of all task files"""
    archive_path = await file_storage_service.create_task_archive(task_id)

    return FileResponse(
        path=archive_path,
        filename=f"task-{task_id}.zip",
        media_type="application/zip"
    )
```

### 3.7 Checkpoint Trigger Service & Concurrency Control

**Purpose:** Define precise checkpoint trigger logic and ensure distributed state consistency.

#### 3.7.1 Checkpoint Trigger Algorithm

```python
# backend/src/services/checkpoint_service.py

class CheckpointService:
    """Enhanced with precise trigger logic"""

    async def check_and_trigger_checkpoint(
        self,
        task_id: UUID,
        completed_subtask_id: UUID
    ):
        """
        Check if checkpoint should be triggered based on multiple factors

        Trigger conditions:
        1. Checkpoint frequency (low/medium/high)
        2. Evaluation score < 7.0
        3. Peer review failure
        4. Max review cycles exceeded
        """
        task = await self.task_repo.get_by_id(task_id)
        completed_subtasks = await self.subtask_repo.get_completed_by_task(task_id)
        all_subtasks = await self.subtask_repo.get_by_task(task_id)

        # Don't trigger if task is already at checkpoint
        if task.status == "checkpoint_pending":
            return

        # Trigger based on checkpoint frequency
        frequency_trigger = self._check_frequency_trigger(
            task.checkpoint_frequency,
            len(completed_subtasks),
            len(all_subtasks)
        )

        # Trigger based on evaluation score
        last_subtask = await self.subtask_repo.get_by_id(completed_subtask_id)
        score_trigger = (
            last_subtask.evaluation_score and
            last_subtask.evaluation_score < 7.0
        )

        if frequency_trigger or score_trigger:
            await self._create_checkpoint(
                task_id,
                completed_subtasks,
                trigger_reason="frequency" if frequency_trigger else "low_score"
            )

    def _check_frequency_trigger(
        self,
        frequency: str,
        completed_count: int,
        total_count: int
    ) -> bool:
        """
        Determine if checkpoint should trigger based on frequency setting

        Frequency rules:
        - low: Only before final subtask (when completed = total - 1)
        - medium: Every 3 subtasks OR when 50% complete OR before final
        - high: After every subtask
        """
        if frequency == "low":
            # Trigger only when one subtask left
            return completed_count == total_count - 1

        elif frequency == "medium":
            # Trigger every 3 subtasks
            if completed_count % 3 == 0:
                return True
            # OR when 50% complete
            if completed_count >= total_count * 0.5 and completed_count < total_count * 0.6:
                return True
            # OR before final
            if completed_count == total_count - 1:
                return True
            return False

        elif frequency == "high":
            # Trigger after every subtask
            return True

        return False

    async def _create_checkpoint(
        self,
        task_id: UUID,
        completed_subtasks: List[Subtask],
        trigger_reason: str
    ):
        """Create checkpoint with completed subtasks context"""

        # Gather evaluation data
        evaluations = []
        for subtask in completed_subtasks[-5:]:  # Last 5 subtasks
            if subtask.evaluation_score:
                evaluations.append({
                    "subtask_id": str(subtask.subtask_id),
                    "name": subtask.name,
                    "score": subtask.evaluation_score
                })

        # Get next subtasks (dependencies resolved)
        next_subtasks = await self._get_next_subtasks(task_id)

        checkpoint = await self.checkpoint_repo.create(
            task_id=task_id,
            trigger_reason=trigger_reason,
            checkpoint_data={
                "completed_subtasks": [str(s.subtask_id) for s in completed_subtasks],
                "completed_count": len(completed_subtasks),
                "evaluations": evaluations,
                "next_subtasks": [
                    {"id": str(s.subtask_id), "name": s.name}
                    for s in next_subtasks
                ],
                "average_score": sum(s.evaluation_score for s in completed_subtasks if s.evaluation_score) / len(completed_subtasks) if completed_subtasks else 0
            }
        )

        # Pause task
        await self.task_repo.update(task_id, status="checkpoint_pending")

        # Notify user
        await self.ws_manager.broadcast_event({
            "type": "checkpoint_ready",
            "data": {
                "checkpoint_id": checkpoint.checkpoint_id,
                "task_id": task_id,
                "reason": trigger_reason,
                "completed_count": len(completed_subtasks),
                "average_score": checkpoint.checkpoint_data["average_score"]
            }
        })
```

#### 3.7.2 Distributed State Consistency

**Problem:** Concurrent subtask completion could cause race conditions in task state updates.

**Solution:** Optimistic locking + Transaction isolation

**Database Schema Update:**

```sql
-- Add version column for optimistic locking
ALTER TABLE tasks ADD COLUMN version INTEGER NOT NULL DEFAULT 0;

-- Create index for fast locking
CREATE INDEX idx_tasks_status_version ON tasks(task_id, status, version);
```

**Concurrency Control Implementation:**

```python
# backend/src/repositories/task_repository.py

class TaskRepository:
    """Enhanced with concurrency control"""

    async def update_with_lock(
        self,
        task_id: UUID,
        expected_version: int,
        **updates
    ) -> bool:
        """
        Update task with optimistic locking

        Returns True if update successful, False if version mismatch
        """
        async with self.session.begin():
            # SELECT FOR UPDATE to prevent concurrent modifications
            query = (
                select(Task)
                .where(Task.task_id == task_id, Task.version == expected_version)
                .with_for_update()  # Row-level lock
            )
            result = await self.session.execute(query)
            task = result.scalar_one_or_none()

            if not task:
                # Version mismatch or task not found
                return False

            # Apply updates
            for key, value in updates.items():
                setattr(task, key, value)

            # Increment version
            task.version += 1
            task.updated_at = datetime.now()

            await self.session.commit()
            return True

    async def increment_progress_atomic(
        self,
        task_id: UUID
    ) -> int:
        """Atomically increment task progress"""
        async with self.session.begin():
            # Use SELECT FOR UPDATE to lock row
            query = (
                select(Task)
                .where(Task.task_id == task_id)
                .with_for_update()
            )
            result = await self.session.execute(query)
            task = result.scalar_one()

            # Calculate new progress
            completed = await self._count_completed_subtasks(task_id)
            total = await self._count_total_subtasks(task_id)
            new_progress = int((completed / total) * 100) if total > 0 else 0

            task.progress = new_progress
            task.updated_at = datetime.now()

            await self.session.commit()
            return new_progress

# backend/src/services/task_service.py

class TaskService:
    """Enhanced with retry on version conflict"""

    async def check_dependencies_and_schedule_next(
        self,
        completed_subtask_id: UUID,
        max_retries: int = 3
    ):
        """
        Check dependencies and schedule next subtasks
        Includes retry logic for version conflicts
        """
        subtask = await self.subtask_repo.get_by_id(completed_subtask_id)
        task = await self.task_repo.get_by_id(subtask.task_id)

        # Find subtasks that depend on this one
        dependent_subtasks = await self.subtask_repo.get_by_dependency(
            completed_subtask_id
        )

        for dep_subtask in dependent_subtasks:
            # Check if all dependencies are complete
            all_deps_complete = await self._all_dependencies_complete(dep_subtask)

            if all_deps_complete:
                # Schedule subtask with retry on conflict
                for attempt in range(max_retries):
                    try:
                        await self._schedule_subtask(dep_subtask.subtask_id)
                        break
                    except VersionConflictError:
                        if attempt == max_retries - 1:
                            raise
                        await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

        # Update task progress atomically
        new_progress = await self.task_repo.increment_progress_atomic(task.task_id)

        # Broadcast progress update
        await self.ws_manager.broadcast_event({
            "type": "task_update",
            "data": {
                "task_id": task.task_id,
                "progress": new_progress
            }
        })

    async def _all_dependencies_complete(self, subtask: Subtask) -> bool:
        """Check if all dependencies are complete (with row locking)"""
        if not subtask.dependencies:
            return True

        async with self.subtask_repo.session.begin():
            # Lock dependency rows to prevent race conditions
            query = (
                select(Subtask.subtask_id, Subtask.status)
                .where(Subtask.subtask_id.in_(subtask.dependencies))
                .with_for_update()
            )
            result = await self.subtask_repo.session.execute(query)
            dependencies = result.all()

            return all(dep.status == "completed" for dep in dependencies)
```

**Transaction Isolation Level:**

```python
# backend/src/database.py

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    DATABASE_URL,
    isolation_level="READ COMMITTED"  # Prevent dirty reads, allow concurrent updates
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

### 3.8 Task Decomposition Fallback Strategy

**Purpose:** Ensure system reliability when LLM-based decomposition fails.

```python
# backend/src/services/task_service.py

class TaskService:
    """Enhanced with fallback decomposition"""

    LLM_TIMEOUT = 10  # seconds

    async def decompose_task(
        self,
        task_description: str,
        task_requirements: dict
    ) -> List[Subtask]:
        """
        Decompose task with LLM + fallback to rule-based

        Priority:
        1. LLM-based decomposition (primary)
        2. Rule-based templates (fallback)
        3. Simple split by requirements (last resort)
        """
        try:
            # Try LLM decomposition with timeout
            subtasks = await asyncio.wait_for(
                self._llm_decompose(task_description, task_requirements),
                timeout=self.LLM_TIMEOUT
            )

            # Validate LLM output
            if self._validate_subtasks(subtasks):
                logger.info(f"LLM decomposition successful ({len(subtasks)} subtasks)")
                return subtasks
            else:
                logger.warning("LLM decomposition invalid, using fallback")

        except (asyncio.TimeoutError, LLMError) as e:
            logger.error(f"LLM decomposition failed: {e}, using fallback")

        # Fallback to rule-based decomposition
        subtasks = await self._rule_based_decompose(
            task_description,
            task_requirements
        )

        if subtasks:
            logger.info(f"Rule-based decomposition successful ({len(subtasks)} subtasks)")
            return subtasks

        # Last resort: simple requirements-based split
        subtasks = self._simple_decompose(task_description, task_requirements)
        logger.warning(f"Using simple decomposition ({len(subtasks)} subtasks)")
        return subtasks

    async def _rule_based_decompose(
        self,
        description: str,
        requirements: dict
    ) -> List[Subtask]:
        """Rule-based decomposition using templates"""

        # Pattern matching for common task types
        if "auth" in description.lower() or "authentication" in description.lower():
            return self._template_auth_system()
        elif "crud" in description.lower() or "api endpoints" in description.lower():
            return self._template_crud_api(requirements)
        elif "refactor" in description.lower():
            return self._template_refactor(requirements)
        elif "dashboard" in description.lower() or "ui" in description.lower():
            return self._template_dashboard_ui()
        else:
            return []

    def _template_auth_system(self) -> List[Subtask]:
        """Template for authentication system"""
        return [
            {
                "name": "Create User model and database schema",
                "description": "Define User model with fields (id, username, email, password_hash). Create migration.",
                "complexity": 2,
                "dependencies": []
            },
            {
                "name": "Implement password hashing utility",
                "description": "Create utility functions for hashing and verifying passwords using bcrypt.",
                "complexity": 2,
                "dependencies": []
            },
            {
                "name": "Create user registration endpoint",
                "description": "POST /auth/register endpoint with validation and password hashing.",
                "complexity": 3,
                "dependencies": [0, 1]
            },
            {
                "name": "Create login endpoint with JWT",
                "description": "POST /auth/login endpoint that returns JWT token on successful authentication.",
                "complexity": 3,
                "dependencies": [0, 1]
            },
            {
                "name": "Create authentication middleware",
                "description": "Middleware to verify JWT tokens and protect routes.",
                "complexity": 3,
                "dependencies": [3]
            },
            {
                "name": "Write tests for auth system",
                "description": "Unit and integration tests for registration, login, and protected routes.",
                "complexity": 3,
                "dependencies": [2, 3, 4]
            }
        ]

    def _template_crud_api(self, requirements: dict) -> List[Subtask]:
        """Template for CRUD API"""
        resource_name = requirements.get("resource_name", "Resource")

        return [
            {
                "name": f"Create {resource_name} model and schema",
                "description": f"Define {resource_name} SQLAlchemy model and Pydantic schemas.",
                "complexity": 2,
                "dependencies": []
            },
            {
                "name": f"Implement GET /{resource_name.lower()}s endpoint",
                "description": f"List all {resource_name}s with pagination and filtering.",
                "complexity": 2,
                "dependencies": [0]
            },
            {
                "name": f"Implement POST /{resource_name.lower()}s endpoint",
                "description": f"Create new {resource_name} with validation.",
                "complexity": 3,
                "dependencies": [0]
            },
            {
                "name": f"Implement GET /{resource_name.lower()}s/{{id}} endpoint",
                "description": f"Get single {resource_name} by ID with 404 handling.",
                "complexity": 2,
                "dependencies": [0]
            },
            {
                "name": f"Implement PUT /{resource_name.lower()}s/{{id}} endpoint",
                "description": f"Update existing {resource_name}.",
                "complexity": 3,
                "dependencies": [0]
            },
            {
                "name": f"Implement DELETE /{resource_name.lower()}s/{{id}} endpoint",
                "description": f"Delete {resource_name} with cascade if needed.",
                "complexity": 2,
                "dependencies": [0]
            },
            {
                "name": f"Write tests for {resource_name} CRUD",
                "description": f"Test all CRUD operations with edge cases.",
                "complexity": 3,
                "dependencies": [1, 2, 3, 4, 5]
            }
        ]

    def _validate_subtasks(self, subtasks: List[dict]) -> bool:
        """Validate LLM-generated subtasks"""
        if not subtasks or len(subtasks) == 0:
            return False

        # Check required fields
        for st in subtasks:
            if not all(k in st for k in ["name", "description", "dependencies"]):
                return False

        # Check for cycles in dependency graph
        if self._has_cycles(subtasks):
            logger.error("Subtask dependencies contain cycles")
            return False

        return True

    def _has_cycles(self, subtasks: List[dict]) -> bool:
        """Detect cycles in dependency graph using DFS"""
        n = len(subtasks)
        visited = [False] * n
        rec_stack = [False] * n

        def dfs(node: int) -> bool:
            visited[node] = True
            rec_stack[node] = True

            for dep in subtasks[node].get("dependencies", []):
                if dep >= n:  # Invalid dependency index
                    return True
                if not visited[dep]:
                    if dfs(dep):
                        return True
                elif rec_stack[dep]:
                    return True  # Cycle detected

            rec_stack[node] = False
            return False

        for i in range(n):
            if not visited[i]:
                if dfs(i):
                    return True

        return False
```

---

## 4. API Design

### 4.1 REST API Endpoints

**Base URL:** `http://localhost:8000/api/v1` (development)

**Authentication:** Bearer Token (JWT)

#### 4.1.1 Task Management

**Submit New Task**

```http
POST /api/v1/tasks
Authorization: Bearer {jwt_token}
Content-Type: application/json

Request Body:
{
  "description": "Build user authentication system with email/password and JWT tokens",
  "checkpoint_frequency": "medium",  // low | medium | high
  "privacy_level": "normal",         // normal | sensitive
  "tool_preferences": ["claude_code", "gemini_cli", "ollama"]  // optional
}

Response (201 Created):
{
  "task_id": "uuid",
  "status": "initializing",
  "message": "Task submitted successfully. Decomposing into subtasks..."
}
```

**Get Task Details**

```http
GET /api/v1/tasks/{task_id}
Authorization: Bearer {jwt_token}

Response (200 OK):
{
  "task_id": "uuid",
  "description": "Build user authentication system...",
  "status": "in_progress",  // pending | in_progress | checkpoint | completed | failed | cancelled
  "progress": 45,           // 0-100
  "created_at": "2025-11-11T12:30:00Z",
  "updated_at": "2025-11-11T12:34:22Z",
  "subtasks": [
    {
      "subtask_id": "uuid",
      "name": "Create API endpoints",
      "status": "in_progress",
      "progress": 85,
      "assigned_worker": "machine-1",
      "assigned_tool": "claude_code",
      "started_at": "2025-11-11T12:31:00Z"
    },
    {
      "subtask_id": "uuid",
      "name": "Implement JWT logic",
      "status": "in_progress",
      "progress": 50,
      "assigned_worker": "machine-2",
      "assigned_tool": "gemini_cli",
      "started_at": "2025-11-11T12:31:30Z"
    }
  ],
  "checkpoints": [
    {
      "checkpoint_id": "uuid",
      "triggered_at": "2025-11-11T12:36:00Z",
      "status": "pending_review",  // pending_review | approved | corrected | rejected
      "subtasks_completed": ["uuid-1", "uuid-2"]
    }
  ],
  "evaluation_scores": {
    "overall": 8.5,
    "dimensions": {
      "code_quality": 9.0,
      "completeness": 7.0,
      "security": 9.0,
      "architecture": 8.0,
      "testability": 6.5
    }
  }
}
```

**List Tasks**

```http
GET /api/v1/tasks?status=in_progress&limit=20&offset=0
Authorization: Bearer {jwt_token}

Response (200 OK):
{
  "tasks": [
    {
      "task_id": "uuid",
      "description": "Build user authentication system...",
      "status": "in_progress",
      "progress": 45,
      "created_at": "2025-11-11T12:30:00Z"
    },
    // ...
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

**Cancel Task**

```http
POST /api/v1/tasks/{task_id}/cancel
Authorization: Bearer {jwt_token}

Response (200 OK):
{
  "task_id": "uuid",
  "status": "cancelled",
  "message": "Task cancelled. All agents stopped."
}
```

#### 4.1.2 Worker Management

**List Workers**

```http
GET /api/v1/workers?status=online
Authorization: Bearer {jwt_token}

Response (200 OK):
{
  "workers": [
    {
      "worker_id": "uuid",
      "machine_id": "machine-1",
      "machine_name": "Desktop PC",
      "status": "online",  // online | offline | busy
      "tools": ["claude_code", "gemini_cli"],
      "resources": {
        "cpu_percent": 45,
        "memory_percent": 60,
        "disk_percent": 30
      },
      "current_task": "subtask-uuid",  // null if idle
      "last_heartbeat": "2025-11-11T12:34:25Z",
      "registered_at": "2025-11-10T10:30:00Z"
    },
    // ...
  ]
}
```

**Get Worker Details**

```http
GET /api/v1/workers/{worker_id}
Authorization: Bearer {jwt_token}

Response (200 OK):
{
  "worker_id": "uuid",
  "machine_id": "machine-1",
  "machine_name": "Desktop PC",
  "status": "online",
  "system_info": {
    "os": "Windows 11",
    "cpu": "Intel Core i7-12700K",
    "memory_total_gb": 32,
    "disk_total_gb": 1024
  },
  "tools": ["claude_code", "gemini_cli"],
  "resources": {
    "cpu_percent": 45,
    "memory_percent": 60,
    "disk_percent": 30
  },
  "current_task": {
    "task_id": "uuid",
    "subtask_id": "uuid",
    "subtask_name": "Create API endpoints",
    "started_at": "2025-11-11T12:31:00Z"
  },
  "task_history": [
    {
      "task_id": "uuid",
      "subtask_name": "Implement JWT logic",
      "status": "completed",
      "completed_at": "2025-11-11T12:20:00Z",
      "duration_seconds": 120
    },
    // last 10 tasks
  ],
  "last_heartbeat": "2025-11-11T12:34:25Z",
  "registered_at": "2025-11-10T10:30:00Z"
}
```

**Register Worker** (called by Worker Agent)

```http
POST /api/v1/workers/register
Authorization: Bearer {worker_secret}

Request Body:
{
  "machine_id": "machine-1",
  "machine_name": "Desktop PC",
  "system_info": {
    "os": "Windows 11",
    "cpu": "Intel Core i7-12700K",
    "memory_total_gb": 32,
    "disk_total_gb": 1024
  },
  "tools": ["claude_code", "gemini_cli"]
}

Response (201 Created):
{
  "worker_id": "uuid",
  "status": "registered",
  "message": "Worker registered successfully"
}
```

**Worker Heartbeat** (called by Worker Agent every 30s)

```http
POST /api/v1/workers/{worker_id}/heartbeat
Authorization: Bearer {worker_secret}

Request Body:
{
  "cpu_percent": 45,
  "memory_percent": 60,
  "disk_percent": 30
}

Response (200 OK):
{
  "acknowledged": true,
  "server_time": "2025-11-11T12:34:25Z"
}
```

#### 4.1.3 Checkpoint Management

**Get Checkpoint Details**

```http
GET /api/v1/checkpoints/{checkpoint_id}
Authorization: Bearer {jwt_token}

Response (200 OK):
{
  "checkpoint_id": "uuid",
  "task_id": "uuid",
  "triggered_at": "2025-11-11T12:36:00Z",
  "status": "pending_review",
  "subtasks_completed": [
    {
      "subtask_id": "uuid",
      "name": "Create API endpoints",
      "output": "Created src/api/auth.js with authentication routes...",
      "files_created": ["src/api/auth.js", "src/routes/auth.js"]
    },
    {
      "subtask_id": "uuid",
      "name": "Implement JWT logic",
      "output": "Implemented JWT token generation and verification...",
      "files_created": ["src/auth/jwt.js"]
    }
  ],
  "evaluation_scores": {
    "code_quality": 9.0,
    "completeness": 7.0,
    "security": 9.0,
    "architecture": 8.0,
    "testability": 6.5
  },
  "next_subtasks": [
    {"name": "Write unit tests"},
    {"name": "Generate documentation"}
  ]
}
```

**Approve Checkpoint**

```http
POST /api/v1/checkpoints/{checkpoint_id}/approve
Authorization: Bearer {jwt_token}

Response (200 OK):
{
  "checkpoint_id": "uuid",
  "status": "approved",
  "message": "Checkpoint approved. Continuing to next subtasks..."
}
```

**Reject Checkpoint**

```http
POST /api/v1/checkpoints/{checkpoint_id}/reject
Authorization: Bearer {jwt_token}

Request Body:
{
  "reason": "Approach is incorrect. Need to use bcrypt for password hashing."
}

Response (200 OK):
{
  "checkpoint_id": "uuid",
  "status": "rejected",
  "message": "Checkpoint rejected. Task cancelled."
}
```

**Correct Agent Work**

```http
POST /api/v1/checkpoints/{checkpoint_id}/correct
Authorization: Bearer {jwt_token}

Request Body:
{
  "subtask_id": "uuid",
  "correction_type": "incomplete",  // wrong_approach | incomplete | bug | style | missing_feature | other
  "guidance": "Add try-catch error handling for the token generation function. Also, add validation for empty or null userId before generating tokens.",
  "reference_files": [],  // optional
  "apply_to_future": false  // learning mode
}

Response (200 OK):
{
  "correction_id": "uuid",
  "status": "re_executing",
  "message": "Correction sent to agent. Re-executing subtask..."
}
```

### 4.2 WebSocket Events

**Connection:** `ws://localhost:8000/ws?token={jwt_token}`

**Event Format:**

```json
{
  "type": "event_type",
  "data": { /* event-specific data */ },
  "timestamp": "2025-11-11T12:34:25Z"
}
```

**Client → Server Events:**

| Event Type | Description | Data |
|------------|-------------|------|
| `subscribe` | Subscribe to event types | `{"event_types": ["task_update", "worker_update"]}` |
| `unsubscribe` | Unsubscribe from event types | `{"event_types": ["task_update"]}` |
| `ping` | Heartbeat ping | `{}` |

**Server → Client Events:**

| Event Type | Description | Data Example |
|------------|-------------|--------------|
| `pong` | Heartbeat response | `{}` |
| `task_update` | Task progress update | `{"task_id": "uuid", "progress": 50, "status": "in_progress"}` |
| `subtask_update` | Subtask status change | `{"subtask_id": "uuid", "status": "in_progress", "progress": 75}` |
| `worker_update` | Worker status change | `{"worker_id": "uuid", "status": "online", "resources": {...}}` |
| `checkpoint_ready` | Checkpoint triggered | `{"checkpoint_id": "uuid", "task_id": "uuid"}` |
| `task_complete` | Task completed | `{"task_id": "uuid", "evaluation_scores": {...}}` |
| `task_failed` | Task failed | `{"task_id": "uuid", "error": "Agent timeout"}` |
| `agent_log` | Real-time agent output | `{"subtask_id": "uuid", "message": "Installing dependencies..."}` |

**Example WebSocket Session:**

```javascript
// Client connects
const ws = new WebSocket('ws://localhost:8000/ws?token=abc123');

// Subscribe to events
ws.send(JSON.stringify({
  type: 'subscribe',
  event_types: ['task_update', 'subtask_update', 'checkpoint_ready']
}));

// Receive updates
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'task_update':
      updateTaskProgress(message.data);
      break;
    case 'checkpoint_ready':
      showCheckpointModal(message.data);
      break;
    // ...
  }
};

// Heartbeat
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

---

## 5. Data Architecture

### 5.1 PostgreSQL Schema

**Database:** `multi_agent_db`

#### 5.1.1 Core Tables

**users** (Future - MVP uses simple authentication)

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
```

**workers**

```sql
CREATE TABLE workers (
    worker_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id VARCHAR(100) UNIQUE NOT NULL,
    machine_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'offline',  -- online | offline | busy
    system_info JSONB NOT NULL,  -- {os, cpu, memory_total_gb, disk_total_gb}
    tools JSONB NOT NULL,  -- ["claude_code", "gemini_cli", "ollama"]

    -- Current resources
    cpu_percent FLOAT,
    memory_percent FLOAT,
    disk_percent FLOAT,

    -- Timestamps
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_status CHECK (status IN ('online', 'offline', 'busy'))
);

CREATE INDEX idx_workers_status ON workers(status);
CREATE INDEX idx_workers_last_heartbeat ON workers(last_heartbeat);
```

**tasks**

```sql
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),

    -- Task details
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | initializing | in_progress | checkpoint | completed | failed | cancelled
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),

    -- Configuration
    checkpoint_frequency VARCHAR(20) NOT NULL DEFAULT 'medium',  -- low | medium | high
    privacy_level VARCHAR(20) NOT NULL DEFAULT 'normal',  -- normal | sensitive
    tool_preferences JSONB,  -- ["claude_code", "gemini_cli"]

    -- Metadata
    metadata JSONB,  -- Flexible field for additional data

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_task_status CHECK (status IN ('pending', 'initializing', 'in_progress', 'checkpoint', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_tasks_user ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
```

**subtasks**

```sql
CREATE TABLE subtasks (
    subtask_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,

    -- Subtask details
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | queued | in_progress | completed | failed | correcting
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),

    -- Dependencies (DAG)
    dependencies JSONB DEFAULT '[]',  -- [uuid1, uuid2] - must complete before this subtask

    -- Assignment
    recommended_tool VARCHAR(50),  -- claude_code | gemini_cli | ollama
    assigned_worker UUID REFERENCES workers(worker_id),
    assigned_tool VARCHAR(50),

    -- Complexity & Priority
    complexity INTEGER CHECK (complexity >= 1 AND complexity <= 5),
    priority INTEGER DEFAULT 0,

    -- Output
    output JSONB,  -- {text: "...", files: [...], usage: {...}}
    error TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_subtask_status CHECK (status IN ('pending', 'queued', 'in_progress', 'completed', 'failed', 'correcting'))
);

CREATE INDEX idx_subtasks_task ON subtasks(task_id);
CREATE INDEX idx_subtasks_status ON subtasks(status);
CREATE INDEX idx_subtasks_worker ON subtasks(assigned_worker);
```

**checkpoints**

```sql
CREATE TABLE checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,

    -- Checkpoint details
    status VARCHAR(20) NOT NULL DEFAULT 'pending_review',  -- pending_review | approved | corrected | rejected
    subtasks_completed JSONB NOT NULL,  -- [uuid1, uuid2] - subtask IDs completed at this checkpoint

    -- User decision
    user_decision VARCHAR(20),  -- approve | correct | reject
    decision_notes TEXT,

    -- Timestamps
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_checkpoint_status CHECK (status IN ('pending_review', 'approved', 'corrected', 'rejected'))
);

CREATE INDEX idx_checkpoints_task ON checkpoints(task_id);
CREATE INDEX idx_checkpoints_status ON checkpoints(status);
```

**corrections**

```sql
CREATE TABLE corrections (
    correction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checkpoint_id UUID NOT NULL REFERENCES checkpoints(checkpoint_id) ON DELETE CASCADE,
    subtask_id UUID NOT NULL REFERENCES subtasks(subtask_id),

    -- Correction details
    correction_type VARCHAR(20) NOT NULL,  -- wrong_approach | incomplete | bug | style | missing_feature | other
    guidance TEXT NOT NULL,
    reference_files JSONB DEFAULT '[]',  -- Links or file paths

    -- Result
    result VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | success | failed
    retry_count INTEGER DEFAULT 0,

    -- Learning mode
    apply_to_future BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_correction_type CHECK (correction_type IN ('wrong_approach', 'incomplete', 'bug', 'style', 'missing_feature', 'other'))
);

CREATE INDEX idx_corrections_checkpoint ON corrections(checkpoint_id);
CREATE INDEX idx_corrections_subtask ON corrections(subtask_id);
```

**evaluations**

```sql
CREATE TABLE evaluations (
    evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subtask_id UUID NOT NULL REFERENCES subtasks(subtask_id) ON DELETE CASCADE,

    -- Evaluation scores (0-10)
    code_quality DECIMAL(3,1) CHECK (code_quality >= 0 AND code_quality <= 10),
    completeness DECIMAL(3,1) CHECK (completeness >= 0 AND completeness <= 10),
    security DECIMAL(3,1) CHECK (security >= 0 AND security <= 10),
    architecture DECIMAL(3,1) CHECK (architecture >= 0 AND architecture <= 10),
    testability DECIMAL(3,1) CHECK (testability >= 0 AND testability <= 10),

    -- Overall score (weighted average)
    overall_score DECIMAL(3,1) CHECK (overall_score >= 0 AND overall_score <= 10),

    -- Detailed results
    details JSONB,  -- {code_quality: {issues: [...], score_breakdown: {...}}, ...}

    -- Timestamp
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evaluations_subtask ON evaluations(subtask_id);
CREATE INDEX idx_evaluations_overall_score ON evaluations(overall_score);
```

**activity_logs**

```sql
CREATE TABLE activity_logs (
    log_id BIGSERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
    subtask_id UUID REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    worker_id UUID REFERENCES workers(worker_id),

    -- Log details
    level VARCHAR(10) NOT NULL,  -- info | warning | error
    message TEXT NOT NULL,
    metadata JSONB,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_logs_task ON activity_logs(task_id);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);
```

#### 5.1.2 Alembic Migration Example

```python
# alembic/versions/001_initial_schema.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login', sa.TIMESTAMP(timezone=True)),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # Create workers table
    op.create_table(
        'workers',
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('machine_id', sa.String(100), unique=True, nullable=False),
        sa.Column('machine_name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='offline'),
        sa.Column('system_info', postgresql.JSONB, nullable=False),
        sa.Column('tools', postgresql.JSONB, nullable=False),
        sa.Column('cpu_percent', sa.Float),
        sa.Column('memory_percent', sa.Float),
        sa.Column('disk_percent', sa.Float),
        sa.Column('last_heartbeat', sa.TIMESTAMP(timezone=True)),
        sa.Column('registered_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("status IN ('online', 'offline', 'busy')", name='chk_status')
    )
    op.create_index('idx_workers_status', 'workers', ['status'])
    op.create_index('idx_workers_last_heartbeat', 'workers', ['last_heartbeat'])

    # ... (remaining tables)

def downgrade():
    op.drop_table('activity_logs')
    op.drop_table('evaluations')
    op.drop_table('corrections')
    op.drop_table('checkpoints')
    op.drop_table('subtasks')
    op.drop_table('tasks')
    op.drop_table('workers')
    op.drop_table('users')
```

### 5.2 Redis Data Structures

**Purpose:** Fast in-memory operations for task queue, worker status, WebSocket sessions

#### 5.2.1 Task Queue (List)

```redis
# Pending subtask IDs (FIFO queue)
LPUSH task_queue:pending {subtask_id}
RPOP task_queue:pending  # Worker pulls task

# In-progress subtask tracking (Set)
SADD task_queue:in_progress {subtask_id}
SREM task_queue:in_progress {subtask_id}  # When completed/failed
```

#### 5.2.2 Worker Status (Hash)

```redis
# Worker online status (fast lookup)
HSET workers:status {worker_id} "online"
HGET workers:status {worker_id}

# Worker current task (Hash)
HSET workers:current_task {worker_id} {subtask_id}
HDEL workers:current_task {worker_id}  # When task completes
```

#### 5.2.3 WebSocket Session Management (Set)

```redis
# Active WebSocket connection IDs
SADD websocket:connections {client_id}
SREM websocket:connections {client_id}

# Subscription mapping (client to event types)
SADD websocket:subscriptions:{client_id} "task_update"
SADD websocket:subscriptions:{client_id} "worker_update"
SMEMBERS websocket:subscriptions:{client_id}
```

#### 5.2.4 Pub/Sub Channels

```redis
# Publish event (for multi-instance backend scaling)
PUBLISH events:task_update '{"task_id": "uuid", "progress": 50}'
PUBLISH events:checkpoint_ready '{"checkpoint_id": "uuid", "task_id": "uuid"}'

# Subscribe to events
SUBSCRIBE events:task_update
SUBSCRIBE events:checkpoint_ready
```

#### 5.2.5 Rate Limiting (String with TTL)

```redis
# API rate limiting (per user per endpoint)
SET ratelimit:{user_id}:{endpoint} 1 EX 60  # 1 request per minute
INCR ratelimit:{user_id}:{endpoint}
GET ratelimit:{user_id}:{endpoint}
```

---

## 6. Communication Protocols

### 6.1 Frontend ↔ Backend

**Protocol 1: REST API (HTTP/HTTPS)**

- **Usage:** CRUD operations (create task, get worker list, approve checkpoint)
- **Format:** JSON
- **Authentication:** JWT Bearer Token in `Authorization` header
- **Error Handling:** Standard HTTP status codes (200, 201, 400, 401, 404, 500)

**Protocol 2: WebSocket (WSS)**

- **Usage:** Real-time updates (task progress, worker status, logs)
- **Format:** JSON events
- **Authentication:** JWT token in query parameter (`?token=abc123`)
- **Reconnection:** Automatic with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- **Heartbeat:** Ping/Pong every 30 seconds

### 6.2 Backend ↔ Worker Agent

**Protocol: WebSocket (WSS)**

- **Usage:** Bidirectional communication (task assignment, heartbeat, result reporting)
- **Format:** JSON messages
- **Authentication:** Worker secret token (pre-shared key or registration token)
- **Reconnection:** Worker attempts reconnection with exponential backoff
- **Heartbeat:** Worker sends heartbeat every 30 seconds

**Message Types:**

| Direction | Type | Purpose |
|-----------|------|---------|
| Worker → Backend | `worker_register` | Worker registration on startup |
| Worker → Backend | `heartbeat` | Worker status and resource update |
| Worker → Backend | `task_result` | Subtask completion or failure |
| Backend → Worker | `execute_task` | Assign subtask to worker |
| Backend → Worker | `cancel_task` | Cancel in-progress subtask |

### 6.3 Backend ↔ PostgreSQL

**Protocol:** PostgreSQL Wire Protocol (asyncpg driver)

- **Connection Pooling:** Max 20 connections per backend instance
- **Async Queries:** All database operations are async (await)
- **Transactions:** ACID transactions for critical operations (task state changes)

### 6.4 Backend ↔ Redis

**Protocol:** RESP (Redis Serialization Protocol)

- **Client:** aioredis (async Redis client)
- **Connection Pooling:** Max 10 connections per backend instance
- **Pub/Sub:** Separate connection for subscription listening

---

## 7. Security Architecture

### 7.1 Authentication & Authorization

**User Authentication (Frontend):**

- **Method:** JWT (JSON Web Token)
- **Login Flow:**
  1. User submits username/password to `/api/v1/auth/login`
  2. Backend verifies credentials (bcrypt password hash)
  3. Backend generates JWT with user claims (`user_id`, `email`, `roles`)
  4. Frontend stores JWT in secure storage (not localStorage due to XSS risk)
  5. Frontend includes JWT in `Authorization: Bearer {token}` header for all requests

- **JWT Structure:**
  ```json
  {
    "user_id": "uuid",
    "email": "user@example.com",
    "roles": ["user"],
    "iat": 1699718400,  // Issued at
    "exp": 1699804800   // Expires in 24 hours
  }
  ```

- **Token Refresh:** Refresh token mechanism (POST `/api/v1/auth/refresh`)

**Worker Authentication:**

- **Method:** Pre-shared worker secret (for MVP) or registration token
- **Configuration:** Worker secret stored in `config/agent.yaml` (not in code)
- **Future:** Mutual TLS (mTLS) for enhanced security

### 7.2 Data Security

**Sensitive Data Protection:**

- **Passwords:** Hashed with bcrypt (cost factor 12)
- **Secrets:** Environment variables (never in code)
- **Database:** Encrypted connections (SSL/TLS)
- **API Keys:** Stored in environment variables, never logged

**Privacy Levels:**

- **Normal:** Use any available AI tool (Claude, Gemini, cloud LLM)
- **Sensitive:** Prefer local LLM (Ollama) for privacy-critical tasks

### 7.3 Network Security

**HTTPS/WSS (Production):**

- All communication encrypted with TLS 1.3
- SSL certificates via Let's Encrypt (auto-renewal)
- HSTS (HTTP Strict Transport Security) enabled

**CORS (Cross-Origin Resource Sharing):**

```python
# backend/main.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],  # Specific origins (not "*")
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Rate Limiting:**

- Per-user API rate limits (e.g., 100 requests per minute)
- Implemented via Redis (`INCR` with TTL)

### 7.4 Input Validation

**Pydantic Models (Backend):**

```python
# models/task.py

from pydantic import BaseModel, Field, validator

class TaskSubmission(BaseModel):
    description: str = Field(..., min_length=10, max_length=5000)
    checkpoint_frequency: str = Field(default="medium", regex="^(low|medium|high)$")
    privacy_level: str = Field(default="normal", regex="^(normal|sensitive)$")
    tool_preferences: Optional[List[str]] = None

    @validator('tool_preferences')
    def validate_tools(cls, v):
        if v is None:
            return v
        valid_tools = {"claude_code", "gemini_cli", "ollama", "codex"}
        if not set(v).issubset(valid_tools):
            raise ValueError(f"Invalid tools. Must be subset of {valid_tools}")
        return v
```

**SQL Injection Prevention:**

- Use ORM (SQLAlchemy) with parameterized queries (never raw SQL with user input)

**XSS Prevention:**

- Frontend sanitizes user input before rendering (Flutter handles this automatically)
- Backend doesn't return raw HTML (only JSON)

---

## 8. Deployment Architecture

### 8.1 Development Environment (Local)

**Docker Compose** for local development:

```yaml
# docker-compose.yml

version: '3.9'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: multi-agent-postgres
    environment:
      POSTGRES_DB: multi_agent_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: multi-agent-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: multi-agent-backend
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres_dev_password@postgres:5432/multi_agent_db
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: dev_secret_key_change_in_production
      ENVIRONMENT: development
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  # Optional: pgAdmin for database management
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: multi-agent-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
  redis_data:
```

**Start Development Environment:**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

**Backend Dockerfile:**

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run database migrations on startup (optional, can be separate)
# CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 Production Deployment (Future)

**Architecture (Post-MVP):**

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Provider (AWS/GCP/Azure)          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐          ┌────────────────────────────┐    │
│  │ CDN         │          │  Load Balancer             │    │
│  │ (Flutter)   │          │  (FastAPI Backend x N)     │    │
│  └─────────────┘          └────────────┬───────────────┘    │
│                                        │                     │
│                   ┌────────────────────┼──────────────────┐ │
│                   │                    │                  │ │
│         ┌─────────▼────────┐  ┌───────▼───────┐  ┌──────▼─────┐
│         │ PostgreSQL RDS   │  │  Redis Cluster│  │ WebSocket  │
│         │ (Multi-AZ)       │  │  (ElastiCache)│  │  Gateway   │
│         └──────────────────┘  └───────────────┘  └────────────┘
└─────────────────────────────────────────────────────────────┘
```

**Components:**

- **Frontend:** Static hosting (AWS S3 + CloudFront, Netlify, Vercel)
- **Backend:** Container orchestration (ECS, Kubernetes) with auto-scaling
- **Database:** Managed PostgreSQL (AWS RDS, Google Cloud SQL)
- **Cache:** Managed Redis (AWS ElastiCache, Google Memorystore)
- **Monitoring:** Prometheus + Grafana, Sentry for error tracking
- **CI/CD:** GitHub Actions → Build Docker images → Deploy to ECS/K8s

---

## 9. Performance & Scalability

### 9.1 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task Submission Response | < 2s | API endpoint latency |
| WebSocket Latency | < 500ms | Client → Server → Client round-trip |
| Worker Heartbeat Processing | < 100ms | Backend processing time |
| Task Decomposition | < 5s | LLM API call + database writes |
| Dashboard Load Time | < 3s | Time to first meaningful paint |
| Concurrent Users | 100+ | Number of simultaneous WebSocket connections |
| Worker Capacity | 10+ machines | Number of registered workers |
| Parallel Tasks | 20+ | Concurrent subtasks executing across workers |

### 9.2 Scalability Strategy

**Vertical Scaling (MVP):**
- Single backend instance with sufficient resources (4 CPU, 16GB RAM)
- PostgreSQL and Redis on same server or managed services

**Horizontal Scaling (Post-MVP):**

**Backend Scaling:**
- Multiple backend instances behind load balancer
- Stateless API design (JWT auth, no server-side sessions)
- WebSocket sticky sessions (route client to same backend instance)

**Database Scaling:**
- PostgreSQL read replicas for read-heavy queries (task list, worker list)
- Connection pooling (pgbouncer) to handle more connections
- Database sharding by user_id (if user base grows significantly)

**Redis Scaling:**
- Redis Cluster for high availability and horizontal scaling
- Separate Redis instances for different purposes (cache, queue, Pub/Sub)

**Worker Scaling:**
- Workers are inherently horizontally scalable (just add more machines)
- Backend task allocation algorithm automatically distributes work

### 9.3 Caching Strategy

**Redis Cache Layers:**

1. **Worker Status Cache** (TTL: 60s)
   - Fast lookup for available workers
   - Invalidated on heartbeat

2. **Task List Cache** (TTL: 30s)
   - Cached task list for dashboard
   - Invalidated on task status change

3. **Frequently Accessed Data** (TTL: 300s)
   - User profiles, system configuration
   - Invalidated on update

**Database Query Optimization:**

- Indexed columns: `status`, `created_at`, `user_id`, `task_id`
- JSONB GIN indexes for metadata searches
- Materialized views for complex aggregations (e.g., worker statistics)

---

## 10. Implementation Patterns

### 10.1 Error Handling Patterns

**Backend (FastAPI):**

```python
# exceptions.py

class MultiAgentException(Exception):
    """Base exception for all Multi-Agent errors"""
    pass

class WorkerOfflineError(MultiAgentException):
    """Raised when no workers are available"""
    pass

class TaskDecompositionError(MultiAgentException):
    """Raised when LLM fails to decompose task"""
    pass

# main.py

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(WorkerOfflineError)
async def worker_offline_handler(request: Request, exc: WorkerOfflineError):
    return JSONResponse(
        status_code=503,
        content={
            "error": "no_workers_available",
            "message": "No workers are currently online. Please start at least one worker.",
            "details": str(exc)
        }
    )

@app.exception_handler(TaskDecompositionError)
async def task_decomposition_handler(request: Request, exc: TaskDecompositionError):
    return JSONResponse(
        status_code=500,
        content={
            "error": "task_decomposition_failed",
            "message": "Failed to decompose task into subtasks. Please try again or simplify the task description.",
            "details": str(exc)
        }
    )
```

**Frontend (Flutter):**

```dart
// exceptions/api_exception.dart

class ApiException implements Exception {
  final int statusCode;
  final String error;
  final String message;
  final String? details;

  ApiException({
    required this.statusCode,
    required this.error,
    required this.message,
    this.details,
  });

  factory ApiException.fromJson(int statusCode, Map<String, dynamic> json) {
    return ApiException(
      statusCode: statusCode,
      error: json['error'] ?? 'unknown_error',
      message: json['message'] ?? 'An unknown error occurred',
      details: json['details'],
    );
  }
}

// repositories/task_repository.dart

class TaskRepository {
  final ApiClient _client;

  Future<Task> submitTask(TaskSubmission submission) async {
    try {
      final response = await _client.post('/api/v1/tasks', data: submission.toJson());
      return Task.fromJson(response.data);
    } on DioException catch (e) {
      if (e.response != null) {
        throw ApiException.fromJson(e.response!.statusCode!, e.response!.data);
      } else {
        throw ApiException(
          statusCode: 0,
          error: 'network_error',
          message: 'Network error. Please check your connection.',
        );
      }
    }
  }
}

// UI error handling

try {
  await ref.read(taskListNotifierProvider.notifier).submitTask(submission);
  // Show success message
} on ApiException catch (e) {
  if (e.error == 'no_workers_available') {
    // Show specific error message
    showDialog(/* "No workers online. Please start a worker." */);
  } else {
    // Show generic error
    showSnackBar(e.message);
  }
}
```

### 10.2 Retry & Resilience Patterns

**Subtask Retry Logic:**

```python
# services/scheduler_service.py

MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]  # seconds

async def handle_subtask_failure(subtask_id: UUID, error: str):
    subtask = await subtask_repo.get_by_id(subtask_id)

    if subtask.retry_count < MAX_RETRIES:
        # Increment retry count
        subtask.retry_count += 1
        await subtask_repo.update(subtask)

        # Schedule retry with exponential backoff
        delay = RETRY_DELAYS[min(subtask.retry_count - 1, len(RETRY_DELAYS) - 1)]
        scheduler.add_job(
            func=retry_subtask,
            args=[subtask_id],
            trigger='date',
            run_date=datetime.now() + timedelta(seconds=delay)
        )

        logger.info(f"Subtask {subtask_id} retry {subtask.retry_count}/{MAX_RETRIES} scheduled in {delay}s")
    else:
        # Max retries exceeded, fail subtask and task
        subtask.status = SubtaskStatus.FAILED
        await subtask_repo.update(subtask)

        await task_service.fail_task(
            subtask.task_id,
            reason=f"Subtask {subtask.name} failed after {MAX_RETRIES} retries"
        )
```

**Worker Reconnection:**

```python
# worker/connection_manager.py

async def connect_with_retry(self):
    attempt = 0
    max_attempts = 10

    while attempt < max_attempts:
        try:
            await self.connect()
            logger.info("Connected to backend")
            return
        except Exception as e:
            attempt += 1
            delay = min(2 ** attempt, 60)  # Exponential backoff, max 60s
            logger.warning(f"Connection failed (attempt {attempt}/{max_attempts}). Retrying in {delay}s...")
            await asyncio.sleep(delay)

    logger.error(f"Failed to connect after {max_attempts} attempts")
    raise ConnectionError("Could not connect to backend")
```

### 10.3 Logging & Observability

**Structured Logging (Backend):**

```python
# utils/logger.py

import structlog

logger = structlog.get_logger()

# Usage in services
await logger.info(
    "task_submitted",
    task_id=str(task.id),
    user_id=str(user_id),
    description=task.description[:100],
    checkpoint_frequency=task.checkpoint_frequency
)

await logger.error(
    "subtask_execution_failed",
    subtask_id=str(subtask.id),
    task_id=str(task.id),
    worker_id=str(worker.id),
    error=str(error),
    retry_count=subtask.retry_count
)
```

**Metrics Collection (Future):**

```python
# utils/metrics.py

from prometheus_client import Counter, Histogram

# Define metrics
task_submissions = Counter('task_submissions_total', 'Total task submissions')
task_duration = Histogram('task_duration_seconds', 'Task execution duration')
worker_heartbeats = Counter('worker_heartbeats_total', 'Total worker heartbeats')

# Usage
task_submissions.inc()

with task_duration.time():
    await execute_task(task)

worker_heartbeats.labels(worker_id=worker.id).inc()
```

### 10.4 Testing Patterns

**Backend Unit Tests:**

```python
# tests/test_task_service.py

import pytest
from services.task_service import TaskService
from models.task import TaskSubmission

@pytest.fixture
async def task_service():
    # Setup mock repositories
    return TaskService(task_repo=mock_task_repo, worker_repo=mock_worker_repo)

@pytest.mark.asyncio
async def test_task_decomposition(task_service):
    submission = TaskSubmission(
        description="Build user authentication system",
        checkpoint_frequency="medium"
    )

    subtasks = await task_service.decompose_task(submission)

    assert len(subtasks) >= 2
    assert subtasks[0].dependencies == []  # First subtask has no dependencies
    # Validate DAG structure
    for subtask in subtasks:
        for dep_id in subtask.dependencies:
            assert any(st.id == dep_id for st in subtasks)
```

**Frontend Widget Tests:**

```dart
// test/widgets/task_card_test.dart

void main() {
  testWidgets('TaskCard displays task name and progress', (WidgetTester tester) async {
    final task = Task(
      id: 'test-id',
      description: 'Build auth system',
      status: TaskStatus.inProgress,
      progress: 45,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: TaskCard(task: task),
        ),
      ),
    );

    expect(find.text('Build auth system'), findsOneWidget);
    expect(find.text('45%'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
  });
}
```

**Integration Tests (E2E):**

```python
# tests/integration/test_task_flow.py

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_task_execution_flow():
    """Test complete task flow from submission to completion"""

    # 1. Submit task
    response = await client.post("/api/v1/tasks", json={
        "description": "Create a simple Hello World function",
        "checkpoint_frequency": "low"
    })
    assert response.status_code == 201
    task_id = response.json()["task_id"]

    # 2. Wait for task decomposition
    await asyncio.sleep(5)

    # 3. Check task status
    response = await client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    task = response.json()
    assert task["status"] in ["in_progress", "completed"]
    assert len(task["subtasks"]) >= 1

    # 4. Wait for completion (or timeout)
    max_wait = 60
    for _ in range(max_wait):
        response = await client.get(f"/api/v1/tasks/{task_id}")
        task = response.json()
        if task["status"] == "completed":
            break
        await asyncio.sleep(1)

    assert task["status"] == "completed"
    assert task["progress"] == 100
```

---

## 11. Appendices

### 11.1 Technology Decision Records (TDRs)

**TDR-001: Why Flutter over React/Vue for Frontend?**

- **Decision:** Use Flutter for cross-platform frontend
- **Rationale:**
  - Single codebase for Desktop + Web + Mobile
  - Native performance (compiled to machine code for Desktop)
  - Material Design 3 first-class support
  - Strong type safety (Dart)
  - Hot reload for fast development
- **Alternatives Considered:**
  - React + Electron (heavier, less performant)
  - Vue + Tauri (smaller ecosystem)
- **Status:** Accepted

**TDR-002: Why FastAPI over Flask/Django?**

- **Decision:** Use FastAPI for backend
- **Rationale:**
  - Built for async from ground up (critical for WebSocket + high concurrency)
  - Automatic OpenAPI documentation
  - Modern Python with type hints (Pydantic validation)
  - Excellent performance (comparable to Node.js)
- **Alternatives Considered:**
  - Flask: Lacks built-in async support, requires extensions
  - Django: Too heavyweight for API-only backend, not async-first
- **Status:** Accepted

**TDR-003: Why PostgreSQL over MongoDB?**

- **Decision:** Use PostgreSQL for primary database
- **Rationale:**
  - ACID transactions critical for task state consistency
  - JSONB support for flexible metadata (best of both SQL and NoSQL)
  - Proven at scale, mature ecosystem
  - Full-text search, complex queries
- **Alternatives Considered:**
  - MongoDB: Eventual consistency not suitable for task orchestration
  - MySQL: Less feature-rich than PostgreSQL (no JSONB, weaker full-text search)
- **Status:** Accepted

### 11.2 Glossary

- **Agent:** AI tool executing tasks (Claude Code, Gemini CLI, Ollama)
- **Worker:** Physical machine running Worker Agent software
- **Task:** User-submitted job to be executed (e.g., "Build auth system")
- **Subtask:** Atomic unit of work decomposed from task (e.g., "Create API endpoints")
- **Checkpoint:** Human review point during task execution
- **Evaluation Framework:** Automated quality scoring system (5 dimensions)
- **Correction:** User feedback to agent when output is incorrect
- **DAG:** Directed Acyclic Graph (subtask dependency structure)

### 11.3 References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Flutter Documentation](https://docs.flutter.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [Material Design 3](https://m3.material.io/)
- [WebSocket Protocol (RFC 6455)](https://datatracker.ietf.org/doc/html/rfc6455)
- [JWT Specification (RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)

### 11.4 Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-11 | Initial architecture document | sir |

---

**Document End**

_This architecture document is a living document and will be updated as the system evolves._
