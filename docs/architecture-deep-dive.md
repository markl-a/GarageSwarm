# Architecture Deep Dive

A comprehensive guide to the Multi-Agent on the Web platform architecture, covering all components, design patterns, and implementation details.

## Table of Contents

- [Project Structure](#project-structure)
- [Backend Architecture](#backend-architecture)
- [Worker Agent Architecture](#worker-agent-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Task Scheduling Architecture](#task-scheduling-architecture)
- [Evaluation Framework Architecture](#evaluation-framework-architecture)
- [Database Design](#database-design)
- [Communication Protocols](#communication-protocols)
- [Security Architecture](#security-architecture)
- [Scalability Considerations](#scalability-considerations)

## Project Structure

```
bmad-test/
├── backend/                    # FastAPI Backend Service
│   ├── src/
│   │   ├── api/               # REST API endpoints
│   │   │   └── v1/           # API version 1
│   │   │       ├── workers.py        # Worker management endpoints
│   │   │       ├── tasks.py          # Task management endpoints
│   │   │       ├── subtasks.py       # Subtask endpoints
│   │   │       ├── checkpoints.py    # Checkpoint endpoints
│   │   │       ├── evaluations.py    # Evaluation endpoints
│   │   │       ├── websocket.py      # WebSocket endpoint
│   │   │       └── health.py         # Health check endpoint
│   │   │
│   │   ├── services/          # Business logic layer
│   │   │   ├── task_service.py       # Task CRUD operations
│   │   │   ├── task_decomposer.py    # Task decomposition logic
│   │   │   ├── task_allocator.py     # Task allocation engine
│   │   │   ├── task_scheduler.py     # Task scheduling & DAG execution
│   │   │   ├── worker_service.py     # Worker management
│   │   │   ├── checkpoint_service.py # Checkpoint management
│   │   │   ├── review_service.py     # Review & correction logic
│   │   │   └── redis_service.py      # Redis operations
│   │   │
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── base.py               # Base model class
│   │   │   ├── user.py               # User model
│   │   │   ├── task.py               # Task model
│   │   │   ├── subtask.py            # Subtask model
│   │   │   ├── worker.py             # Worker model
│   │   │   ├── checkpoint.py         # Checkpoint model
│   │   │   ├── correction.py         # Correction model
│   │   │   ├── evaluation.py         # Evaluation model
│   │   │   └── activity_log.py       # Activity log model
│   │   │
│   │   ├── schemas/           # Pydantic schemas (DTOs)
│   │   │   ├── task.py               # Task schemas
│   │   │   ├── subtask.py            # Subtask schemas
│   │   │   ├── worker.py             # Worker schemas
│   │   │   ├── checkpoint.py         # Checkpoint schemas
│   │   │   ├── evaluation.py         # Evaluation schemas
│   │   │   ├── allocation.py         # Allocation schemas
│   │   │   ├── scheduler.py          # Scheduler schemas
│   │   │   └── log.py                # Log schemas
│   │   │
│   │   ├── evaluators/        # Code evaluation framework
│   │   │   ├── base.py               # Base evaluator interface
│   │   │   ├── code_quality.py       # Code quality evaluator
│   │   │   ├── completeness.py       # Completeness evaluator
│   │   │   ├── security.py           # Security evaluator
│   │   │   └── aggregator.py         # Score aggregation
│   │   │
│   │   ├── repositories/      # Data access layer (future)
│   │   ├── database.py        # Database connection & session
│   │   ├── redis_client.py    # Redis client setup
│   │   ├── config.py          # Configuration management
│   │   ├── logging_config.py  # Structured logging setup
│   │   ├── dependencies.py    # FastAPI dependency injection
│   │   └── main.py           # Application entry point
│   │
│   ├── alembic/              # Database migrations
│   │   ├── versions/
│   │   │   ├── 001_initial_schema.py
│   │   │   └── 002_add_subtask_type.py
│   │   └── env.py
│   │
│   ├── tests/                # Test suite
│   │   ├── unit/            # Unit tests
│   │   ├── integration/     # Integration tests
│   │   └── conftest.py      # Pytest fixtures
│   │
│   └── requirements.txt      # Python dependencies
│
├── worker-agent/             # Worker Agent SDK
│   ├── src/
│   │   ├── agent/           # Agent core logic
│   │   │   ├── core.py              # Main WorkerAgent class
│   │   │   ├── connection.py        # Backend connection manager
│   │   │   ├── executor.py          # Task execution engine
│   │   │   └── monitor.py           # Resource monitoring
│   │   │
│   │   ├── tools/           # AI tool adapters
│   │   │   ├── base.py              # BaseTool interface
│   │   │   ├── claude_code.py       # Claude Code adapter
│   │   │   ├── gemini_cli.py        # Gemini CLI adapter
│   │   │   └── ollama.py            # Ollama adapter
│   │   │
│   │   ├── config.py        # Configuration loader
│   │   └── main.py          # CLI entry point
│   │
│   ├── config/              # Configuration files
│   │   └── agent.yaml.example
│   │
│   ├── tests/               # Test suite
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   │
│   └── requirements.txt     # Python dependencies
│
├── frontend/                # Flutter Frontend
│   ├── lib/
│   │   ├── screens/        # UI screens
│   │   │   ├── dashboard/
│   │   │   ├── tasks/
│   │   │   ├── workers/
│   │   │   └── settings/
│   │   │
│   │   ├── widgets/        # Reusable widgets
│   │   │   ├── task_card.dart
│   │   │   ├── worker_card.dart
│   │   │   └── status_badge.dart
│   │   │
│   │   ├── providers/      # Riverpod state management
│   │   │   ├── task_provider.dart
│   │   │   ├── worker_provider.dart
│   │   │   └── websocket_provider.dart
│   │   │
│   │   ├── services/       # API & WebSocket clients
│   │   │   ├── api_service.dart
│   │   │   └── websocket_service.dart
│   │   │
│   │   ├── models/         # Data models
│   │   │   ├── task.dart
│   │   │   ├── worker.dart
│   │   │   └── subtask.dart
│   │   │
│   │   └── main.dart       # Application entry point
│   │
│   ├── test/               # Test suite
│   └── pubspec.yaml        # Dart dependencies
│
├── docs/                   # Documentation
│   ├── architecture.md
│   ├── architecture-deep-dive.md (this file)
│   ├── development.md
│   ├── contributing.md
│   ├── PRD.md
│   ├── epics.md
│   └── sprint-1-plan.md
│
├── docker/                 # Docker configurations
│   ├── backend.Dockerfile
│   ├── worker.Dockerfile
│   └── frontend.Dockerfile
│
├── docker-compose.yml      # Docker Compose configuration
├── Makefile               # Development commands
└── README.md              # Project overview
```

## Backend Architecture

The backend follows a **layered architecture** pattern with clear separation of concerns.

### Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  ┌────────────┬────────────┬────────────┬─────────────┐    │
│  │  Workers   │   Tasks    │  Subtasks  │  WebSocket  │    │
│  │   API      │    API     │    API     │     API     │    │
│  └────────────┴────────────┴────────────┴─────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  ┌──────────────┬──────────────┬──────────────────────┐    │
│  │    Task      │     Task     │       Worker         │    │
│  │  Decomposer  │   Allocator  │      Service         │    │
│  ├──────────────┼──────────────┼──────────────────────┤    │
│  │    Task      │   Review     │     Checkpoint       │    │
│  │  Scheduler   │   Service    │      Service         │    │
│  └──────────────┴──────────────┴──────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌────────────────────────┬──────────────────────────┐     │
│  │  SQLAlchemy Models     │   Pydantic Schemas       │     │
│  │  (ORM)                 │   (DTOs)                 │     │
│  └────────────────────────┴──────────────────────────┘     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               Storage Layer                                  │
│  ┌──────────────────────┬─────────────────────────────┐    │
│  │   PostgreSQL         │        Redis                │    │
│  │  (Persistent)        │      (Cache/State)          │    │
│  └──────────────────────┴─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### API Layer

The API layer uses **FastAPI** for high-performance async API endpoints.

**Key Features:**
- RESTful API design
- OpenAPI (Swagger) auto-documentation
- Async/await for non-blocking I/O
- Dependency injection for database sessions
- Request validation with Pydantic schemas
- WebSocket support for real-time communication

**Example Endpoint Structure:**

```python
# backend/src/api/v1/tasks.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.dependencies import get_db
from src.services.task_service import TaskService
from src.schemas.task import TaskCreate, TaskResponse

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new task"""
    service = TaskService(db)
    task = await service.create_task(task_data)
    return task
```

### Service Layer

The service layer contains **business logic** and orchestrates between the API and data layers.

**Key Services:**

1. **TaskService**: CRUD operations for tasks
2. **TaskDecomposer**: Breaks tasks into subtasks using rule-based templates
3. **TaskAllocator**: Assigns subtasks to workers based on scoring algorithm
4. **TaskScheduler**: Manages task execution with DAG dependency resolution
5. **WorkerService**: Worker registration, heartbeat, and status management
6. **CheckpointService**: Human checkpoint management
7. **ReviewService**: Agent review and correction workflow
8. **RedisService**: Redis operations for caching and real-time state

**Example Service Implementation:**

```python
# backend/src/services/task_service.py
class TaskService:
    def __init__(self, db: AsyncSession, redis: RedisService):
        self.db = db
        self.redis = redis

    async def create_task(self, task_data: TaskCreate) -> Task:
        # Create task in database
        task = Task(**task_data.dict())
        self.db.add(task)
        await self.db.commit()

        # Cache in Redis
        await self.redis.set_task_status(task.task_id, "pending")

        return task
```

### Data Layer

**SQLAlchemy Models** (ORM):
- Map Python classes to database tables
- Define relationships between entities
- Include constraints and indexes

**Pydantic Schemas** (DTOs):
- Validate request/response data
- Automatic JSON serialization/deserialization
- Type safety and IDE autocomplete

**Example Model & Schema:**

```python
# Model (backend/src/models/task.py)
from sqlalchemy import Column, String, Integer, TEXT
from sqlalchemy.dialects.postgresql import UUID, JSONB

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True)
    description = Column(TEXT, nullable=False)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    task_metadata = Column(JSONB, nullable=True)

# Schema (backend/src/schemas/task.py)
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    description: str = Field(..., min_length=10)
    checkpoint_frequency: str = "medium"
    privacy_level: str = "normal"

class TaskResponse(BaseModel):
    task_id: UUID
    description: str
    status: str
    progress: int

    class Config:
        from_attributes = True
```

## Worker Agent Architecture

The Worker Agent is a **distributed agent** that runs on worker machines and executes tasks assigned by the backend.

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WorkerAgent (Core)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • Lifecycle management                              │  │
│  │  • Signal handling (graceful shutdown)               │  │
│  │  • Component coordination                            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────┬─────────────────┬────────────────┬───────────────┘
           │                 │                │
           ▼                 ▼                ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
│  Connection     │  │   Task       │  │    Resource      │
│   Manager       │  │  Executor    │  │     Monitor      │
│                 │  │              │  │                  │
│ • Registration  │  │ • Tool mgmt  │  │ • CPU/Memory     │
│ • Heartbeat     │  │ • Execution  │  │ • Disk usage     │
│ • WebSocket     │  │ • Logging    │  │ • Thresholds     │
│ • API calls     │  │ • Results    │  │                  │
└─────────────────┘  └──────────────┘  └──────────────────┘
           │                 │
           │                 ▼
           │         ┌──────────────────────┐
           │         │     AI Tools         │
           │         │  ┌────────────────┐  │
           │         │  │  Claude Code   │  │
           │         │  ├────────────────┤  │
           │         │  │  Gemini CLI    │  │
           │         │  ├────────────────┤  │
           │         │  │  Ollama        │  │
           │         │  └────────────────┘  │
           │         └──────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│         Backend API              │
│  • REST endpoints                │
│  • WebSocket endpoint            │
└──────────────────────────────────┘
```

### Core Components

#### 1. WorkerAgent (Core)

**Responsibilities:**
- Initialize and coordinate all components
- Manage agent lifecycle (start, run, stop)
- Handle OS signals for graceful shutdown
- Maintain running state

**Key Methods:**
```python
class WorkerAgent:
    async def start(self):
        """Start agent, register with backend, begin loops"""

    async def stop(self):
        """Graceful shutdown with task completion wait"""

    async def _heartbeat_loop(self):
        """Periodic heartbeat to backend"""

    async def _websocket_loop(self):
        """Maintain WebSocket connection"""

    async def _handle_task_assignment(self, task_data):
        """Execute assigned task"""
```

#### 2. ConnectionManager

**Responsibilities:**
- Backend API communication
- Worker registration and unregistration
- Heartbeat transmission
- WebSocket connection management
- Task result upload
- Log streaming

**Key Methods:**
```python
class ConnectionManager:
    async def register(self, machine_id, machine_name, system_info, tools):
        """Register worker with backend"""

    async def send_heartbeat(self, worker_id, resources, status):
        """Send heartbeat with current status"""

    async def connect_websocket(self, worker_id, message_handler):
        """Establish WebSocket connection"""

    async def upload_subtask_result(self, subtask_id, result):
        """Upload task execution result"""

    async def stream_execution_log(self, subtask_id, log_line, log_level):
        """Stream log lines to backend"""
```

#### 3. TaskExecutor

**Responsibilities:**
- Manage AI tool registry
- Execute tasks using appropriate tools
- Stream execution logs
- Handle tool errors and retries

**Key Methods:**
```python
class TaskExecutor:
    def register_tool(self, name: str, tool: BaseTool):
        """Register AI tool"""

    async def execute_task(self, task_data: dict) -> dict:
        """Execute task using assigned tool"""

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
```

#### 4. ResourceMonitor

**Responsibilities:**
- Monitor system resources (CPU, memory, disk)
- Provide system information
- Check resource thresholds
- Detect resource constraints

**Key Methods:**
```python
class ResourceMonitor:
    def get_resources(self) -> dict:
        """Get current resource usage"""

    def get_system_info(self) -> dict:
        """Get static system information"""

    def check_resource_thresholds(self, cpu_threshold, memory_threshold, disk_threshold):
        """Check if resources exceed thresholds"""
```

### AI Tool Integration

All AI tools implement the **BaseTool** interface:

```python
class BaseTool(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def execute(self, instructions: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute task and return result"""
        pass

    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate tool configuration"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if tool is available"""
        pass
```

**Implemented Tools:**

1. **ClaudeCodeTool**: Integrates with Anthropic's Claude Code
2. **GeminiCLITool**: Integrates with Google's Gemini
3. **OllamaTool**: Integrates with local Ollama LLM

## Frontend Architecture

The frontend uses **Flutter** with **Riverpod** state management following a clean architecture pattern.

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Screens (UI)                         │  │
│  │  • Dashboard  • Tasks  • Workers  • Settings         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Widgets (Components)                 │  │
│  │  • TaskCard  • WorkerCard  • StatusBadge             │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  State Management (Riverpod)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • TaskProvider  • WorkerProvider  • WSProvider      │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌───────────────────────────┬──────────────────────────┐  │
│  │    ApiService (HTTP)      │  WebSocketService (WS)   │  │
│  └───────────────────────────┴──────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Models                               │
│  • Task  • Worker  • Subtask  • Checkpoint                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**Screens**: Full-page views (Dashboard, Task List, Worker List)
**Widgets**: Reusable UI components
**Providers**: State management with Riverpod
**Services**: API and WebSocket communication
**Models**: Data classes with JSON serialization

## Task Scheduling Architecture

The task scheduling system manages task decomposition, allocation, and execution coordination.

### Workflow Diagram

```
User Submits Task
       │
       ▼
┌──────────────────┐
│  Task Created    │  Status: "pending"
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│      TaskDecomposer.decompose_task()     │
│  • Get task type from metadata           │
│  • Load subtask template                 │
│  • Create subtasks with dependencies     │
└────────┬─────────────────────────────────┘
         │                   Status: "initializing"
         ▼
┌──────────────────────────────────────────┐
│      TaskScheduler.schedule_task()       │
│  • Get ready subtasks (no pending deps)  │
│  • For each ready subtask:               │
│    └─> TaskAllocator.allocate_subtask()  │
└────────┬─────────────────────────────────┘
         │                   Status: "in_progress"
         ▼
┌───────────────────────────────────────────────┐
│       TaskAllocator.allocate_subtask()        │
│  • Score each online worker:                  │
│    - Tool match (50%)                         │
│    - Resource availability (30%)              │
│    - Privacy compliance (20%)                 │
│  • Select best worker                         │
│  • Assign subtask via WebSocket/polling       │
└────────┬──────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│        Worker Executes Subtask           │
│  • Receives task via WebSocket           │
│  • Executes using assigned tool          │
│  • Streams logs to backend               │
│  • Uploads result                        │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│     Subtask Result Processing            │
│  • Store result in database              │
│  • Update subtask status: "completed"    │
│  • Check task completion                 │
│  • Schedule next ready subtasks (DAG)    │
└────────┬─────────────────────────────────┘
         │
         ├─> More subtasks? ──> Repeat allocation
         │
         ▼
┌──────────────────────────────────────────┐
│       All Subtasks Complete              │
│  • Update task status: "completed"       │
│  • Calculate overall progress: 100%      │
│  • Set completion timestamp              │
└──────────────────────────────────────────┘
```

### Task Decomposer

Uses **rule-based templates** to decompose tasks into subtasks.

**Supported Task Types:**
- `develop_feature`: Code generation, review, testing, documentation
- `bug_fix`: Analysis, fix implementation, regression testing
- `refactor`: Code analysis, refactoring, test verification
- `code_review`: Static analysis, security review, report generation
- `documentation`: API docs, user guide, README updates
- `testing`: Test planning, unit tests, integration tests, execution report

**Example Template:**

```python
SUBTASK_DEFINITIONS = {
    "develop_feature": [
        {
            "name": "Code Generation",
            "description": "Generate the main code implementation",
            "recommended_tool": "claude_code",
            "complexity": 3,
            "priority": 100,
            "dependencies": []
        },
        {
            "name": "Code Review",
            "description": "Review generated code for quality",
            "recommended_tool": "claude_code",
            "complexity": 2,
            "priority": 80,
            "dependencies": ["Code Generation"]
        },
        # ... more subtasks
    ]
}
```

### Task Allocator

Implements a **scoring algorithm** to select the best worker for each subtask.

**Scoring Formula:**

```
Total Score = (Tool Match Score × 0.5) + (Resource Score × 0.3) + (Privacy Score × 0.2)

Where:
- Tool Match Score: 10 if worker has recommended tool, 0 otherwise
- Resource Score: Based on CPU/memory availability (0-10)
- Privacy Score: 10 if privacy requirements met, 0 otherwise
```

**Allocation Process:**

1. Filter online workers
2. Score each worker
3. Sort by score descending
4. Assign to top worker
5. Send via WebSocket or mark for polling

### Task Scheduler

Manages **DAG-based dependency resolution** and parallel execution.

**Key Features:**
- Identifies ready subtasks (all dependencies satisfied)
- Schedules multiple subtasks in parallel
- Respects dependency constraints
- Monitors completion and triggers next wave

**DAG Example:**

```
Code Generation (priority: 100)
       │
       ├────────────────────┐
       ▼                    ▼
Code Review (80)      Test Generation (70)
       │                    │
       └────────┬───────────┘
                ▼
         Documentation (50)
```

## Evaluation Framework Architecture

The evaluation framework provides **quantitative quality assessment** of code generated by AI tools.

### Evaluator Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EvaluationAggregator                      │
│  • Collects results from all evaluators                     │
│  • Applies weights                                           │
│  • Calculates weighted average score                         │
│  • Triggers checkpoint if score < threshold                  │
└────────┬─────────┬─────────┬─────────┬──────────────────────┘
         │         │         │         │
         ▼         ▼         ▼         ▼
┌────────────┬────────────┬────────────┬──────────────────────┐
│   Code     │ Complete-  │  Security  │  More evaluators...  │
│  Quality   │   ness     │            │                      │
│            │            │            │                      │
│ • Syntax   │ • Require- │ • Vulner-  │                      │
│ • Linting  │   ments    │   ability  │                      │
│ • Complex  │ • Completn.│ • Best     │                      │
│ • Comments │            │   practice │                      │
└────────────┴────────────┴────────────┴──────────────────────┘
```

### BaseEvaluator Interface

All evaluators extend `BaseEvaluator`:

```python
class BaseEvaluator(ABC):
    def __init__(self, weight: float = 1.0):
        self.weight = weight

    @property
    @abstractmethod
    def name(self) -> str:
        """Return evaluator name"""
        pass

    @abstractmethod
    async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate code and return result

        Returns:
            EvaluationResult(
                score: Decimal (0.0-10.0),
                details: Dict[str, Any],
                suggestions: List[str],
                issues: List[Dict[str, Any]]
            )
        """
        pass
```

### Implemented Evaluators

#### 1. CodeQualityEvaluator

**Evaluates:**
- Syntax errors (critical)
- Linting issues (line length, docstrings, blank lines)
- Cyclomatic complexity
- Comment coverage

**Scoring:**
```
score = 10.0 - (syntax_errors × 5) - (lint_warnings × 0.5) - (high_complexity × 1) + (comment_bonus)
```

#### 2. CompletenessEvaluator

**Evaluates:**
- Requirement coverage (keyword matching)
- Code length adequacy
- Function/class presence
- Implementation completeness

**Scoring:**
```
score = (requirement_coverage × 0.5) + (length_score × 0.2) + (structure_score × 0.3)
```

#### 3. SecurityEvaluator

**Evaluates:**
- Hardcoded secrets (API keys, passwords)
- SQL injection risks
- Command injection risks
- Security best practices

**Scoring:**
```
score = 10.0 - (critical_issues × 3) - (high_issues × 1.5) - (medium_issues × 0.5)
```

### EvaluationAggregator

Combines evaluator scores using weighted average:

```python
class EvaluationAggregator:
    def __init__(self, evaluators: List[BaseEvaluator]):
        self.evaluators = evaluators

    async def aggregate_evaluation(self, code: str, context: Dict[str, Any]) -> AggregatedResult:
        # Run all evaluators
        results = await asyncio.gather(*[
            evaluator.evaluate(code, context)
            for evaluator in self.evaluators
        ])

        # Calculate weighted average
        total_weight = sum(e.weight for e in self.evaluators)
        weighted_score = sum(
            result.score * evaluator.weight
            for result, evaluator in zip(results, self.evaluators)
        ) / total_weight

        # Check threshold
        needs_checkpoint = weighted_score < 7.0

        return AggregatedResult(
            overall_score=weighted_score,
            individual_results=results,
            needs_checkpoint=needs_checkpoint
        )
```

## Database Design

### Entity-Relationship Diagram (Textual)

```
┌─────────────┐
│    User     │
│─────────────│
│ user_id PK  │
│ username    │
│ email       │
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────────────┐
│       Task          │
│─────────────────────│
│ task_id PK          │
│ user_id FK          │
│ description         │
│ status              │
│ progress            │
│ checkpoint_frequency│
│ privacy_level       │
└──────┬──────────────┘
       │
       │ 1:N
       ▼
┌─────────────────────┐          ┌──────────────┐
│     Subtask         │ N:1      │   Worker     │
│─────────────────────│◄─────────│──────────────│
│ subtask_id PK       │          │ worker_id PK │
│ task_id FK          │          │ machine_id   │
│ assigned_worker FK ─┼──────────│ machine_name │
│ name                │          │ status       │
│ description         │          │ system_info  │
│ status              │          │ resources    │
│ dependencies []     │          └──────────────┘
│ recommended_tool    │
└──────┬──────────────┘
       │
       │ 1:N
       ▼
┌─────────────────────┐
│   Checkpoint        │
│─────────────────────│
│ checkpoint_id PK    │
│ task_id FK          │
│ subtask_id FK       │
│ checkpoint_type     │
│ status              │
│ triggered_by        │
└──────┬──────────────┘
       │
       │ 1:N
       ▼
┌─────────────────────┐
│   Correction        │
│─────────────────────│
│ correction_id PK    │
│ checkpoint_id FK    │
│ feedback            │
│ corrective_action   │
└─────────────────────┘

┌─────────────────────┐
│   Evaluation        │
│─────────────────────│
│ evaluation_id PK    │
│ subtask_id FK       │
│ overall_score       │
│ dimension_scores    │
│ details             │
└─────────────────────┘

┌─────────────────────┐
│  ActivityLog        │
│─────────────────────│
│ log_id PK           │
│ task_id FK          │
│ subtask_id FK       │
│ worker_id FK        │
│ action              │
│ details             │
│ timestamp           │
└─────────────────────┘
```

### Key Tables

#### tasks
Main user-submitted tasks

**Columns:**
- `task_id`: UUID, Primary Key
- `user_id`: UUID, Foreign Key to users
- `description`: TEXT, Task description
- `status`: VARCHAR(20), Enum: pending, initializing, in_progress, checkpoint, completed, failed, cancelled
- `progress`: INTEGER, 0-100
- `checkpoint_frequency`: VARCHAR(20), Enum: low, medium, high
- `privacy_level`: VARCHAR(20), Enum: normal, sensitive
- `tool_preferences`: JSONB, Preferred AI tools
- `task_metadata`: JSONB, Flexible metadata
- `created_at`, `updated_at`, `started_at`, `completed_at`: TIMESTAMP

#### subtasks
Decomposed subtasks from tasks

**Columns:**
- `subtask_id`: UUID, Primary Key
- `task_id`: UUID, Foreign Key to tasks
- `assigned_worker`: UUID, Foreign Key to workers (nullable)
- `name`: VARCHAR(255), Subtask name
- `description`: TEXT, Detailed description
- `status`: VARCHAR(20), Enum: pending, allocated, in_progress, review, completed, failed
- `dependencies`: JSONB, Array of subtask_ids
- `recommended_tool`: VARCHAR(50), Recommended AI tool
- `complexity`: INTEGER, 1-5
- `priority`: INTEGER, Scheduling priority
- `result`: JSONB, Execution result
- `created_at`, `updated_at`, `assigned_at`, `completed_at`: TIMESTAMP

#### workers
Registered worker agents

**Columns:**
- `worker_id`: UUID, Primary Key
- `machine_id`: VARCHAR(255), Unique persistent machine ID
- `machine_name`: VARCHAR(255), Human-readable name
- `status`: VARCHAR(20), Enum: online, busy, offline, error
- `current_task`: UUID, Foreign Key to subtasks (nullable)
- `system_info`: JSONB, CPU, memory, OS info
- `resources`: JSONB, Current resource usage
- `available_tools`: JSONB, Array of tool names
- `registered_at`, `last_heartbeat`: TIMESTAMP

#### checkpoints
Human intervention checkpoints

**Columns:**
- `checkpoint_id`: UUID, Primary Key
- `task_id`: UUID, Foreign Key to tasks
- `subtask_id`: UUID, Foreign Key to subtasks (nullable)
- `checkpoint_type`: VARCHAR(50), Enum: manual, evaluation_triggered, scheduled
- `status`: VARCHAR(20), Enum: pending, resolved, skipped
- `triggered_by`: VARCHAR(50), Trigger reason
- `checkpoint_data`: JSONB, Code, evaluation results
- `created_at`, `resolved_at`: TIMESTAMP

#### evaluations
Code evaluation results

**Columns:**
- `evaluation_id`: UUID, Primary Key
- `subtask_id`: UUID, Foreign Key to subtasks
- `overall_score`: NUMERIC(4,1), Weighted average score
- `dimension_scores`: JSONB, Individual evaluator scores
- `details`: JSONB, Full evaluation details
- `needs_checkpoint`: BOOLEAN, Whether checkpoint needed
- `created_at`: TIMESTAMP

### Indexes

**Performance-critical indexes:**
- `tasks(status, created_at)`: Task listing by status
- `subtasks(task_id, status)`: Subtask queries
- `subtasks(assigned_worker, status)`: Worker task lookup
- `workers(status, last_heartbeat)`: Active worker queries
- `checkpoints(task_id, status)`: Checkpoint management
- `activity_logs(task_id, timestamp)`: Log retrieval

## Communication Protocols

### REST API

**Base URL:** `http://localhost:8000/api/v1`

**Authentication:** JWT Bearer tokens (future feature)

**Key Endpoints:**

```
# Tasks
POST   /tasks              Create new task
GET    /tasks              List tasks
GET    /tasks/{id}         Get task details
PATCH  /tasks/{id}         Update task

# Subtasks
GET    /tasks/{id}/subtasks    Get task subtasks
POST   /subtasks/{id}/result   Upload subtask result

# Workers
POST   /workers                Register worker
GET    /workers                List workers
POST   /workers/{id}/heartbeat Send heartbeat
DELETE /workers/{id}           Unregister worker

# Checkpoints
GET    /checkpoints            List checkpoints
POST   /checkpoints/{id}/resolve  Resolve checkpoint

# Evaluations
GET    /subtasks/{id}/evaluation  Get evaluation
```

### WebSocket Protocol

**Endpoint:** `ws://localhost:8000/api/v1/ws/worker/{worker_id}`

**Message Format:**

```json
{
  "type": "message_type",
  "data": { ... }
}
```

**Message Types:**

**Server → Worker:**
```json
{
  "type": "task_assignment",
  "data": {
    "subtask_id": "uuid",
    "description": "...",
    "assigned_tool": "claude_code",
    "context": {}
  }
}

{
  "type": "task_cancel",
  "data": {
    "subtask_id": "uuid",
    "reason": "user_cancelled"
  }
}

{
  "type": "ping",
  "data": {}
}
```

**Worker → Server:**
```json
{
  "type": "pong",
  "worker_id": "uuid"
}

{
  "type": "task_rejected",
  "worker_id": "uuid",
  "reason": "shutdown_in_progress",
  "subtask_id": "uuid"
}
```

### Log Streaming

**Endpoint:** `POST /api/v1/subtasks/{subtask_id}/logs`

**Payload:**
```json
{
  "log_line": "Log message",
  "log_level": "info",
  "timestamp": "2025-12-08T15:30:00Z"
}
```

## Security Architecture

### API Security

- **HTTPS in production**: TLS 1.3
- **CORS configuration**: Allowed origins only
- **Rate limiting**: Per IP and per user
- **Input validation**: Pydantic schemas
- **SQL injection prevention**: ORM with parameterized queries

### Worker Security

- **Machine ID verification**: Persistent unique machine IDs
- **API key authentication**: For AI tool access
- **Privacy level enforcement**: Sensitive tasks on trusted workers only
- **Log sanitization**: Remove sensitive data from logs

### Data Security

- **Database encryption at rest**: PostgreSQL native encryption
- **Redis security**: Password authentication, TLS
- **Environment variables**: Secrets in .env files
- **Secret scanning**: Pre-commit hooks with detect-secrets

## Scalability Considerations

### Horizontal Scaling

**Backend:**
- Stateless API servers
- Load balancer (Nginx/HAProxy)
- Multiple FastAPI instances
- Shared PostgreSQL and Redis

**Workers:**
- Add more worker machines
- Auto-scaling based on task queue depth
- Geographically distributed workers

### Vertical Scaling

- Increase CPU/memory for backend
- PostgreSQL optimization (indexes, query tuning)
- Redis clustering for high throughput

### Performance Optimizations

**Database:**
- Connection pooling (SQLAlchemy)
- Query optimization (EXPLAIN ANALYZE)
- Materialized views for reporting
- Partitioning for large tables (activity_logs)

**Caching:**
- Redis caching layer
- Task status cache (TTL: 60s)
- Worker status cache (TTL: 30s)
- API response caching (conditional)

**Async Processing:**
- Background task queue (future: Celery)
- Async/await throughout backend
- Non-blocking I/O operations

### Monitoring

- **Metrics**: Prometheus + Grafana
- **Logging**: Structured logging with structlog
- **Tracing**: OpenTelemetry (future)
- **Alerting**: Alert on worker failures, API errors, resource thresholds

## Conclusion

This architecture provides a solid foundation for a distributed multi-agent orchestration platform with:

- **Scalability**: Horizontal and vertical scaling capabilities
- **Reliability**: Graceful error handling and retry mechanisms
- **Extensibility**: Pluggable evaluators and AI tools
- **Observability**: Comprehensive logging and monitoring
- **Security**: Multi-layer security controls

For more information:
- [Development Setup](./development.md)
- [Contributing Guide](./contributing.md)
- [Adding AI Tools](./adding-ai-tools.md)
- [Extending Evaluation](./extending-evaluation.md)
