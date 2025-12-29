# Sprint 1 Planning - Multi-Agent on the Web

**Sprint Duration:** 2 weeks (10 working days)
**Sprint Goal:** 建立完整的項目基礎設施，包括數據庫、API 框架、Worker Agent 骨架、開發環境，為後續開發奠定基礎
**Team Velocity:** 40-50 Story Points (estimated for single developer)
**Sprint Dates:** 2025-11-12 to 2025-11-25

---

## Sprint Scope

**Selected Stories from Epic 1: Foundation & Infrastructure**

本 Sprint 將完成 Epic 1 的所有 7 個 User Stories：

- ✅ Story 1.1: 項目初始化與開發環境配置 (5 SP)
- ✅ Story 1.2: PostgreSQL 數據庫設計與 ORM 配置 (8 SP)
- ✅ Story 1.3: Redis 數據結構設計與連接配置 (5 SP)
- ✅ Story 1.4: FastAPI 後端框架搭建 (8 SP)
- ✅ Story 1.5: Worker Agent Python SDK 基礎框架 (5 SP)
- ✅ Story 1.6: Docker Compose 多容器編排配置 (5 SP)
- ✅ Story 1.7: CI/CD 基礎配置 (5 SP)

**Total Story Points:** 41 SP

---

## Sprint Backlog - Detailed Task Breakdown

### Story 1.1: 項目初始化與開發環境配置 (5 SP)

**Story Owner:** Developer
**Priority:** P0 (Blocker)

#### Tasks:

**Task 1.1.1: 創建 Monorepo 項目結構** (2 hours)
- [ ] 創建根目錄和主要模塊目錄
  ```
  multi-agent-web/
  ├── backend/
  ├── frontend/
  ├── worker-agent/
  ├── docs/
  ├── docker/
  └── scripts/
  ```
- [ ] 創建 README.md 主文件
- [ ] 創建 .gitignore（Python, Flutter, Node）
- [ ] 初始化 Git 倉庫
- **Definition of Done:** 目錄結構建立，Git 初始化完成

**Task 1.1.2: 配置 Python Backend 環境** (2 hours)
- [ ] 在 `backend/` 創建 Python 項目結構
  ```
  backend/
  ├── src/
  │   ├── api/
  │   ├── services/
  │   ├── models/
  │   ├── repositories/
  │   └── main.py
  ├── tests/
  ├── alembic/
  ├── pyproject.toml
  ├── requirements.txt
  └── README.md
  ```
- [ ] 初始化 Poetry 或創建 requirements.txt
  ```
  fastapi==0.104.1
  uvicorn[standard]==0.24.0
  pydantic==2.5.0
  pydantic-settings==2.1.0
  sqlalchemy[asyncio]==2.0.23
  asyncpg==0.29.0
  alembic==1.13.0
  redis[hiredis]==5.0.1
  pytest==7.4.3
  pytest-asyncio==0.21.1
  black==23.12.0
  isort==5.13.0
  pylint==3.0.3
  ```
- [ ] 創建 .env.example
- [ ] 配置 Python 虛擬環境
- **Definition of Done:** Poetry/venv 配置完成，依賴可安裝

**Task 1.1.3: 配置 Flutter Frontend 環境** (2 hours)
- [ ] 使用 Flutter CLI 創建項目
  ```bash
  flutter create --org com.multiagent --platforms=web,linux,windows,macos multi_agent_flutter
  ```
- [ ] 配置項目結構
  ```
  frontend/
  ├── lib/
  │   ├── main.dart
  │   ├── screens/
  │   ├── widgets/
  │   ├── providers/
  │   ├── models/
  │   ├── services/
  │   └── utils/
  ├── test/
  ├── pubspec.yaml
  └── README.md
  ```
- [ ] 添加核心依賴到 pubspec.yaml
  ```yaml
  dependencies:
    flutter_riverpod: ^2.4.0
    go_router: ^12.0.0
    dio: ^5.4.0
    web_socket_channel: ^2.4.0
  ```
- [ ] 運行 `flutter pub get`
- **Definition of Done:** Flutter 項目可運行，依賴安裝成功

**Task 1.1.4: 配置 Worker Agent 環境** (1 hour)
- [ ] 創建 worker-agent/ 項目結構
  ```
  worker-agent/
  ├── src/
  │   ├── agent/
  │   ├── tools/
  │   └── main.py
  ├── config/
  │   └── agent.yaml.example
  ├── tests/
  ├── requirements.txt
  └── README.md
  ```
- [ ] 創建 requirements.txt
  ```
  httpx==0.25.2
  websockets==12.0
  psutil==5.9.6
  pyyaml==6.0.1
  anthropic==0.8.0
  google-generativeai==0.3.0
  structlog==23.2.0
  ```
- **Definition of Done:** Worker Agent 項目結構建立

**Task 1.1.5: 配置 Git Hooks 和開發工具** (1 hour)
- [ ] 安裝 pre-commit
  ```bash
  pip install pre-commit
  ```
- [ ] 創建 .pre-commit-config.yaml
  ```yaml
  repos:
    - repo: https://github.com/psf/black
      rev: 23.12.0
      hooks:
        - id: black
    - repo: https://github.com/pycqa/isort
      rev: 5.13.0
      hooks:
        - id: isort
    - repo: https://github.com/pycqa/pylint
      rev: v3.0.3
      hooks:
        - id: pylint
  ```
- [ ] 運行 `pre-commit install`
- [ ] 創建 Makefile 或 scripts/dev.sh 包含常用命令
- **Definition of Done:** Pre-commit hooks 可運行

**Task 1.1.6: 創建文檔和配置文件** (1 hour)
- [ ] 創建 CONTRIBUTING.md（開發指南）
- [ ] 創建 docs/architecture.md（已存在，確認路徑）
- [ ] 創建 .vscode/settings.json（推薦配置）
- [ ] 創建 .editorconfig（統一編輯器配置）
- **Definition of Done:** 文檔完整，新開發者可參考

---

### Story 1.2: PostgreSQL 數據庫設計與 ORM 配置 (8 SP)

**Story Owner:** Developer
**Priority:** P0 (Blocker)

#### Tasks:

**Task 1.2.1: 設計數據庫 Schema** (2 hours)
- [ ] 根據架構文檔（architecture.md section 5.1）創建 ERD
- [ ] 確認所有表的欄位、類型、約束
- [ ] 設計索引策略
- [ ] 確認外鍵關聯
- **Definition of Done:** Schema 設計完成，有清晰的 ERD 圖

**Task 1.2.2: 配置 SQLAlchemy 與 Alembic** (2 hours)
- [ ] 創建 `backend/src/database.py`
  ```python
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
  from sqlalchemy.orm import sessionmaker, declarative_base

  Base = declarative_base()
  engine = create_async_engine(DATABASE_URL, echo=True)
  AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

  async def get_db():
      async with AsyncSessionLocal() as session:
          yield session
  ```
- [ ] 初始化 Alembic
  ```bash
  cd backend
  alembic init alembic
  ```
- [ ] 配置 alembic.ini 和 alembic/env.py
- **Definition of Done:** SQLAlchemy 和 Alembic 配置完成

**Task 1.2.3: 創建 ORM 模型 - Users Table** (1 hour)
- [ ] 創建 `backend/src/models/user.py`
  ```python
  from sqlalchemy import Column, String, DateTime
  from sqlalchemy.dialects.postgresql import UUID
  import uuid
  from datetime import datetime

  class User(Base):
      __tablename__ = "users"

      user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      username = Column(String(100), unique=True, nullable=False, index=True)
      email = Column(String(255), unique=True, nullable=False, index=True)
      password_hash = Column(String(255), nullable=False)
      created_at = Column(DateTime, default=datetime.utcnow)
  ```
- **Definition of Done:** User 模型定義完成

**Task 1.2.4: 創建 ORM 模型 - Workers Table** (1 hour)
- [ ] 創建 `backend/src/models/worker.py`
  ```python
  from sqlalchemy import Column, String, DateTime, Float, JSON
  from sqlalchemy.dialects.postgresql import UUID

  class Worker(Base):
      __tablename__ = "workers"

      worker_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      machine_id = Column(String(100), unique=True, nullable=False, index=True)
      machine_name = Column(String(100), nullable=False)
      status = Column(String(20), default="offline", index=True)
      system_info = Column(JSON, nullable=False)
      tools = Column(JSON, nullable=False)
      cpu_percent = Column(Float)
      memory_percent = Column(Float)
      disk_percent = Column(Float)
      last_heartbeat = Column(DateTime, index=True)
      registered_at = Column(DateTime, default=datetime.utcnow)
  ```
- **Definition of Done:** Worker 模型定義完成

**Task 1.2.5: 創建 ORM 模型 - Tasks & Subtasks Tables** (2 hours)
- [ ] 創建 `backend/src/models/task.py`
  ```python
  class Task(Base):
      __tablename__ = "tasks"

      task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
      description = Column(Text, nullable=False)
      requirements = Column(JSON)
      status = Column(String(20), default="pending", index=True)
      progress = Column(Integer, default=0)
      checkpoint_frequency = Column(String(20), default="medium")
      privacy_level = Column(String(20), default="normal")
      tool_preferences = Column(JSON)
      metadata = Column(JSON)
      version = Column(Integer, default=0)  # For optimistic locking
      created_at = Column(DateTime, default=datetime.utcnow)
      updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
      completed_at = Column(DateTime)

      # Relationships
      subtasks = relationship("Subtask", back_populates="task")

  class Subtask(Base):
      __tablename__ = "subtasks"

      subtask_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.task_id", ondelete="CASCADE"), index=True)
      name = Column(String(255), nullable=False)
      description = Column(Text, nullable=False)
      status = Column(String(20), default="pending", index=True)
      progress = Column(Integer, default=0)
      dependencies = Column(JSON, default=[])
      recommended_tool = Column(String(50))
      assigned_worker = Column(UUID(as_uuid=True), ForeignKey("workers.worker_id"))
      assigned_tool = Column(String(50))
      complexity = Column(Integer)
      output = Column(JSON)
      error = Column(Text)
      evaluation_score = Column(Float)
      subtask_type = Column(String(20), default="task")  # task, review, correction
      review_target_id = Column(UUID(as_uuid=True), ForeignKey("subtasks.subtask_id"))
      review_cycle_count = Column(Integer, default=0)
      review_result = Column(JSON)
      created_at = Column(DateTime, default=datetime.utcnow)

      # Relationships
      task = relationship("Task", back_populates="subtasks")
  ```
- **Definition of Done:** Task 和 Subtask 模型定義完成

**Task 1.2.6: 創建 ORM 模型 - Checkpoints, Evaluations, Reviews Tables** (2 hours)
- [ ] 創建 `backend/src/models/checkpoint.py`
- [ ] 創建 `backend/src/models/evaluation.py`
- [ ] 創建 `backend/src/models/review.py`
- [ ] 創建 `backend/src/models/activity_log.py`
- [ ] 創建 `backend/src/models/correction.py`
- **Definition of Done:** 所有輔助表模型定義完成

**Task 1.2.7: 創建並執行數據庫遷移** (2 hours)
- [ ] 自動生成遷移腳本
  ```bash
  alembic revision --autogenerate -m "Initial schema"
  ```
- [ ] 檢查生成的遷移腳本，確認正確性
- [ ] 執行遷移
  ```bash
  alembic upgrade head
  ```
- [ ] 驗證數據庫表已創建
  ```bash
  psql -U postgres -d multi_agent_db -c "\dt"
  ```
- [ ] 創建種子數據腳本（可選）
- **Definition of Done:** 數據庫遷移成功，所有表存在

**Task 1.2.8: 創建 Repository 層基礎類** (2 hours)
- [ ] 創建 `backend/src/repositories/base_repository.py`
  ```python
  from typing import Generic, TypeVar, Type, List, Optional
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select

  T = TypeVar('T')

  class BaseRepository(Generic[T]):
      def __init__(self, model: Type[T], session: AsyncSession):
          self.model = model
          self.session = session

      async def get_by_id(self, id: UUID) -> Optional[T]:
          result = await self.session.execute(
              select(self.model).where(self.model.id == id)
          )
          return result.scalar_one_or_none()

      async def get_all(self) -> List[T]:
          result = await self.session.execute(select(self.model))
          return result.scalars().all()

      async def create(self, **kwargs) -> T:
          instance = self.model(**kwargs)
          self.session.add(instance)
          await self.session.commit()
          await self.session.refresh(instance)
          return instance
  ```
- [ ] 創建具體 Repository：TaskRepository, WorkerRepository, SubtaskRepository
- **Definition of Done:** Repository 層基礎完成，可執行 CRUD

---

### Story 1.3: Redis 數據結構設計與連接配置 (5 SP)

**Story Owner:** Developer
**Priority:** P0 (Blocker)

#### Tasks:

**Task 1.3.1: 設計 Redis Key Schema** (1 hour)
- [ ] 文檔化 Redis Key 結構（在 architecture.md 或單獨文件）
  ```
  # Worker Status
  workers:{worker_id}:status → "online" | "offline" | "busy"
  workers:{worker_id}:current_task → task_id (UUID)
  workers:online → Set of worker_ids

  # Task Status
  tasks:{task_id}:status → "pending" | "in_progress" | "checkpoint_pending" | "completed"
  tasks:{task_id}:progress → Integer (0-100)

  # Task Queue
  task_queue:pending → List of subtask_ids

  # WebSocket Connections
  websocket:connections → Set of client_ids
  websocket:subscriptions:{client_id} → Set of task_ids

  # Pub/Sub Channels
  events:task_update → Publish task updates
  events:worker_update → Publish worker status changes
  ```
- **Definition of Done:** Redis Key Schema 文檔完成

**Task 1.3.2: 配置 Redis 連接池** (1 hour)
- [ ] 創建 `backend/src/redis_client.py`
  ```python
  import redis.asyncio as redis
  from typing import Optional

  class RedisClient:
      def __init__(self, url: str):
          self.pool = redis.ConnectionPool.from_url(url, decode_responses=True)
          self.client: Optional[redis.Redis] = None

      async def connect(self):
          self.client = redis.Redis(connection_pool=self.pool)
          await self.client.ping()

      async def close(self):
          if self.client:
              await self.client.close()
              await self.pool.disconnect()
  ```
- [ ] 在 FastAPI startup 事件中初始化連接
- **Definition of Done:** Redis 連接池配置完成

**Task 1.3.3: 實現 Redis 工具類 - Worker Status** (1 hour)
- [ ] 創建 `backend/src/services/redis_service.py`
  ```python
  class RedisService:
      def __init__(self, redis_client: redis.Redis):
          self.redis = redis_client

      async def set_worker_status(self, worker_id: UUID, status: str):
          await self.redis.setex(
              f"workers:{worker_id}:status",
              120,  # TTL 120 seconds
              status
          )
          if status == "online":
              await self.redis.sadd("workers:online", str(worker_id))
          else:
              await self.redis.srem("workers:online", str(worker_id))

      async def get_worker_status(self, worker_id: UUID) -> Optional[str]:
          return await self.redis.get(f"workers:{worker_id}:status")

      async def get_online_workers(self) -> List[str]:
          return await self.redis.smembers("workers:online")
  ```
- **Definition of Done:** Worker Status Redis 操作可用

**Task 1.3.4: 實現 Redis 工具類 - Task Status** (1 hour)
- [ ] 添加 Task Status 方法到 RedisService
  ```python
  async def set_task_status(self, task_id: UUID, status: str):
      await self.redis.set(f"tasks:{task_id}:status", status)

  async def set_task_progress(self, task_id: UUID, progress: int):
      await self.redis.set(f"tasks:{task_id}:progress", progress)

  async def get_task_status(self, task_id: UUID) -> Optional[str]:
      return await self.redis.get(f"tasks:{task_id}:status")
  ```
- **Definition of Done:** Task Status Redis 操作可用

**Task 1.3.5: 實現 Redis Pub/Sub 基礎** (2 hours)
- [ ] 添加 Pub/Sub 方法到 RedisService
  ```python
  async def publish_event(self, channel: str, message: dict):
      await self.redis.publish(channel, json.dumps(message))

  async def subscribe(self, *channels):
      pubsub = self.redis.pubsub()
      await pubsub.subscribe(*channels)
      return pubsub
  ```
- [ ] 創建測試腳本驗證 Pub/Sub 功能
- **Definition of Done:** Pub/Sub 基礎功能可用

**Task 1.3.6: 配置 Redis 在 Docker Compose** (30 minutes)
- [ ] 已在 Task 1.1 中完成，確認配置正確
- [ ] 驗證 Redis 可連接
- **Definition of Done:** Redis 容器運行正常

---

### Story 1.4: FastAPI 後端框架搭建 (8 SP)

**Story Owner:** Developer
**Priority:** P0 (Blocker)

#### Tasks:

**Task 1.4.1: 創建 FastAPI 主應用** (2 hours)
- [ ] 創建 `backend/src/main.py`
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from contextlib import asynccontextmanager

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # Startup
      await database.connect()
      await redis_client.connect()
      yield
      # Shutdown
      await database.disconnect()
      await redis_client.close()

  app = FastAPI(
      title="Multi-Agent on the Web API",
      version="1.0.0",
      lifespan=lifespan
  )

  # CORS
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000", "http://localhost:8080"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- **Definition of Done:** FastAPI 應用可啟動

**Task 1.4.2: 配置環境變量管理** (1 hour)
- [ ] 創建 `backend/src/config.py`
  ```python
  from pydantic_settings import BaseSettings

  class Settings(BaseSettings):
      DATABASE_URL: str
      REDIS_URL: str
      SECRET_KEY: str
      DEBUG: bool = False

      class Config:
          env_file = ".env"

  settings = Settings()
  ```
- [ ] 創建 .env.example
- **Definition of Done:** 環境變量可讀取

**Task 1.4.3: 配置日誌系統** (1 hour)
- [ ] 選擇日誌庫（structlog 或 loguru）
- [ ] 配置日誌格式和等級
  ```python
  import structlog

  structlog.configure(
      processors=[
          structlog.processors.TimeStamper(fmt="iso"),
          structlog.processors.JSONRenderer()
      ],
      logger_factory=structlog.PrintLoggerFactory(),
  )

  logger = structlog.get_logger()
  ```
- **Definition of Done:** 日誌可正常輸出

**Task 1.4.4: 創建健康檢查端點** (1 hour)
- [ ] 創建 `backend/src/api/v1/health.py`
  ```python
  from fastapi import APIRouter, Depends
  from sqlalchemy.ext.asyncio import AsyncSession

  router = APIRouter()

  @router.get("/health")
  async def health_check(db: AsyncSession = Depends(get_db)):
      # Check database
      await db.execute("SELECT 1")

      # Check Redis
      await redis_client.ping()

      return {
          "status": "healthy",
          "database": "connected",
          "redis": "connected"
      }
  ```
- [ ] 註冊路由到主應用
- **Definition of Done:** /health 端點返回 200

**Task 1.4.5: 配置依賴注入** (2 hours)
- [ ] 創建依賴注入函數
  ```python
  # backend/src/dependencies.py

  async def get_db() -> AsyncSession:
      async with AsyncSessionLocal() as session:
          yield session

  async def get_redis() -> redis.Redis:
      return redis_client.client

  async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
      # JWT validation (placeholder)
      pass
  ```
- [ ] 在路由中使用依賴注入
- **Definition of Done:** 依賴注入可用

**Task 1.4.6: 配置 API 版本化** (1 hour)
- [ ] 創建 API v1 路由結構
  ```
  backend/src/api/
  ├── __init__.py
  └── v1/
      ├── __init__.py
      ├── health.py
      ├── workers.py (placeholder)
      ├── tasks.py (placeholder)
      └── checkpoints.py (placeholder)
  ```
- [ ] 在 main.py 中註冊 v1 路由
  ```python
  from api.v1 import health, workers, tasks

  app.include_router(health.router, prefix="/api/v1", tags=["health"])
  app.include_router(workers.router, prefix="/api/v1", tags=["workers"])
  app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
  ```
- **Definition of Done:** API 版本化結構建立

**Task 1.4.7: 配置 OpenAPI 文檔** (30 minutes)
- [ ] 確認 FastAPI 自動生成的 OpenAPI docs 可訪問
  - Swagger UI: http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc
- [ ] 自定義 OpenAPI metadata
- **Definition of Done:** API 文檔可訪問

---

### Story 1.5: Worker Agent Python SDK 基礎框架 (5 SP)

**Story Owner:** Developer
**Priority:** P0 (Blocker)

#### Tasks:

**Task 1.5.1: 創建 WorkerAgent 主類** (2 hours)
- [ ] 創建 `worker-agent/src/agent/core.py`
  ```python
  import asyncio
  from typing import Dict, List
  from uuid import UUID

  class WorkerAgent:
      def __init__(self, config: dict):
          self.config = config
          self.worker_id: Optional[UUID] = None
          self.machine_id = self._get_or_create_machine_id()
          self.connection_manager = ConnectionManager(config)
          self.resource_monitor = ResourceMonitor()
          self.task_executor = TaskExecutor()
          self.tools: Dict[str, BaseTool] = {}

      async def start(self):
          logger.info("Starting Worker Agent...")

          # 1. Register with backend
          self.worker_id = await self.connection_manager.register(
              machine_id=self.machine_id,
              machine_name=self.config["machine_name"],
              system_info=self._get_system_info(),
              tools=list(self.tools.keys())
          )

          # 2. Start heartbeat loop
          asyncio.create_task(self._heartbeat_loop())

          # 3. Start task listener
          asyncio.create_task(self._task_listener())

          logger.info(f"Worker Agent started (worker_id={self.worker_id})")

      def _get_or_create_machine_id(self) -> str:
          machine_id_file = Path.home() / ".multi_agent_worker_id"
          if machine_id_file.exists():
              return machine_id_file.read_text().strip()
          else:
              machine_id = str(uuid.uuid4())
              machine_id_file.write_text(machine_id)
              return machine_id
  ```
- **Definition of Done:** WorkerAgent 類可初始化

**Task 1.5.2: 創建 ConnectionManager 類** (2 hours)
- [ ] 創建 `worker-agent/src/agent/connection.py`
  ```python
  import httpx
  import websockets

  class ConnectionManager:
      def __init__(self, config: dict):
          self.backend_url = config["backend_url"]
          self.client = httpx.AsyncClient(base_url=self.backend_url)
          self.ws = None

      async def register(self, machine_id: str, machine_name: str, system_info: dict, tools: List[str]) -> UUID:
          response = await self.client.post(
              "/api/v1/workers/register",
              json={
                  "machine_id": machine_id,
                  "machine_name": machine_name,
                  "system_info": system_info,
                  "tools": tools
              }
          )
          response.raise_for_status()
          data = response.json()
          return UUID(data["worker_id"])

      async def send_heartbeat(self, worker_id: UUID, resources: dict):
          response = await self.client.post(
              f"/api/v1/workers/{worker_id}/heartbeat",
              json=resources
          )
          response.raise_for_status()
          return response.json()
  ```
- **Definition of Done:** ConnectionManager 可發送 HTTP 請求

**Task 1.5.3: 創建 ResourceMonitor 類** (1 hour)
- [ ] 創建 `worker-agent/src/agent/monitor.py`
  ```python
  import psutil

  class ResourceMonitor:
      def get_resources(self) -> dict:
          return {
              "cpu_percent": psutil.cpu_percent(interval=1),
              "memory_percent": psutil.virtual_memory().percent,
              "disk_percent": psutil.disk_usage('/').percent
          }

      def get_system_info(self) -> dict:
          return {
              "os": platform.system(),
              "os_version": platform.version(),
              "cpu_count": psutil.cpu_count(),
              "memory_total": psutil.virtual_memory().total,
              "python_version": platform.python_version()
          }
  ```
- **Definition of Done:** ResourceMonitor 可獲取系統資源

**Task 1.5.4: 創建 TaskExecutor 基礎類** (1 hour)
- [ ] 創建 `worker-agent/src/agent/executor.py`
  ```python
  class TaskExecutor:
      def __init__(self):
          self.tools: Dict[str, BaseTool] = {}

      def register_tool(self, name: str, tool: BaseTool):
          self.tools[name] = tool

      async def execute_task(self, subtask: dict) -> dict:
          tool_name = subtask["assigned_tool"]
          if tool_name not in self.tools:
              raise ValueError(f"Tool {tool_name} not available")

          tool = self.tools[tool_name]
          result = await tool.execute(
              instructions=subtask["description"],
              context=subtask.get("context", {})
          )
          return result
  ```
- **Definition of Done:** TaskExecutor 基礎架構完成

**Task 1.5.5: 創建配置文件加載** (1 hour)
- [ ] 創建 `worker-agent/config/agent.yaml.example`
  ```yaml
  backend_url: "http://localhost:8000"
  machine_name: "Development Machine"
  heartbeat_interval: 30
  tools:
    - claude_code
    - gemini_cli
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
  gemini:
    api_key: "${GOOGLE_API_KEY}"
  ```
- [ ] 創建配置加載函數
  ```python
  import yaml
  import os

  def load_config(config_path: str) -> dict:
      with open(config_path, 'r') as f:
          config = yaml.safe_load(f)

      # Environment variable substitution
      config = _substitute_env_vars(config)
      return config
  ```
- **Definition of Done:** 配置文件可加載

**Task 1.5.6: 創建 Worker Agent CLI 入口** (1 hour)
- [ ] 創建 `worker-agent/src/main.py`
  ```python
  import asyncio
  import argparse
  from agent.core import WorkerAgent
  from config import load_config

  async def main():
      parser = argparse.ArgumentParser(description="Multi-Agent Worker")
      parser.add_argument("--config", default="config/agent.yaml", help="Config file path")
      args = parser.parse_args()

      config = load_config(args.config)
      agent = WorkerAgent(config)

      try:
          await agent.start()
          # Keep running
          await asyncio.Event().wait()
      except KeyboardInterrupt:
          logger.info("Shutting down...")
          await agent.stop()

  if __name__ == "__main__":
      asyncio.run(main())
  ```
- [ ] 測試 Worker Agent 可啟動（無需實際功能）
- **Definition of Done:** Worker Agent CLI 可運行

---

### Story 1.6: Docker Compose 多容器編排配置 (5 SP)

**Story Owner:** Developer
**Priority:** P1

#### Tasks:

**Task 1.6.1: 創建 Docker Compose 配置** (2 hours)
- [ ] 創建 `docker-compose.yml`
  ```yaml
  version: '3.9'

  services:
    postgres:
      image: postgres:15-alpine
      container_name: multi_agent_postgres
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

    redis:
      image: redis:7-alpine
      container_name: multi_agent_redis
      ports:
        - "6379:6379"
      volumes:
        - redis_data:/data
      healthcheck:
        test: ["CMD", "redis-cli", "ping"]
        interval: 10s
        timeout: 5s
        retries: 5

    backend:
      build:
        context: ./backend
        dockerfile: Dockerfile.dev
      container_name: multi_agent_backend
      environment:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres_dev_password@postgres:5432/multi_agent_db
        REDIS_URL: redis://redis:6379/0
        DEBUG: "true"
      ports:
        - "8000:8000"
      volumes:
        - ./backend:/app
      depends_on:
        postgres:
          condition: service_healthy
        redis:
          condition: service_healthy
      command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  volumes:
    postgres_data:
    redis_data:
  ```
- **Definition of Done:** docker-compose.yml 創建完成

**Task 1.6.2: 創建 Backend Dockerfile** (1 hour)
- [ ] 創建 `backend/Dockerfile.dev`
  ```dockerfile
  FROM python:3.11-slim

  WORKDIR /app

  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      postgresql-client \
      && rm -rf /var/lib/apt/lists/*

  # Install Python dependencies
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  # Copy application code
  COPY . .

  EXPOSE 8000

  CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
  ```
- **Definition of Done:** Backend Dockerfile 可構建

**Task 1.6.3: 創建數據庫初始化腳本** (1 hour)
- [ ] 創建 `docker/init-db.sh`
  ```bash
  #!/bin/bash
  set -e

  echo "Waiting for PostgreSQL to be ready..."
  until pg_isready -h postgres -U postgres; do
    sleep 1
  done

  echo "Running database migrations..."
  cd /app
  alembic upgrade head

  echo "Database initialization complete!"
  ```
- [ ] 在 docker-compose.yml 中配置初始化腳本
- **Definition of Done:** 數據庫初始化腳本可運行

**Task 1.6.4: 創建 Makefile 便捷命令** (1 hour)
- [ ] 創建 `Makefile`
  ```makefile
  .PHONY: help up down logs shell-backend shell-worker test clean

  help:
  	@echo "Available commands:"
  	@echo "  make up          - Start all services"
  	@echo "  make down        - Stop all services"
  	@echo "  make logs        - View logs"
  	@echo "  make shell-backend - Shell into backend container"
  	@echo "  make test        - Run tests"
  	@echo "  make clean       - Clean up volumes"

  up:
  	docker-compose up -d
  	@echo "Services started. Backend: http://localhost:8000"

  down:
  	docker-compose down

  logs:
  	docker-compose logs -f

  shell-backend:
  	docker-compose exec backend bash

  test:
  	docker-compose exec backend pytest

  clean:
  	docker-compose down -v
  	rm -rf backend/__pycache__
  	rm -rf backend/.pytest_cache
  ```
- **Definition of Done:** Makefile 命令可用

**Task 1.6.5: 測試 Docker Compose 編排** (1 hour)
- [ ] 運行 `docker-compose up`
- [ ] 驗證所有容器啟動成功
  ```bash
  docker-compose ps
  ```
- [ ] 驗證後端可訪問：http://localhost:8000/health
- [ ] 驗證數據庫遷移執行成功
- [ ] 驗證代碼熱重載工作
- **Definition of Done:** Docker Compose 完全正常運作

---

### Story 1.7: CI/CD 基礎配置 (5 SP)

**Story Owner:** Developer
**Priority:** P2

#### Tasks:

**Task 1.7.1: 創建 GitHub Actions Workflow** (2 hours)
- [ ] 創建 `.github/workflows/ci.yml`
  ```yaml
  name: CI

  on:
    push:
      branches: [ main, develop ]
    pull_request:
      branches: [ main, develop ]

  jobs:
    lint:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - uses: actions/setup-python@v4
          with:
            python-version: '3.11'
        - name: Install dependencies
          run: |
            cd backend
            pip install -r requirements.txt
        - name: Run black
          run: cd backend && black --check src/
        - name: Run isort
          run: cd backend && isort --check src/
        - name: Run pylint
          run: cd backend && pylint src/

    test:
      runs-on: ubuntu-latest
      services:
        postgres:
          image: postgres:15
          env:
            POSTGRES_PASSWORD: postgres
            POSTGRES_DB: test_db
          options: >-
            --health-cmd pg_isready
            --health-interval 10s
            --health-timeout 5s
            --health-retries 5
          ports:
            - 5432:5432
        redis:
          image: redis:7
          options: >-
            --health-cmd "redis-cli ping"
            --health-interval 10s
            --health-timeout 5s
            --health-retries 5
          ports:
            - 6379:6379
      steps:
        - uses: actions/checkout@v3
        - uses: actions/setup-python@v4
          with:
            python-version: '3.11'
        - name: Install dependencies
          run: |
            cd backend
            pip install -r requirements.txt
        - name: Run tests
          env:
            DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_db
            REDIS_URL: redis://localhost:6379/0
          run: cd backend && pytest --cov=src tests/
        - name: Upload coverage
          uses: codecov/codecov-action@v3
          with:
            file: ./backend/coverage.xml
  ```
- **Definition of Done:** GitHub Actions workflow 配置完成

**Task 1.7.2: 配置測試框架** (2 hours)
- [ ] 在 backend/ 創建 pytest 配置
  ```ini
  # backend/pytest.ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  python_classes = Test*
  python_functions = test_*
  addopts =
      --verbose
      --cov=src
      --cov-report=term-missing
      --cov-report=xml
  asyncio_mode = auto
  ```
- [ ] 創建測試基礎結構
  ```
  backend/tests/
  ├── __init__.py
  ├── conftest.py
  ├── unit/
  │   ├── __init__.py
  │   └── test_database.py
  └── integration/
      ├── __init__.py
      └── test_api_health.py
  ```
- [ ] 創建 conftest.py
  ```python
  import pytest
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
  from sqlalchemy.orm import sessionmaker

  @pytest.fixture
  async def db_session():
      engine = create_async_engine("sqlite+aiosqlite:///:memory:")
      AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)
      async with AsyncSessionLocal() as session:
          yield session
  ```
- **Definition of Done:** pytest 可運行

**Task 1.7.3: 創建基礎單元測試** (2 hours)
- [ ] 創建 `backend/tests/unit/test_database.py`
  ```python
  import pytest
  from src.models.worker import Worker

  @pytest.mark.asyncio
  async def test_create_worker(db_session):
      worker = Worker(
          machine_id="test-machine-1",
          machine_name="Test Machine",
          system_info={"os": "Linux"},
          tools=["claude_code"]
      )
      db_session.add(worker)
      await db_session.commit()

      assert worker.worker_id is not None
      assert worker.status == "offline"
  ```
- [ ] 創建 `backend/tests/integration/test_api_health.py`
  ```python
  from fastapi.testclient import TestClient
  from src.main import app

  client = TestClient(app)

  def test_health_check():
      response = client.get("/api/v1/health")
      assert response.status_code == 200
      assert response.json()["status"] == "healthy"
  ```
- **Definition of Done:** 基礎測試可運行並通過

**Task 1.7.4: 配置代碼覆蓋率報告** (1 hour)
- [ ] 配置 codecov 或 coveralls
- [ ] 在 README.md 添加覆蓋率徽章
- [ ] 設置最低覆蓋率閾值（例如 80%）
- **Definition of Done:** 代碼覆蓋率報告可生成

---

## Sprint Goal Verification

**Sprint 完成後，應達到以下目標：**

✅ **項目結構完整**
- Monorepo 結構清晰，包含 backend, frontend, worker-agent
- 所有配置文件就緒（.env, docker-compose.yml, Makefile）

✅ **數據庫完全就緒**
- PostgreSQL 表全部創建（users, workers, tasks, subtasks, checkpoints, evaluations, reviews）
- SQLAlchemy ORM 模型定義完成
- Alembic 遷移可運行

✅ **FastAPI 後端框架運行**
- 後端可啟動並監聽 8000 端口
- Health check 端點可訪問
- 依賴注入配置完成
- API 文檔可訪問（/docs）

✅ **Redis 連接配置**
- Redis 數據結構設計完成
- RedisService 可讀寫 Worker 和 Task 狀態
- Pub/Sub 基礎可用

✅ **Worker Agent 骨架完成**
- WorkerAgent 類可初始化
- ConnectionManager, ResourceMonitor, TaskExecutor 基礎類完成
- Worker Agent CLI 可運行

✅ **Docker Compose 環境就緒**
- 一鍵啟動：`make up` 或 `docker-compose up`
- 所有容器運行正常
- 代碼熱重載工作

✅ **CI/CD 基礎配置**
- GitHub Actions workflow 配置
- 自動運行 linting 和測試
- 代碼覆蓋率報告

---

## Definition of Done (DoD)

每個 Story/Task 完成的標準：

### Code Quality
- [ ] 代碼通過 black, isort, pylint 檢查
- [ ] 無明顯的代碼異味（code smells）
- [ ] 遵循 PEP 8 和項目編碼規範

### Testing
- [ ] 單元測試編寫並通過（覆蓋率 > 80%）
- [ ] 整合測試（如適用）編寫並通過
- [ ] 手動測試通過

### Documentation
- [ ] 代碼包含清晰的註釋和 docstrings
- [ ] README 或技術文檔更新
- [ ] API 文檔（OpenAPI）自動生成

### Review
- [ ] 代碼已自我審查
- [ ] 符合架構設計（architecture.md）

### Deployment
- [ ] 在本地 Docker 環境中測試通過
- [ ] 環境變量配置正確
- [ ] CI/CD pipeline 通過

---

## Risk Management

### 已識別風險

**Risk 1: Docker 環境配置複雜度**
- **Impact:** HIGH
- **Probability:** MEDIUM
- **Mitigation:** 提供詳細的 Makefile 和文檔，測試多平台（Windows/Mac/Linux）

**Risk 2: SQLAlchemy 2.x 異步語法不熟悉**
- **Impact:** MEDIUM
- **Probability:** HIGH
- **Mitigation:** 參考官方文檔和範例，編寫單元測試驗證

**Risk 3: Redis Pub/Sub 實作複雜**
- **Impact:** MEDIUM
- **Probability:** MEDIUM
- **Mitigation:** 先實現基礎功能，複雜的 Pub/Sub 可在 Sprint 2 優化

---

## Dependencies & Blockers

### External Dependencies
- Docker Desktop 已安裝
- Python 3.11+ 已安裝
- Flutter 3.x+ SDK 已安裝（Flutter 部分在 Sprint 1 可選）

### Internal Dependencies
- 架構文檔已完成 ✅
- PRD 已完成 ✅
- Epic 拆分已完成 ✅

### Potential Blockers
- 無

---

## Notes

- Flutter frontend 在 Sprint 1 中只需要初始化項目結構，不需要實作任何 UI
- Worker Agent 的 AI tool integration 在 Sprint 5 才開始，Sprint 1 只需基礎框架
- 本 Sprint 重點是"能跑起來"，不追求完美實作

---

**Sprint Planning Meeting Date:** 2025-11-12
**Sprint Review Date:** 2025-11-25
**Sprint Retrospective Date:** 2025-11-25
