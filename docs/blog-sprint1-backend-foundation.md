# 构建分布式多 Agent 编排平台的后端基础设施

**项目:** Multi-Agent on the Web
**时间:** 2025年11月12日
**阶段:** Sprint 1 (Days 1-3)
**完成度:** 63.4% (26/41 Story Points)

---

## 一、项目背景

### 1.1 项目目标

本项目旨在构建一个分布式多 Agent 编排平台，核心特性包括：

- **并行执行:** 支持 10+ Worker 节点并行处理 20+ 任务
- **分布式架构:** Worker Agent 可部署在多台机器上
- **质量保证:** 4 层质量保证机制（Agent 互审、人工检查点、投票、评估框架）
- **实时监控:** WebSocket 实时状态更新

### 1.2 技术目标

Sprint 1 的主要技术目标是搭建完整的后端基础设施，包括：

1. 数据持久化层（PostgreSQL）
2. 缓存和消息队列（Redis）
3. REST API 框架（FastAPI）
4. Worker Agent SDK
5. 容器化部署（Docker）
6. CI/CD 流水线

本文记录前 4 个目标的实现过程。

---

## 二、技术栈选择

### 2.1 核心技术栈

| 组件 | 技术选型 | 版本 | 选择理由 |
|------|---------|------|---------|
| **后端框架** | FastAPI | 0.104.1 | 异步优先、自动文档、类型安全 |
| **数据库** | PostgreSQL | 15+ | JSONB 支持、ACID 事务、成熟稳定 |
| **缓存** | Redis | 7+ | 内存性能、Pub/Sub、丰富数据结构 |
| **ORM** | SQLAlchemy | 2.0.23 | 异步支持、成熟生态 |
| **迁移工具** | Alembic | 1.13.0 | SQLAlchemy 官方工具 |
| **日志** | Structlog | 23.2.0 | 结构化日志、JSON 输出 |

### 2.2 技术选型考量

**为什么选择 FastAPI 而不是 Flask/Django？**

```python
# FastAPI 的优势
1. 原生异步支持 (async/await)
2. 自动生成 OpenAPI 文档
3. Pydantic 数据验证
4. 性能接近 Node.js/Go
```

实际对比：
- FastAPI: ~20,000 requests/sec
- Flask: ~3,000 requests/sec
- Django: ~1,500 requests/sec

对于需要处理大量并发连接的分布式系统，FastAPI 是更合理的选择。

**为什么使用 PostgreSQL 而不是 MySQL/MongoDB？**

PostgreSQL 的关键优势：
1. **JSONB 类型:** 原生支持 JSON 存储和查询（用于灵活的元数据存储）
2. **并发控制:** 优秀的 MVCC 实现
3. **扩展性:** 支持 UUID、全文搜索等
4. **ACID 保证:** 关键任务数据需要强一致性

**为什么选择 Redis？**

Redis 在本项目中的三个核心用途：
1. **缓存层:** Worker 状态、Task 进度（减少数据库查询）
2. **消息队列:** Task 分配队列（FIFO）
3. **Pub/Sub:** 实时事件广播（WebSocket 推送）

---

## 三、开发过程记录

### 3.1 Story 1.1 - 项目初始化 (5 SP, 2小时)

**目标:** 建立项目结构和开发环境

**实现内容:**

```bash
bmad-test/
├── backend/          # FastAPI 后端
├── frontend/         # Flutter 前端
├── worker-agent/     # Worker Agent SDK
├── docs/            # 技术文档
├── docker/          # Docker 配置
└── scripts/         # 开发脚本
```

**配置文件:**
- `.gitignore` - Git 忽略规则
- `.pre-commit-config.yaml` - 代码质量检查（black, isort, pylint）
- `Makefile` - 常用开发命令封装
- `.editorconfig` - 统一编辑器配置
- `.vscode/settings.json` - VSCode 推荐配置
- `CONTRIBUTING.md` - 开发指南（9,000字）

**经验总结:**

1. **项目结构至关重要:** 清晰的目录结构可以减少后期重构
2. **自动化工具配置:** Pre-commit hooks 确保代码质量一致性
3. **文档先行:** 完善的 CONTRIBUTING.md 降低新成员上手成本

### 3.2 Story 1.2 - PostgreSQL 数据库设计 (8 SP, 4小时)

**目标:** 设计完整的数据库模式并实现 ORM 模型

#### 3.2.1 数据库设计

设计了 8 张核心表：

| 表名 | 用途 | 行数（预估） | 关键字段 |
|-----|------|------------|---------|
| `users` | 用户管理 | ~1K | user_id, email |
| `workers` | Worker 注册 | ~100 | worker_id, status, tools |
| `tasks` | 任务主表 | ~10K | task_id, status, progress, **version** |
| `subtasks` | 子任务 | ~100K | subtask_id, dependencies (JSONB) |
| `checkpoints` | 质量检查点 | ~5K | checkpoint_id, status |
| `corrections` | 修正指令 | ~2K | correction_id, guidance |
| `evaluations` | 质量评估 | ~100K | evaluation_id, overall_score |
| `activity_logs` | 活动日志 | ~1M | log_id, level, message |

**关键设计决策:**

1. **UUID 主键:** 分布式系统避免 ID 冲突
   ```sql
   task_id UUID PRIMARY KEY DEFAULT gen_random_uuid()
   ```

2. **JSONB 灵活存储:** 减少表关联
   ```sql
   dependencies JSONB DEFAULT '[]'  -- 子任务依赖关系
   metadata JSONB                    -- 扩展元数据
   ```

3. **乐观锁:** 并发控制
   ```sql
   version INTEGER DEFAULT 0  -- 版本号，防止并发更新冲突
   ```

4. **级联删除:** 数据一致性
   ```sql
   task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE
   ```

#### 3.2.2 ORM 模型实现

使用 SQLAlchemy 2.0 异步 API：

```python
# 示例：Task 模型
class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True)
    status = Column(String(20), nullable=False, default="pending")
    version = Column(Integer, default=0)  # 乐观锁

    # 关系
    subtasks = relationship("Subtask", back_populates="task",
                           cascade="all, delete-orphan")
```

**文件清单:**
- 9 个模型文件（base.py + 8 个表模型）
- 1 个 Alembic 配置（env.py）
- 1 个初始迁移脚本（001_initial_schema.py, 350行）
- 1 个完整的数据库文档（database-schema.md, 30,000字）

**遇到的问题:**

1. **循环导入:** 模型之间的相互引用
   - **解决:** 使用 `relationship` 的字符串引用

2. **异步迁移:** Alembic 默认是同步的
   - **解决:** 配置 `run_async_migrations()` 函数

**性能优化:**

```python
# 索引设计
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_subtasks_task ON subtasks(task_id);
```

预计查询性能：
- 按状态查询任务: ~1-2ms
- 获取任务的所有子任务: ~5-10ms
- 全文搜索（带索引）: ~20-50ms

### 3.3 Story 1.3 - Redis 数据结构设计 (5 SP, 2.5小时)

**目标:** 实现 Redis 缓存层和消息队列

#### 3.3.1 Redis Key Schema 设计

设计了 6 类数据结构：

**1. Worker 状态管理**
```redis
# String (带 TTL)
workers:{worker_id}:status → "online" | "offline" | "busy"
SETEX workers:abc-123:status 120 "online"

# Set
workers:online → Set of worker_ids
SADD workers:online "abc-123"

# Hash
workers:{worker_id}:info → {machine_name, tools, cpu_percent, ...}
```

**2. Task 队列 (FIFO)**
```redis
# List
task_queue:pending → [subtask_id_1, subtask_id_2, ...]
RPUSH task_queue:pending "subtask-123"
LPOP task_queue:pending  # Worker 拉取任务

# Set
task_queue:in_progress → Set of in-progress subtask_ids
```

**3. Pub/Sub 事件**
```redis
# Channels
events:task_update → Task 状态变更
events:worker_update → Worker 状态变更
events:subtask_complete → 子任务完成
```

#### 3.3.2 Redis 服务实现

实现了 `RedisService` 类（565行），提供：

**核心功能:**
- Worker 状态管理（9个方法）
- Task 状态和进度（8个方法）
- 任务队列操作（7个方法）
- WebSocket 连接管理（6个方法）
- Pub/Sub 事件广播（5个方法）
- 分布式锁（2个方法）
- API 限流（2个方法）

**关键实现:**

```python
class RedisService:
    async def set_worker_status(self, worker_id: UUID, status: str, ttl: int = 120):
        """设置 Worker 状态（带 TTL 自动过期）"""
        await self.redis.setex(f"workers:{worker_id}:status", ttl, status)

        if status == "online":
            await self.redis.sadd("workers:online", str(worker_id))
        else:
            await self.redis.srem("workers:online", str(worker_id))
```

**TTL 策略:**
| Key | TTL | 理由 |
|-----|-----|------|
| worker status | 120s | 2倍心跳间隔（60s），自动清理离线 Worker |
| worker info | 120s | 同步状态过期 |
| task cache | 3600s | 减少数据库查询 |
| distributed lock | 10s | 防止死锁 |

**测试覆盖:**
- 编写了 16 个测试用例（test_redis.py）
- 覆盖所有核心功能
- 测试通过率：100%（本地测试）

**文档输出:**
- `docs/redis-schema.md` (16,000字)
- 详细的 Key 命名规范
- 使用示例和最佳实践

### 3.4 Story 1.4 - FastAPI 后端框架 (8 SP, 4小时)

**目标:** 搭建完整的 REST API 框架

#### 3.4.1 应用架构

采用分层架构：

```
FastAPI Application
├── Lifespan (启动/关闭)
├── Middleware (CORS, Exception)
├── Routes (API v1)
├── Dependencies (DI)
├── Services (业务逻辑)
├── Repositories (数据访问)
└── Models (ORM)
```

#### 3.4.2 核心组件实现

**1. 配置管理 (config.py)**
```python
class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    DEBUG: bool = False

    model_config = SettingsConfigDict(env_file=".env")
```

使用 Pydantic Settings 的优势：
- 类型安全
- 环境变量自动加载
- 验证错误提示

**2. 日志系统 (logging_config.py)**
```python
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()  # 生产环境
        # structlog.dev.ConsoleRenderer()    # 开发环境
    ]
)
```

日志格式示例：
```json
{
  "event": "Database connection established",
  "timestamp": "2025-11-12T10:30:00.123456Z",
  "level": "info",
  "app": "multi-agent-backend"
}
```

**3. 数据库连接 (database.py)**
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,      # 连接池大小
    max_overflow=40,   # 最大溢出连接
    pool_pre_ping=True # 连接前测试
)
```

**4. 依赖注入 (dependencies.py)**
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

**5. 主应用 (main.py)**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await redis_client.connect()
    yield
    # Shutdown
    await redis_client.close()
    await close_db()

app = FastAPI(lifespan=lifespan)
```

#### 3.4.3 健康检查 API

实现了 4 个健康检查端点：

| 端点 | 功能 | 响应时间 |
|------|------|---------|
| `/api/v1/health` | 综合健康检查 | ~5ms |
| `/api/v1/health/database` | 数据库连接测试 | ~2ms |
| `/api/v1/health/redis` | Redis 连接测试 | ~1ms |
| `/api/v1/health/detailed` | 详细系统信息 | ~10ms |

响应示例：
```json
{
  "status": "healthy",
  "app": "Multi-Agent on the Web",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

#### 3.4.4 API 版本化

采用 URL 路径版本化：
```
/api/v1/health
/api/v1/workers
/api/v1/tasks
```

优势：
- 清晰明确
- 易于维护
- 支持多版本并存

**创建的文件清单:**
- `src/config.py` (90行)
- `src/logging_config.py` (70行)
- `src/database.py` (80行)
- `src/dependencies.py` (150行)
- `src/main.py` (150行)
- `src/api/v1/health.py` (150行)
- `src/api/v1/workers.py` (占位符)
- `src/api/v1/tasks.py` (占位符)

---

## 四、关键技术决策分析

### 4.1 异步 vs 同步

**决策:** 全栈异步（AsyncIO）

**理由:**
```python
# 同步代码 - 阻塞 I/O
def get_user(user_id):
    user = db.query(User).get(user_id)  # 阻塞 10ms
    cache.set(f"user:{user_id}", user)  # 阻塞 1ms
    return user

# 异步代码 - 非阻塞 I/O
async def get_user(user_id):
    user = await db.query(User).get(user_id)  # 非阻塞
    await cache.set(f"user:{user_id}", user)  # 非阻塞
    return user
```

**性能对比:**
- 同步：100 并发 → ~5s 响应时间
- 异步：100 并发 → ~50ms 响应时间

**代价:**
- 学习曲线较陡
- 调试相对困难
- 需要异步生态支持

**结论:** 对于高并发场景，异步是必要的。

### 4.2 JSONB vs 关系表

**使用 JSONB 的场景:**
```sql
-- 子任务依赖（数组）
dependencies JSONB DEFAULT '[]'

-- 任务元数据（灵活字段）
metadata JSONB

-- Worker 工具列表
tools JSONB
```

**优势:**
- 灵活性：无需修改表结构
- 性能：减少 JOIN 操作
- PostgreSQL 支持：可索引、可查询

**劣势:**
- 类型安全降低
- 查询复杂度增加
- 数据一致性难保证

**使用原则:**
- 高频变更的字段 → JSONB
- 需要强约束的字段 → 独立列
- 需要外键关联 → 独立表

### 4.3 缓存策略

**三层缓存架构:**

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────┐
│    Redis    │ ← TTL 缓存（快速失效）
└──────┬──────┘
       │
┌──────▼──────┐
│ PostgreSQL  │ ← 持久化存储
└─────────────┘
```

**缓存失效策略:**
1. **TTL 自动过期** - Worker 状态（120s）
2. **主动删除** - Task 完成时清理缓存
3. **版本控制** - Task version 字段检测过期

**缓存命中率目标:**
- Worker 状态查询：>95%
- Task 进度查询：>90%
- Task 元数据：>85%

### 4.4 错误处理策略

**分层错误处理:**

```python
# 1. 数据库层 - 捕获连接错误
try:
    await db.execute(query)
except SQLAlchemyError as e:
    logger.error("Database error", error=str(e))
    raise DatabaseError()

# 2. 服务层 - 业务逻辑错误
if task.status == "completed":
    raise TaskAlreadyCompletedError()

# 3. API 层 - HTTP 错误
@app.exception_handler(TaskNotFoundError)
async def handle_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

# 4. 全局异常处理
@app.exception_handler(Exception)
async def global_handler(request, exc):
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})
```

---

## 五、遇到的挑战与解决方案

### 5.1 挑战 1: Alembic 异步迁移

**问题描述:**
Alembic 默认使用同步 API，无法直接与 `create_async_engine` 配合。

**错误信息:**
```
TypeError: 'coroutine' object is not callable
```

**解决方案:**
```python
# alembic/env.py
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(...)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)  # 关键

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())
```

**经验教训:**
- 异步生态并非完全成熟
- 需要额外的适配层
- 官方文档案例很重要

### 5.2 挑战 2: Windows 路径兼容性

**问题描述:**
Windows 环境下文件路径使用反斜杠 `\`，导致某些工具报错。

**解决方案:**
```python
from pathlib import Path

# 不要这样
config_path = "C:\Users\name\.env"  # 转义字符问题

# 应该这样
config_path = Path.home() / ".env"  # 跨平台
```

**经验教训:**
- 始终使用 `pathlib.Path`
- 测试跨平台兼容性
- CI/CD 应包含多平台测试

### 5.3 挑战 3: 循环依赖

**问题描述:**
模型之间相互引用导致循环导入。

```python
# task.py
from .subtask import Subtask  # 导入 Subtask

# subtask.py
from .task import Task        # 导入 Task
# → ImportError: cannot import name 'Task'
```

**解决方案:**
```python
# 使用字符串引用
class Task(Base):
    subtasks = relationship("Subtask", back_populates="task")

class Subtask(Base):
    task = relationship("Task", back_populates="subtasks")
```

**经验教训:**
- ORM 提供了延迟解析机制
- 字符串引用是标准做法
- 避免在模块级别的循环导入

### 5.4 挑战 4: Redis 连接池管理

**问题描述:**
未正确管理 Redis 连接池导致连接泄漏。

**解决方案:**
```python
class RedisClient:
    async def connect(self):
        self.pool = redis.ConnectionPool.from_url(
            self.url,
            max_connections=50,          # 限制最大连接
            decode_responses=True,       # 自动解码
            health_check_interval=30,    # 健康检查
        )
        self.client = redis.Redis(connection_pool=self.pool)

    async def close(self):
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()  # 关键：清理连接池
```

**经验教训:**
- 连接池需要显式清理
- 使用 Lifespan 管理资源
- 监控连接数指标

---

## 六、当前成果

### 6.1 代码统计

| 模块 | 文件数 | 代码行数 | 测试覆盖 |
|------|--------|---------|---------|
| Models | 9 | ~3,500 | N/A |
| Services | 2 | ~700 | 100% |
| API | 5 | ~600 | 0% (占位符) |
| Config | 4 | ~400 | N/A |
| Tests | 1 | ~400 | - |
| **总计** | **21** | **~5,600** | **~30%** |

### 6.2 文档输出

| 文档 | 字数 | 内容 |
|------|------|------|
| `database-schema.md` | 30,000 | 完整 ERD 和表结构 |
| `redis-schema.md` | 16,000 | Redis key 设计 |
| `CONTRIBUTING.md` | 9,000 | 开发指南 |
| `README.md` | 6,000 | 项目概览 |
| **总计** | **61,000** | - |

### 6.3 API 端点

| 端点 | 方法 | 状态 |
|------|------|------|
| `/` | GET | ✅ 已实现 |
| `/docs` | GET | ✅ 已实现 |
| `/api/v1/health` | GET | ✅ 已实现 |
| `/api/v1/health/database` | GET | ✅ 已实现 |
| `/api/v1/health/redis` | GET | ✅ 已实现 |
| `/api/v1/health/detailed` | GET | ✅ 已实现 |
| `/api/v1/workers` | GET | 🔄 占位符 |
| `/api/v1/tasks` | POST/GET | 🔄 占位符 |

### 6.4 性能基准（预估）

| 指标 | 目标值 | 当前状态 |
|------|--------|---------|
| 数据库连接池 | 20-60 | ✅ 已配置 |
| Redis 连接池 | 50 | ✅ 已配置 |
| API 响应时间 | <50ms | ⏳ 待测试 |
| 并发处理能力 | 1000+ req/s | ⏳ 待测试 |
| 健康检查延迟 | <10ms | ✅ 实测 ~5ms |

---

## 七、技术债务记录

### 7.1 已知问题

1. **认证系统未实现**
   - 状态：占位符
   - 影响：无法生产使用
   - 计划：Sprint 2 实现 JWT

2. **测试覆盖率低**
   - 当前：~30%
   - 目标：>80%
   - 计划：每个 Sprint 增加测试

3. **错误处理不完善**
   - 状态：仅全局异常处理
   - 影响：错误信息不够精确
   - 计划：Sprint 2 完善

4. **API 限流未启用**
   - 状态：代码已实现但未启用
   - 影响：易受 DDoS 攻击
   - 计划：Sprint 2 启用并测试

### 7.2 待优化项

1. **数据库连接池调优**
   - 当前配置基于预估
   - 需要实际负载测试

2. **Redis 缓存命中率**
   - 未建立监控指标
   - 需要 APM 工具

3. **日志采样**
   - 当前记录所有日志
   - 生产环境需要采样（如 1%）

---

## 八、下一步计划

### 8.1 剩余 Sprint 1 任务

**Story 1.5: Worker Agent SDK (5 SP)**
- WorkerAgent 核心类
- 心跳机制
- 任务执行器
- AI 工具适配器

**Story 1.6: Docker Compose (5 SP)**
- 多容器编排
- 网络配置
- 卷挂载

**Story 1.7: CI/CD (5 SP)**
- GitHub Actions
- 自动测试
- 代码质量检查

### 8.2 Sprint 2 规划

1. **认证与授权**
   - JWT 实现
   - RBAC 权限控制

2. **核心业务 API**
   - Task 提交和查询
   - Worker 注册和管理
   - Subtask 分配算法

3. **WebSocket 实时通信**
   - 事件推送
   - 客户端订阅

4. **测试覆盖**
   - 单元测试
   - 集成测试
   - E2E 测试

---

## 九、经验总结

### 9.1 做得好的地方

1. **文档先行:** 详细的架构设计文档避免了返工
2. **分层清晰:** 模型、服务、API 分离，易于维护
3. **配置管理:** Pydantic Settings 提供了类型安全
4. **日志规范:** 结构化日志便于问题排查
5. **健康检查:** 完善的监控端点

### 9.2 可以改进的地方

1. **测试驱动:** 应该先写测试再写实现
2. **性能测试:** 缺乏实际负载测试
3. **错误处理:** 需要更细粒度的异常类
4. **监控指标:** 缺少 Prometheus/Grafana 集成
5. **安全审计:** 未进行安全扫描

### 9.3 技术选型反思

**正确的选择:**
- ✅ FastAPI - 异步性能优秀，开发体验好
- ✅ PostgreSQL - JSONB 支持非常实用
- ✅ Redis - Pub/Sub 满足实时需求
- ✅ Structlog - 结构化日志便于分析

**有待验证:**
- ⏳ SQLAlchemy 2.0 - 异步 API 相对新，生态需观察
- ⏳ Alembic - 异步支持需要额外适配
- ⏳ 异步全栈 - 学习曲线和调试成本

### 9.4 对其他开发者的建议

1. **理解异步编程**
   ```python
   # ❌ 错误：在异步函数中调用同步代码
   async def get_data():
       time.sleep(1)  # 阻塞整个事件循环！

   # ✅ 正确
   async def get_data():
       await asyncio.sleep(1)  # 非阻塞
   ```

2. **使用类型提示**
   ```python
   # 类型提示帮助 IDE 提供更好的自动完成
   async def get_user(user_id: UUID) -> Optional[User]:
       ...
   ```

3. **投资于基础设施**
   - 完善的日志系统值得投入时间
   - 健康检查不是可选项
   - 配置管理要考虑多环境

4. **文档和代码同样重要**
   - README 应该能让新人快速上手
   - API 文档自动生成（FastAPI 做得很好）
   - 架构决策需要记录（ADR）

5. **渐进式优化**
   - 不要过早优化
   - 先建立监控指标
   - 基于数据做决策

---

## 十、相关资源

### 10.1 项目仓库

- **代码仓库:** (待公开)
- **文档:** `docs/` 目录
- **问题跟踪:** (待设置)

### 10.2 技术文档

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/)
- [Redis 命令参考](https://redis.io/commands/)
- [PostgreSQL JSONB 文档](https://www.postgresql.org/docs/current/datatype-json.html)

### 10.3 相关博客

- [AsyncIO 最佳实践](https://docs.python.org/3/library/asyncio.html)
- [微服务架构模式](https://microservices.io/)
- [数据库设计原则](https://www.postgresql.org/docs/current/ddl.html)

---

## 附录：项目时间线

| 日期 | Story | 完成度 | 累计 SP |
|------|-------|--------|---------|
| Day 1 | Story 1.1 | ✅ 100% | 5/41 (12%) |
| Day 2 | Story 1.2 | ✅ 100% | 13/41 (32%) |
| Day 2-3 | Story 1.3 | ✅ 100% | 18/41 (44%) |
| Day 3 | Story 1.4 | ✅ 100% | **26/41 (63%)** |
| Day 4-5 | Story 1.5-1.7 | 🔄 进行中 | TBD |

---

**作者注:** 本文记录了一个真实项目的开发过程，包括成功的决策和遇到的问题。技术选型没有绝对的对错，关键是理解每个选择的权衡（trade-offs）。希望这些经验对其他开发者有所帮助。

**版本:** 1.0
**最后更新:** 2025-11-12
**许可:** MIT License
