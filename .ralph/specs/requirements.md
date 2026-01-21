# GarageSwarm 2.0 - 技術規格

## Phase 0: 基礎設施修復

### P0-1: WebSocket 實現

**目標**: 實現 Worker 與 Backend 之間的 WebSocket 連接

**技術規格**:
```python
# backend/src/api/v1/websocket.py

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json

class ConnectionManager:
    """管理 WebSocket 連接"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, worker_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[worker_id] = websocket

    async def disconnect(self, worker_id: str):
        if worker_id in self.active_connections:
            del self.active_connections[worker_id]

    async def send_task(self, worker_id: str, task: dict):
        if worker_id in self.active_connections:
            await self.active_connections[worker_id].send_json(task)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/worker/{worker_id}")
async def websocket_endpoint(websocket: WebSocket, worker_id: str):
    # 驗證 Worker
    # 建立連接
    # 處理消息
    # 心跳檢測
    pass
```

**驗收標準**:
- [ ] Worker 可以連接到 WebSocket 端點
- [ ] 連接管理器追蹤活躍連接
- [ ] 支持向特定 Worker 發送消息
- [ ] 支持廣播消息
- [ ] 斷開連接時正確清理

---

### P0-2: 結果回報端點

**目標**: Worker 可以回報任務執行結果

**API 規格**:
```
POST /api/v1/workers/{worker_id}/report-result

Headers:
  X-Worker-API-Key: string (required)
  Content-Type: application/json

Request Body:
{
  "task_id": "uuid",
  "status": "completed" | "failed" | "cancelled",
  "result": {
    "output": "string",
    "data": {}  // 可選的結構化數據
  },
  "error": "string" | null,
  "execution_time_ms": integer,
  "metrics": {
    "tokens_used": integer,
    "api_calls": integer
  }
}

Response (200 OK):
{
  "success": true,
  "task_id": "uuid",
  "new_status": "completed"
}

Response (400 Bad Request):
{
  "detail": "Task not found or not assigned to this worker"
}
```

**Pydantic Schema**:
```python
# backend/src/schemas/worker.py

class TaskResultReport(BaseModel):
    task_id: UUID
    status: Literal["completed", "failed", "cancelled"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int
    metrics: Optional[Dict[str, int]] = None

class TaskResultResponse(BaseModel):
    success: bool
    task_id: UUID
    new_status: str
```

**驗收標準**:
- [ ] 端點接受有效的結果回報
- [ ] 更新數據庫中的任務狀態
- [ ] 記錄執行指標
- [ ] 拒絕未授權的請求
- [ ] 拒絕不屬於該 Worker 的任務

---

### P0-3: Worker API Key 驗證

**目標**: 驗證 Worker 的 API Key

**實現規格**:
```python
# backend/src/auth/worker_auth.py

from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def verify_worker_api_key(
    x_worker_api_key: str = Header(..., alias="X-Worker-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> Worker:
    """驗證 Worker API Key 並返回 Worker 對象"""

    # 查詢 Worker
    worker = await db.execute(
        select(Worker).where(Worker.api_key == x_worker_api_key)
    )
    worker = worker.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=401,
            detail="Invalid Worker API Key"
        )

    if not worker.is_active:
        raise HTTPException(
            status_code=403,
            detail="Worker is deactivated"
        )

    return worker
```

**API Key 生成**:
```python
import secrets

def generate_worker_api_key() -> str:
    """生成安全的 Worker API Key"""
    return f"gsw_{secrets.token_urlsafe(32)}"
```

**驗收標準**:
- [ ] 有效 API Key 通過驗證
- [ ] 無效 API Key 返回 401
- [ ] 停用的 Worker 返回 403
- [ ] API Key 在註冊時自動生成
- [ ] API Key 安全存儲（考慮 hash）

---

### P0-4: Worker 結果回報客戶端

**目標**: Worker Agent 自動回報執行結果

**實現規格**:
```python
# worker-agent/src/agent/result_reporter.py

import httpx
from typing import Optional, Dict, Any

class ResultReporter:
    """任務結果回報器"""

    def __init__(self, backend_url: str, api_key: str):
        self.backend_url = backend_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"X-Worker-API-Key": api_key}
        )

    async def report_result(
        self,
        worker_id: str,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time_ms: int = 0
    ) -> bool:
        """回報任務執行結果"""

        url = f"{self.backend_url}/api/v1/workers/{worker_id}/report-result"

        payload = {
            "task_id": task_id,
            "status": status,
            "result": result,
            "error": error,
            "execution_time_ms": execution_time_ms
        }

        try:
            response = await self.client.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            # 記錄錯誤，稍後重試
            return False

    async def close(self):
        await self.client.aclose()
```

**整合到 TaskExecutor**:
```python
# worker-agent/src/agent/executor.py

class TaskExecutor:
    async def execute_task(self, task: Task) -> TaskResult:
        start_time = time.time()

        try:
            result = await self._run_tool(task)
            execution_time = int((time.time() - start_time) * 1000)

            # 回報成功
            await self.reporter.report_result(
                worker_id=self.worker_id,
                task_id=task.id,
                status="completed",
                result=result,
                execution_time_ms=execution_time
            )

            return result

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)

            # 回報失敗
            await self.reporter.report_result(
                worker_id=self.worker_id,
                task_id=task.id,
                status="failed",
                error=str(e),
                execution_time_ms=execution_time
            )

            raise
```

**驗收標準**:
- [ ] 成功執行後自動回報
- [ ] 失敗執行後自動回報錯誤
- [ ] 包含執行時間
- [ ] 網絡錯誤時重試
- [ ] 與現有 TaskExecutor 整合

---

## 數據庫 Schema 補充

### Worker 表添加 API Key

```python
# backend/src/models/worker.py

class Worker(Base):
    __tablename__ = "workers"

    # 現有字段...

    # 新增字段
    api_key = Column(String(64), unique=True, index=True)
    api_key_created_at = Column(DateTime, default=datetime.utcnow)
```

**Migration**:
```python
# alembic/versions/002_add_worker_api_key.py

def upgrade():
    op.add_column('workers', sa.Column('api_key', sa.String(64), unique=True, index=True))
    op.add_column('workers', sa.Column('api_key_created_at', sa.DateTime))

def downgrade():
    op.drop_column('workers', 'api_key')
    op.drop_column('workers', 'api_key_created_at')
```

---

## 測試規格

### WebSocket 測試

```python
# backend/tests/test_websocket.py

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_websocket_connect():
    """測試 WebSocket 連接"""
    pass

@pytest.mark.asyncio
async def test_websocket_receive_task():
    """測試通過 WebSocket 接收任務"""
    pass

@pytest.mark.asyncio
async def test_websocket_disconnect():
    """測試斷開連接"""
    pass
```

### 結果回報測試

```python
# backend/tests/test_result_report.py

@pytest.mark.asyncio
async def test_report_result_success():
    """測試成功回報結果"""
    pass

@pytest.mark.asyncio
async def test_report_result_invalid_task():
    """測試回報無效任務"""
    pass

@pytest.mark.asyncio
async def test_report_result_unauthorized():
    """測試未授權回報"""
    pass
```
