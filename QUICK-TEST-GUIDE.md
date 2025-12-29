# 快速測試指南

## 問題：本地環境依賴衝突

在 Windows 本地環境中，Python 依賴可能會有衝突。最可靠的測試方式是使用 Docker 環境。

---

## 🚀 方案 A: Docker 環境測試（推薦）

### 步驟 1: 啟動 Docker Desktop

1. 打開 Docker Desktop 應用程式
2. 等待 Docker 引擎啟動（右下角圖標變綠）

### 步驟 2: 啟動測試環境

```bash
# 在專案根目錄
cd C:\Users\m4932\OneDrive\Documents\Gitlab\bmad-test

# 啟動所有服務
docker-compose up -d

# 等待服務啟動（約 10-20 秒）
docker-compose ps
```

### 步驟 3: 在 Docker 容器中運行測試

```bash
# 方式 1: 進入容器運行測試
docker-compose exec backend pytest tests/unit/test_worker_service.py -v

# 方式 2: 運行所有測試
docker-compose exec backend pytest tests/ -v

# 方式 3: 生成覆蓋率報告
docker-compose exec backend pytest tests/ --cov=src --cov-report=term-missing
```

### 步驟 4: 查看結果

測試結果會直接顯示在終端。

---

## 🔧 方案 B: 使用提供的測試腳本

### 前提：Docker 正在運行

```bash
# 1. 啟動服務
make up

# 2. 手動測試 API
./test-worker-api.sh

# 或者在 PowerShell 中
bash test-worker-api.sh
```

這個腳本會：
1. 註冊一個測試 Worker
2. 發送心跳
3. 查詢列表
4. 查詢詳情
5. 測試冪等性
6. 註銷 Worker

---

## 📊 方案 C: 使用 Swagger UI 手動測試

### 步驟 1: 啟動服務

```bash
make up
```

### 步驟 2: 開啟 Swagger UI

在瀏覽器打開：http://localhost:8000/docs

### 步驟 3: 測試 API

1. 找到 `POST /api/v1/workers/register`
2. 點擊 "Try it out"
3. 修改請求 body：
   ```json
   {
     "machine_id": "test-machine-001",
     "machine_name": "My Test Machine",
     "system_info": {
       "os": "Windows",
       "cpu_count": 8
     },
     "tools": ["claude_code"]
   }
   ```
4. 點擊 "Execute"
5. 查看響應（應該返回 200 OK）

---

## ⚡ 方案 D: 簡化測試（無 Docker）

如果實在無法使用 Docker，可以做語法和邏輯檢查：

```bash
# 1. 檢查語法
cd backend
python -m py_compile src/api/v1/workers.py
python -m py_compile src/services/worker_service.py
python -m py_compile src/schemas/worker.py

# 2. 檢查導入
python -c "from src.schemas.worker import WorkerRegisterRequest; print('✓ Schemas OK')"
python -c "from src.services.worker_service import WorkerService; print('✓ Service OK')"
```

---

## 🎯 預期測試結果

### 成功的測試輸出範例

```
tests/unit/test_worker_service.py::test_register_new_worker PASSED           [ 10%]
tests/unit/test_worker_service.py::test_register_existing_worker_updates PASSED [ 20%]
tests/unit/test_worker_service.py::test_update_heartbeat PASSED             [ 30%]
tests/unit/test_worker_service.py::test_update_heartbeat_worker_not_found PASSED [ 40%]
tests/unit/test_worker_service.py::test_get_worker PASSED                   [ 50%]
tests/unit/test_worker_service.py::test_get_worker_not_found PASSED         [ 60%]
tests/unit/test_worker_service.py::test_unregister_worker PASSED            [ 70%]
tests/unit/test_worker_service.py::test_unregister_worker_not_found PASSED  [ 80%]

======================== 10 passed in 0.45s ========================
```

### API 測試成功範例

```json
{
  "status": "registered",
  "worker_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Worker registered successfully"
}
```

---

## ❓ 常見問題

### Q: Docker 無法啟動

**A:** 確保 Docker Desktop 已安裝並正在運行。

### Q: 端口 8000 被佔用

**A:**
```bash
# 停止佔用端口的進程
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Q: 測試失敗

**A:** 檢查：
1. 所有服務都正常運行：`docker-compose ps`
2. 查看後端日誌：`docker-compose logs backend`
3. 資料庫連接正常：`docker-compose exec postgres psql -U postgres -c "SELECT 1"`

---

## 📞 需要幫助？

如果遇到問題：

1. 查看完整測試指南：`TESTING.md`
2. 查看 Docker 日誌：`docker-compose logs`
3. 重新啟動服務：`make down && make up`

---

## ✅ 測試檢查清單

- [ ] Docker Desktop 已安裝並運行
- [ ] 執行 `make up` 或 `docker-compose up -d`
- [ ] 確認服務狀態：`docker-compose ps`（都是 Up）
- [ ] 執行測試或訪問 Swagger UI
- [ ] 驗證結果

---

**祝測試順利！** 🎉
