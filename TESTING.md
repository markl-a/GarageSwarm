# 測試指南

本文檔說明如何測試 Multi-Agent on the Web 專案。

---

## 測試方式總覽

我們提供三種測試方式：

1. **自動化測試（Pytest）** ⭐ 推薦
2. **Docker Compose 環境測試**
3. **手動 API 測試（curl/Postman）**

---

## 方式 1: 自動化測試（Pytest）⭐

### 準備工作

```bash
# 進入後端目錄
cd backend

# 安裝依賴（如果還沒安裝）
pip install -r requirements.txt
```

### 運行測試

#### 運行所有測試
```bash
pytest
```

#### 只運行單元測試
```bash
pytest tests/unit/ -v
```

#### 只運行整合測試
```bash
pytest tests/integration/ -v
```

#### 運行特定測試文件
```bash
# Worker Service 單元測試
pytest tests/unit/test_worker_service.py -v

# Worker API 整合測試
pytest tests/integration/test_workers_api.py -v
```

#### 運行特定測試函數
```bash
pytest tests/unit/test_worker_service.py::test_register_new_worker -v
```

#### 生成覆蓋率報告
```bash
pytest --cov=src tests/ --cov-report=html
```

然後開啟 `htmlcov/index.html` 查看覆蓋率報告。

### 測試結構

```
backend/tests/
├── unit/                           # 單元測試
│   ├── test_worker_service.py     # WorkerService 測試（10個測試）
│   └── test_models.py              # 資料模型測試
├── integration/                    # 整合測試
│   ├── test_workers_api.py        # Worker API 測試（14個測試）
│   └── test_api_health.py          # 健康檢查測試
└── conftest.py                     # 測試配置和 fixtures
```

### Worker Service 單元測試（10個測試）

- ✅ `test_register_new_worker` - 註冊新 Worker
- ✅ `test_register_existing_worker_updates` - 重複註冊（冪等性）
- ✅ `test_update_heartbeat` - 更新心跳
- ✅ `test_update_heartbeat_worker_not_found` - 心跳更新失敗
- ✅ `test_get_worker` - 查詢 Worker
- ✅ `test_get_worker_not_found` - 查詢不存在的 Worker
- ✅ `test_unregister_worker` - 註銷 Worker
- ✅ `test_unregister_worker_not_found` - 註銷不存在的 Worker

### Worker API 整合測試（14個測試）

- ✅ `test_register_worker_success` - 成功註冊
- ✅ `test_register_worker_idempotency` - 冪等性測試
- ✅ `test_register_worker_validation_error` - 驗證錯誤
- ✅ `test_worker_heartbeat_success` - 成功心跳
- ✅ `test_worker_heartbeat_not_found` - 心跳失敗
- ✅ `test_list_workers` - 列表查詢
- ✅ `test_list_workers_with_filters` - 過濾查詢
- ✅ `test_get_worker_detail` - 詳情查詢
- ✅ `test_get_worker_not_found` - 查詢失敗
- ✅ `test_unregister_worker` - 註銷成功
- ✅ `test_unregister_worker_not_found` - 註銷失敗
- ✅ `test_worker_lifecycle` - 完整生命週期測試

---

## 方式 2: Docker Compose 環境測試

### 1. 啟動服務

```bash
# 啟動所有服務（postgres, redis, backend）
make up

# 或者
docker-compose up -d
```

### 2. 檢查服務狀態

```bash
docker-compose ps
```

應該看到所有服務都是 `Up` 狀態。

### 3. 查看後端日誌

```bash
docker-compose logs -f backend
```

### 4. 測試 API

```bash
# 使用提供的測試腳本
./test-worker-api.sh

# 或手動測試（見方式 3）
```

### 5. 停止服務

```bash
make down

# 或者
docker-compose down
```

---

## 方式 3: 手動 API 測試（curl）

### 前提：後端正在運行

```bash
# 啟動 Docker Compose
make up

# 或本地運行
cd backend
uvicorn src.main:app --reload
```

### 測試腳本

#### 1. 健康檢查
```bash
curl -X GET "http://localhost:8000/api/v1/health" | jq '.'
```

#### 2. 註冊 Worker
```bash
curl -X POST "http://localhost:8000/api/v1/workers/register" \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "test-machine-001",
    "machine_name": "Test Machine",
    "system_info": {
      "os": "Linux",
      "cpu_count": 8,
      "memory_total": 16000000000
    },
    "tools": ["claude_code", "gemini_cli"]
  }' | jq '.'
```

**預期響應：**
```json
{
  "status": "registered",
  "worker_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Worker registered successfully"
}
```

#### 3. 發送心跳
```bash
# 替換 {WORKER_ID} 為實際的 worker_id
curl -X POST "http://localhost:8000/api/v1/workers/{WORKER_ID}/heartbeat" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "idle",
    "resources": {
      "cpu_percent": 25.5,
      "memory_percent": 60.2,
      "disk_percent": 45.0
    }
  }' | jq '.'
```

**預期響應：**
```json
{
  "acknowledged": true,
  "message": "Heartbeat received"
}
```

#### 4. 查詢 Worker 列表
```bash
curl -X GET "http://localhost:8000/api/v1/workers?limit=10" | jq '.'
```

**預期響應：**
```json
{
  "workers": [
    {
      "worker_id": "550e8400-e29b-41d4-a716-446655440000",
      "machine_name": "Test Machine",
      "machine_id": "test-machine-001",
      "status": "idle",
      "tools": ["claude_code", "gemini_cli"],
      "cpu_percent": 25.5,
      "memory_percent": 60.2,
      "disk_percent": 45.0,
      "last_heartbeat": "2025-11-12T15:30:00Z",
      "registered_at": "2025-11-12T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

#### 5. 查詢 Worker 詳情
```bash
curl -X GET "http://localhost:8000/api/v1/workers/{WORKER_ID}" | jq '.'
```

#### 6. 註銷 Worker
```bash
curl -X POST "http://localhost:8000/api/v1/workers/{WORKER_ID}/unregister" | jq '.'
```

#### 7. 測試冪等性（重複註冊）
```bash
# 使用相同的 machine_id 再次註冊
curl -X POST "http://localhost:8000/api/v1/workers/register" \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "test-machine-001",
    "machine_name": "Updated Machine Name",
    "system_info": {"os": "Linux"},
    "tools": ["claude_code"]
  }' | jq '.'
```

應該返回相同的 `worker_id`，狀態為 `"updated"`。

---

## 方式 4: 使用 Swagger UI 測試

### 1. 啟動後端

```bash
make up
```

### 2. 開啟 Swagger UI

在瀏覽器開啟：http://localhost:8000/docs

### 3. 互動式測試

Swagger UI 提供了一個互動式界面：
- 可以查看所有 API 端點
- 可以直接在瀏覽器中發送請求
- 自動生成請求範例
- 即時查看響應

**步驟：**
1. 展開 `POST /api/v1/workers/register`
2. 點擊 "Try it out"
3. 修改請求 body
4. 點擊 "Execute"
5. 查看響應

---

## 常見問題

### Q1: pytest 找不到模組
```
ModuleNotFoundError: No module named 'src'
```

**解決方法：**
```bash
cd backend
pip install -r requirements.txt
```

### Q2: 數據庫連接失敗
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解決方法：**
```bash
# 確保 PostgreSQL 正在運行
docker-compose up -d postgres

# 或使用測試數據庫（SQLite）
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
pytest
```

### Q3: Redis 連接失敗

**解決方法：**
```bash
# 確保 Redis 正在運行
docker-compose up -d redis

# 檢查連接
docker-compose exec redis redis-cli ping
```

### Q4: 端口被佔用
```
Error: Port 8000 is already in use
```

**解決方法：**
```bash
# 停止佔用端口的進程
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

---

## 測試覆蓋率目標

- **單元測試:** ≥ 80%
- **整合測試:** ≥ 70%
- **整體覆蓋率:** ≥ 75%

---

## 持續集成（CI）

所有測試會在 GitHub Actions 中自動運行：
- 每次 push 到 main/develop 分支
- 每個 Pull Request

查看 `.github/workflows/ci.yml` 了解詳情。

---

## 下一步

完成 Worker Management API 測試後，可以繼續：
1. Epic 3: 任務協調與調度引擎
2. Epic 4: Flutter 可視化儀表板
3. Epic 5: AI 工具整合引擎

---

**測試愉快！** 🎉
