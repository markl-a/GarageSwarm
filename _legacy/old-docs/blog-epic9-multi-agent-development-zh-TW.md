# 多 AI Agent 協作開發實戰：Epic 9 測試與文檔的並行開發之旅

> 本文記錄了使用 Claude Code 多 Agent 並行開發模式完成 Multi-Agent on the Web 專案 Epic 9 的完整流程。

## 前言

在軟體開發中，測試和文檔往往是最容易被忽略但又至關重要的環節。今天，我們使用 Claude Code 的多 Agent 並行開發模式，在短時間內完成了 Epic 9 的全部 6 個 Story，包含端到端測試、性能測試、錯誤處理、用戶文檔、開發者文檔和發布準備。

## 專案背景

Multi-Agent on the Web 是一個基於 Web 的多 AI Agent 協作平台，技術棧包括：

- **後端**: FastAPI + PostgreSQL + Redis
- **前端**: Flutter Web
- **Worker Agent**: Python + 多 AI 工具整合

在 Epic 1-8 完成後，專案已具備完整的核心功能，Epic 9 的目標是補齊測試覆蓋率、性能優化和完整文檔。

## 開發流程

### 第一步：測試驗證

在開始 Epic 9 之前，首先驗證現有測試是否全部通過：

```bash
cd backend && python -m pytest
```

結果發現 22 個測試失敗！問題出在 `test_review_service.py` 和 `test_parallel_scheduler.py` 的 async fixture。

#### 問題分析

```python
# 錯誤的寫法 - 使用同步 fixture
@pytest.fixture
def sample_task(db_session):
    task = Task(...)
    db_session.add(task)
    db_session.flush()  # 同步方法，不會真正執行
    return task
```

#### 解決方案

```python
# 正確的寫法 - 使用異步 fixture
import pytest_asyncio
from sqlalchemy import select

@pytest_asyncio.fixture
async def sample_task(db_session):
    task = Task(...)
    db_session.add(task)
    await db_session.commit()  # 異步提交
    await db_session.refresh(task)  # 刷新獲取 ID
    return task
```

修復後，**208 個測試全部通過**！

### 第二步：多 Agent 並行開發策略

Epic 9 包含 6 個相互獨立的 Story，非常適合並行開發：

```
Epic 9: 測試、優化與文檔
├── Story 9.1: 端到端測試套件
├── Story 9.2: 性能測試和優化
├── Story 9.3: 錯誤處理完善
├── Story 9.4: 用戶文檔撰寫
├── Story 9.5: 開發者文檔撰寫
└── Story 9.6: 發布準備和 GitHub 配置
```

我們將 6 個 Story 分成兩批並行執行：

#### 第一批：技術實現類（Story 9.1-9.3）

同時啟動 3 個 Agent：

```
Agent 1: E2E 測試 → 專注於完整流程測試
Agent 2: 性能測試 → 專注於 Locust 壓測和優化
Agent 3: 錯誤處理 → 專注於異常機制和重試邏輯
```

#### 第二批：文檔與配置類（Story 9.4-9.6）

```
Agent 4: 用戶文檔 → 安裝指南、使用手冊
Agent 5: 開發者文檔 → API 參考、架構深入
Agent 6: 發布準備 → GitHub 配置、LICENSE
```

### 第三步：各 Story 成果

#### Story 9.1: 端到端測試套件 (69 tests)

建立完整的 E2E 測試框架：

```
backend/tests/e2e/
├── __init__.py
├── conftest.py              # E2E 專用 fixtures
├── test_task_lifecycle.py   # 任務生命週期
├── test_worker_lifecycle.py # Worker 生命週期
├── test_subtask_flow.py     # 子任務流程
├── test_evaluation_flow.py  # 評估流程
├── test_checkpoint_flow.py  # 檢查點流程
└── test_error_scenarios.py  # 錯誤場景
```

關鍵設計模式 - Factory Pattern：

```python
class TaskFactory:
    """測試數據工廠"""
    @staticmethod
    async def create_task(db_session, **overrides):
        defaults = {
            "title": f"Test Task {uuid.uuid4().hex[:8]}",
            "description": "E2E test task",
            "status": TaskStatus.PENDING,
            "priority": 5
        }
        defaults.update(overrides)
        task = Task(**defaults)
        db_session.add(task)
        await db_session.commit()
        return task
```

#### Story 9.2: 性能測試和優化 (29 tests)

建立 Locust 壓測框架：

```python
# backend/tests/performance/locustfile.py
class TaskAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_tasks(self):
        self.client.get("/api/v1/tasks")

    @task(2)
    def create_task(self):
        self.client.post("/api/v1/tasks", json={...})

    @task(1)
    def get_task_detail(self):
        self.client.get(f"/api/v1/tasks/{self.task_id}")
```

性能測試覆蓋：
- 並發任務創建 (50+ 並發)
- Worker 心跳負載
- 資料庫連接池壓力
- Redis 快取命中率

#### Story 9.3: 錯誤處理完善 (50 tests)

建立統一的異常處理機制：

```python
# backend/src/exceptions.py
class BaseAPIException(Exception):
    """API 異常基類"""
    def __init__(self, message: str, error_code: str, status_code: int):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class TaskNotFoundException(BaseAPIException):
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task {task_id} not found",
            error_code="TASK_NOT_FOUND",
            status_code=404
        )
```

指數退避重試機制：

```python
# worker-agent/src/utils/retry.py
async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
):
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            await asyncio.sleep(delay)
```

#### Story 9.4: 用戶文檔 (~86KB)

```
docs/
├── installation.md      # 安裝指南
├── user-guide.md        # 使用手冊
├── api-reference.md     # API 參考
├── troubleshooting.md   # 故障排除
└── README.md            # 文檔索引
```

#### Story 9.5: 開發者文檔

```
docs/
├── development.md           # 開發環境設置
├── contributing.md          # 貢獻指南
├── architecture-deep-dive.md # 架構深入解析
├── extending-evaluation.md  # 擴展評估系統
└── adding-ai-tools.md       # 添加 AI 工具
```

#### Story 9.6: 發布準備

```
.github/
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   ├── feature_request.md
│   └── config.yml
├── PULL_REQUEST_TEMPLATE.md
└── workflows/
    └── ci.yml

LICENSE (MIT)
```

## 開發效率分析

### 時間對比

| 開發模式 | 預估時間 | 實際時間 | 效率提升 |
|---------|---------|---------|---------|
| 單人串行 | 16-24 小時 | - | 基準 |
| 多 Agent 並行 | - | ~2 小時 | **8-12x** |

### 產出統計

- **測試文件**: 43 個
- **測試案例**: 208+ 個 (後端) + 69 個 (E2E)
- **文檔**: 28 份 (~150KB)
- **程式碼覆蓋**: 核心模組 >80%

## 關鍵學習

### 1. Async Fixture 的正確使用

pytest-asyncio 的 fixture 必須使用 `@pytest_asyncio.fixture`，而非 `@pytest.fixture`：

```python
# ✅ 正確
@pytest_asyncio.fixture
async def db_session():
    async with async_session() as session:
        yield session

# ❌ 錯誤
@pytest.fixture
async def db_session():
    ...
```

### 2. SQLAlchemy Async Session 的物件刷新

更新資料後，需要重新查詢才能獲取最新狀態：

```python
# 更新後重新查詢
await service.update_subtask(subtask_id, new_data)

# 不要依賴本地物件狀態
result = await db_session.execute(
    select(Subtask).where(Subtask.subtask_id == subtask_id)
)
refreshed = result.scalar_one()
assert refreshed.status == expected_status  # ✅
```

### 3. 並行開發的任務劃分原則

適合並行的任務特徵：
- **低耦合**: 任務間沒有依賴關係
- **明確邊界**: 各任務輸出不會衝突
- **獨立驗證**: 可以獨立測試和驗證

不適合並行的情況：
- 需要共享狀態或配置
- 有嚴格的執行順序
- 輸出會相互覆蓋

### 4. Agent 協作的溝通模式

```
主 Agent (協調者)
    │
    ├── 制定整體計劃
    ├── 分配任務給子 Agent
    ├── 收集各 Agent 結果
    └── 整合並驗證

子 Agent (執行者)
    │
    ├── 接收明確的任務定義
    ├── 獨立完成任務
    └── 回報完成狀態和產出
```

## 結論

多 Agent 並行開發模式在以下場景特別有效：

1. **測試撰寫**: 不同模組的測試可以完全並行
2. **文檔撰寫**: 用戶文檔和開發者文檔可以同時進行
3. **獨立功能**: 沒有依賴關係的功能模組

透過合理的任務劃分和並行執行，我們在 Epic 9 中實現了 8-12 倍的開發效率提升。這種模式不僅適用於 AI 輔助開發，也可以借鑑到人類團隊的工作分配中。

## 專案連結

- **GitHub**: [Multi-Agent on the Web](https://github.com/your-repo)
- **文檔**: [docs/README.md](./README.md)
- **API 參考**: [docs/api-reference.md](./api-reference.md)

---

*本文由 Claude Code 協助撰寫，記錄於 2024 年 12 月*
