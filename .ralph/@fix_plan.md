# GarageSwarm 2.0 - 任務計劃

## Phase 0: 基礎設施修復 (當前)

### 高優先級 (本週)

- [x] **P0-1: WebSocket 實現** ✅ 2026-01-22
  - 文件: `backend/src/api/v1/websocket.py`
  - 實現: ConnectionManager, heartbeat, 消息處理 (576 行)

- [x] **P0-2: 結果回報端點** ✅ 2026-01-22
  - 文件: `backend/src/api/v1/workers.py`
  - 實現: POST `/api/v1/workers/{worker_id}/report-result`

- [x] **P0-3: Worker API Key 驗證** ✅ 2026-01-22
  - 文件: `backend/src/auth/worker_auth.py`
  - 實現: verify_worker_api_key, generate_worker_api_key (136 行)

- [x] **P0-4: Worker 結果回報客戶端** ✅ 2026-01-22
  - 文件: `worker-agent/src/agent/result_reporter.py`
  - 實現: ResultReporter with retry logic (403 行)

### 中優先級

- [ ] **P0-5: 基本錯誤重試邏輯**
  - 文件: `backend/src/services/task_executor.py`
  - 任務: 添加任務失敗重試機制
  - 配置: max_retries=3, retry_delay=exponential backoff

- [ ] **P0-6: 任務狀態 WebSocket 推送**
  - 文件: `backend/src/api/v1/websocket.py`
  - 任務: 實現任務狀態變更的即時推送
  - 驗收: 前端可以即時收到任務狀態更新

### 低優先級

- [ ] **P0-7: OpenAPI 文檔完善**
  - 文件: `backend/src/api/v1/*.py`
  - 任務: 添加詳細的 API 文檔和示例

---

## Phase 1: MCP 整合層 (下一階段)

### 高優先級

- [ ] **P1-1: MCP Bus 核心**
  - 目錄: `backend/src/mcp/`
  - 文件: `bus.py`, `registry.py`, `__init__.py`
  - 任務: 實現 MCP 工具匯流排管理器

- [ ] **P1-2: 遷移 Ollama 到 MCP**
  - 文件: `backend/src/mcp/servers/ollama.py`
  - 任務: 將現有 Ollama 整合轉為 MCP Server
  - 作為 Proof of Concept

- [ ] **P1-3: STDIO 傳輸層**
  - 文件: `backend/src/mcp/transports/stdio.py`
  - 任務: 實現本地進程 MCP 通訊

### 中優先級

- [ ] **P1-4: Claude Code MCP Server**
  - 文件: `backend/src/mcp/servers/claude_code.py`

- [ ] **P1-5: Gemini CLI MCP Server**
  - 文件: `backend/src/mcp/servers/gemini_cli.py`

- [ ] **P1-6: SSE 遠程傳輸**
  - 文件: `backend/src/mcp/transports/sse.py`

- [ ] **P1-7: 工具自動發現**
  - 任務: MCP 伺服器工具自動註冊

---

## Phase 2: 智能路由與記憶系統

### 高優先級

- [ ] **P2-1: 智能路由器**
  - 文件: `backend/src/services/router.py`
  - 任務: 多維度評分路由決策

- [ ] **P2-2: 短期記憶 (Redis)**
  - 文件: `backend/src/memory/stores/short_term.py`

- [ ] **P2-3: 長期記憶 (向量庫)**
  - 文件: `backend/src/memory/stores/vector.py`
  - 依賴: ChromaDB

### 中優先級

- [ ] **P2-4: 關係記憶 (圖)**
  - 文件: `backend/src/memory/stores/graph.py`

- [ ] **P2-5: 反饋學習循環**
  - 文件: `backend/src/memory/learning/feedback.py`

- [ ] **P2-6: 成本追蹤系統**
  - 文件: `backend/src/services/cost_tracker.py`

---

## Phase 3: 工作流引擎重構

### 高優先級

- [ ] **P3-1: DAG 執行器核心**
  - 文件: `backend/src/workflows/engine.py`

- [ ] **P3-2: 條件分支節點**
  - 文件: `backend/src/workflows/nodes/condition.py`

- [ ] **P3-3: 並行執行支援**
  - 文件: `backend/src/workflows/nodes/parallel.py`

- [ ] **P3-4: 人工審核節點**
  - 文件: `backend/src/workflows/nodes/human.py`

- [ ] **P3-5: 檢查點與恢復**
  - 文件: `backend/src/workflows/checkpoints.py`

### 中優先級

- [ ] **P3-6: 子工作流支援**
- [ ] **P3-7: 工作流模板系統**
- [ ] **P3-8: 可視化編輯器 API**

---

## Phase 4: 前端與可視化

- [ ] **P4-1: 儀表板核心**
- [ ] **P4-2: 工作流編輯器 (React Flow)**
- [ ] **P4-3: 任務管理界面**
- [ ] **P4-4: Worker 監控界面**
- [ ] **P4-5: 執行回放功能**
- [ ] **P4-6: 審核隊列界面**

---

## Phase 5: 多模態與外部整合

- [ ] **P5-1: 文件存儲系統 (MinIO)**
- [ ] **P5-2: ComfyUI MCP Server**
- [ ] **P5-3: 多模態輸出處理**
- [ ] **P5-4: Suno AI 整合**
- [ ] **P5-5: ElevenLabs 整合**
- [ ] **P5-6: 外部 Webhook 系統**
- [ ] **P5-7: 排程系統**

---

## Phase 6: 企業級功能

- [ ] **P6-1: 多租戶支援**
- [ ] **P6-2: RBAC 權限系統**
- [ ] **P6-3: 審計日誌**
- [ ] **P6-4: SSO 整合**
- [ ] **P6-5: API 限流**
- [ ] **P6-6: 加密存儲**

---

## 完成記錄

### 已完成任務
<!-- 完成的任務移到這裡 -->
