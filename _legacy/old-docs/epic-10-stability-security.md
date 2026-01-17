# Epic 10: 安全修復與穩定性強化

**Author:** Deep Analysis Agents (10 parallel agents)
**Date:** 2024-12-14
**Epic Type:** Stabilization & Security Hardening
**Priority:** P0 - Critical (Blocks Production Release)
**Estimated Duration:** 2-3 週

---

## Overview

### 觸發原因

經過 10 個並行 Agent 的深度代碼審查，發現了 **200 個問題**，按嚴重程度分類：

| 嚴重程度 | 數量 | 說明 |
|---------|------|------|
| **Critical** | 42 | 阻斷部署，必須立即修復 |
| **High** | 51 | 重要功能缺失或安全風險 |
| **Medium** | 57 | 影響穩定性和可維護性 |
| **Low** | 50 | 代碼品質和最佳實踐 |

### Epic Goal

修復所有 Critical 和 High 優先級問題，確保系統達到生產環境就緒狀態。

### Business Value

- **安全性**: 修復 CORS、認證、密鑰管理等安全漏洞
- **穩定性**: 修復數據庫遷移衝突、Services 層競態條件
- **可靠性**: 添加關鍵模組的測試覆蓋
- **完整性**: 完成 Worker Agent 核心功能實作

---

## Story Breakdown

### Phase A: 阻斷問題修復 (Days 1-3)

---

### Story 10.1: 安全漏洞緊急修復

**As a** 系統管理員，
**I want** 修復所有關鍵安全漏洞，
**So that** 系統不會被未授權訪問或攻擊。

**Priority:** P0 - Critical
**Estimated Effort:** 8 小時
**Status:** ⏳ In Progress

#### Acceptance Criteria

**AC1: CORS 配置修復**
- [ ] 修改 `backend/src/main.py:109-112`
- [ ] 將 `allow_methods=["*"]` 改為 `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]`
- [ ] 將 `allow_headers=["*"]` 改為 `["Content-Type", "Authorization", "X-Request-ID"]`
- [ ] 從環境變數讀取 `CORS_ORIGINS`

**AC2: WebSocket 認證**
- [x] ✅ WebSocket 端點已實作 (`backend/src/api/v1/websocket.py`)
- [ ] 添加 JWT token 驗證參數
- [ ] 驗證用戶對 task_id 的訪問權限
- [ ] 拒絕未授權連接

**AC3: 密鑰管理**
- [ ] 修改 `backend/src/config.py`
- [ ] 強制 `SECRET_KEY` 必須從環境變數讀取，不允許默認值
- [ ] 添加密鑰長度驗證（最少 32 字符）
- [ ] 更新 `.env.example` 說明

**AC4: Token 黑名單遷移**
- [x] ✅ JWT 認證系統已實作 (`backend/src/auth/jwt_handler.py`)
- [ ] 將內存黑名單遷移到 Redis
- [ ] 添加 TTL 自動過期機制

#### Technical Notes

```python
# CORS 修復範例
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 從環境變數讀取
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)

# WebSocket 認證範例
@router.websocket("/ws/tasks/{task_id}/logs")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: UUID,
    token: str = Query(...),  # 必須提供 token
    db: AsyncSession = Depends(get_db),
):
    # 驗證 token
    user = await verify_websocket_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    # 驗證用戶權限
    task = await get_task_with_permission(db, task_id, user.user_id)
    if not task:
        await websocket.close(code=4003)
        return
```

#### Files to Modify

| 文件 | 行號 | 修改類型 |
|-----|------|---------|
| `backend/src/main.py` | 109-112 | CORS 配置 |
| `backend/src/api/v1/websocket.py` | 410-468 | WebSocket 認證 |
| `backend/src/config.py` | 30, 37 | 密鑰驗證 |
| `backend/src/auth/jwt_handler.py` | 28-51 | Redis 黑名單 |
| `backend/src/services/redis_service.py` | - | 添加黑名單方法 |

---

### Story 10.2: 數據庫遷移衝突修復

**As a** DevOps 工程師，
**I want** 修復數據庫遷移版本衝突，
**So that** Alembic 能正確執行遷移，系統能正常啟動。

**Priority:** P0 - Critical
**Estimated Effort:** 4 小時
**Status:** ⚠️ Needs Attention

#### Acceptance Criteria

**AC1: 遷移版本號修復**
- [x] ✅ 遷移文件已存在：`003_add_user_is_active.py`, `005_add_workflow_templates.py`
- [x] ✅ 遷移順序：001 → 002 → 003 (proposals) → 003 (user_is_active) → 004 → 005
- [ ] ⚠️ 需要解決兩個 003 版本號衝突

**AC2: 欄位名稱同步**
- [ ] 檢查 `backend/src/models/activity_log.py` 欄位名稱
- [ ] 確保與數據庫遷移一致

**AC3: env.py 模型導入**
- [ ] 修改 `backend/alembic/env.py`
- [ ] 添加缺失的模型導入：`Proposal`, `ProposalVote`, `WorkflowTemplate`, `TemplateStep`

**AC4: 遷移驗證**
- [ ] 運行 `alembic heads` 確認單一 head
- [ ] 運行 `alembic upgrade head` 驗證遷移
- [ ] 修復任何遷移錯誤

#### Files to Modify

| 文件 | 修改類型 |
|-----|---------|
| `backend/alembic/versions/003_add_user_is_active.py` | 重命名為 005 |
| `backend/alembic/versions/004_add_performance_indexes.py` | 更新 down_revision |
| `backend/src/models/activity_log.py` | 修復欄位名 |
| `backend/alembic/env.py` | 添加模型導入 |
| `backend/alembic/versions/006_add_templates.py` | 新建遷移 |

---

### Phase B: 認證與 API 強化 (Days 4-6)

---

### Story 10.3: Backend API 認證強化

**As a** 安全審計員，
**I want** 所有 API 端點都有適當的認證保護，
**So that** 未授權用戶無法訪問或修改系統數據。

**Priority:** P0 - Critical
**Estimated Effort:** 12 小時

#### Acceptance Criteria

**AC1: Tasks API 認證**
- [ ] 修改 `backend/src/api/v1/tasks.py`
- [ ] 為所有端點添加 `Depends(get_current_active_user)`
- [ ] 驗證用戶只能訪問自己的任務

**AC2: Workers API 認證**
- [ ] 修改 `backend/src/api/v1/workers.py`
- [ ] 添加認證依賴
- [ ] Worker 註冊需要 API Key 或 Service Account

**AC3: Subtasks API 認證**
- [ ] 修改 `backend/src/api/v1/subtasks.py`
- [ ] 添加認證和權限檢查

**AC4: Checkpoints API 認證**
- [ ] 修改 `backend/src/api/v1/checkpoints.py`
- [ ] 驗證用戶對 checkpoint 的操作權限

**AC5: Templates API 認證**
- [ ] 修改 `backend/src/api/v1/templates.py`
- [ ] 公開模板允許讀取，修改需要認證

**AC6: Evaluations API 認證**
- [ ] 修改 `backend/src/api/v1/evaluations.py`
- [ ] 添加認證依賴

**AC7: Metrics API 保護**
- [ ] 修改 `backend/src/api/v1/metrics.py`
- [ ] 添加 API Key 或內部網路限制

**AC8: Health API 詳細端點保護**
- [ ] 修改 `backend/src/api/v1/health.py`
- [ ] `/health/detailed` 需要認證
- [ ] 移除 DEBUG 模式信息洩漏

#### Technical Notes

```python
# 認證依賴範例
from src.auth.dependencies import get_current_active_user

@router.get("/tasks")
async def list_tasks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # 只返回當前用戶的任務
    return await task_service.get_user_tasks(db, current_user.user_id)
```

#### Files to Modify

| 文件 | 端點數量 | 修改類型 |
|-----|---------|---------|
| `backend/src/api/v1/tasks.py` | 5 | 添加認證 |
| `backend/src/api/v1/workers.py` | 6 | 添加認證 |
| `backend/src/api/v1/subtasks.py` | 10 | 添加認證 |
| `backend/src/api/v1/checkpoints.py` | 4 | 添加認證 |
| `backend/src/api/v1/templates.py` | 5 | 添加認證 |
| `backend/src/api/v1/evaluations.py` | 4 | 添加認證 |
| `backend/src/api/v1/metrics.py` | 1 | 添加保護 |
| `backend/src/api/v1/health.py` | 1 | 移除敏感信息 |

---

### Phase C: Worker Agent 完善 (Days 7-9)

---

### Story 10.4: Worker Agent 核心功能完善

**As a** Worker Agent，
**I want** 所有核心功能正確實作，
**So that** 我能正常執行和管理任務。

**Priority:** P0 - Critical
**Estimated Effort:** 16 小時

#### Acceptance Criteria

**AC1: 工具註冊實作**
- [ ] 修改 `worker-agent/src/main.py:99-103`
- [ ] 實作 AI 工具註冊邏輯
- [ ] 根據配置載入 Claude Code, Gemini CLI, Ollama

**AC2: 任務取消實作**
- [ ] 修改 `worker-agent/src/agent/core.py:561`
- [ ] 實作 `_handle_task_cancel()` 方法
- [ ] 正確終止運行中的任務
- [ ] 清理資源並回報狀態

**AC3: Windows 兼容性修復**
- [ ] 修改 `worker-agent/src/agent/monitor.py:24`
- [ ] 使用跨平台的磁盤路徑檢查

**AC4: 統一 Retry 框架**
- [ ] 創建 `worker-agent/src/utils/retry.py`
- [ ] 統一所有工具的重試邏輯
- [ ] 支持指數退避和自定義異常

**AC5: 阻塞式速率限制修復**
- [ ] 修改 `worker-agent/src/tools/gemini_cli.py:221`
- [ ] 將 `time.sleep()` 改為 `await asyncio.sleep()`

**AC6: 工具初始化驗證**
- [ ] 修改 `worker-agent/src/agent/core.py:95-100`
- [ ] 在 `register_tool()` 中調用 `validate_config()` 和 `health_check()`

**AC7: WebSocket 競態條件修復**
- [ ] 修改 `worker-agent/src/agent/websocket_client.py:247`
- [ ] 添加鎖機制保護共享狀態

#### Technical Notes

```python
# 工具註冊實作範例
async def _register_tools(self):
    """Register AI tools based on configuration"""
    tool_configs = self.config.get("tools", {})

    if "claude_code" in tool_configs:
        from src.tools.claude_code import ClaudeCodeTool
        tool = ClaudeCodeTool(tool_configs["claude_code"])
        if await tool.validate_config() and await tool.health_check():
            self.register_tool("claude_code", tool)
            logger.info("Registered Claude Code tool")

    if "gemini_cli" in tool_configs:
        from src.tools.gemini_cli import GeminiCLITool
        tool = GeminiCLITool(tool_configs["gemini_cli"])
        if await tool.validate_config() and await tool.health_check():
            self.register_tool("gemini_cli", tool)
            logger.info("Registered Gemini CLI tool")

    if "ollama" in tool_configs:
        from src.tools.ollama import OllamaTool
        tool = OllamaTool(tool_configs["ollama"])
        if await tool.validate_config() and await tool.health_check():
            self.register_tool("ollama", tool)
            logger.info("Registered Ollama tool")
```

#### Files to Modify

| 文件 | 行號 | 修改類型 |
|-----|------|---------|
| `worker-agent/src/main.py` | 99-103 | 實作工具註冊 |
| `worker-agent/src/agent/core.py` | 561, 95-100 | 任務取消、驗證 |
| `worker-agent/src/agent/monitor.py` | 24 | Windows 兼容 |
| `worker-agent/src/utils/retry.py` | 新建 | 統一 Retry |
| `worker-agent/src/tools/gemini_cli.py` | 221 | 異步 sleep |
| `worker-agent/src/agent/websocket_client.py` | 247 | 鎖機制 |

---

### Phase D: 測試與穩定性 (Days 10-14)

---

### Story 10.5: 關鍵模組測試套件

**As a** QA 工程師，
**I want** 為所有關鍵模組添加測試，
**So that** 我們能確保代碼品質和防止回歸。

**Priority:** High
**Estimated Effort:** 20 小時

#### Acceptance Criteria

**AC1: Templates API 測試**
- [ ] 創建 `backend/tests/integration/test_templates_api.py`
- [ ] 覆蓋所有 CRUD 操作
- [ ] 測試模板應用邏輯

**AC2: Metrics API 測試**
- [ ] 創建 `backend/tests/integration/test_metrics_api.py`
- [ ] 驗證 Prometheus metrics 格式

**AC3: Checkpoint Trigger 測試**
- [ ] 創建 `backend/tests/unit/test_checkpoint_trigger.py`
- [ ] 測試所有觸發條件

**AC4: Template Service 測試**
- [ ] 創建 `backend/tests/unit/test_template_service.py`
- [ ] 測試業務邏輯

**AC5: Worker Agent Connection 測試**
- [ ] 創建 `worker-agent/tests/unit/test_connection.py`
- [ ] 測試 WebSocket 連接管理

**AC6: Worker Agent Core 測試**
- [ ] 創建 `worker-agent/tests/unit/test_core.py`
- [ ] 測試 Agent 核心邏輯

**AC7: Worker Agent WebSocket Client 測試**
- [ ] 創建 `worker-agent/tests/unit/test_websocket_client.py`
- [ ] 測試重連和心跳邏輯

#### Files to Create

| 文件 | 測試數量 | 覆蓋模組 |
|-----|---------|---------|
| `backend/tests/integration/test_templates_api.py` | 15+ | Templates API |
| `backend/tests/integration/test_metrics_api.py` | 5+ | Metrics API |
| `backend/tests/unit/test_checkpoint_trigger.py` | 20+ | CheckpointTrigger |
| `backend/tests/unit/test_template_service.py` | 15+ | TemplateService |
| `worker-agent/tests/unit/test_connection.py` | 10+ | Connection |
| `worker-agent/tests/unit/test_core.py` | 15+ | Core |
| `worker-agent/tests/unit/test_websocket_client.py` | 10+ | WebSocketClient |

---

### Story 10.6: Services 層錯誤修復

**As a** 後端開發者，
**I want** 修復 Services 層的邏輯錯誤和競態條件，
**So that** 系統能正確處理任務調度和檢查點。

**Priority:** High
**Estimated Effort:** 12 小時

#### Acceptance Criteria

**AC1: CheckpointTrigger GROUP BY 修復**
- [ ] 修改 `backend/src/services/checkpoint_trigger.py:307-350`
- [ ] 修正 `_check_correction_cycle_limit()` 的 GROUP BY 邏輯

**AC2: TaskAllocator pop_from_queue 修復**
- [ ] 修改 `backend/src/services/task_allocator.py:189`
- [ ] 傳入正確的 subtask_id 參數

**AC3: TaskScheduler 失敗恢復**
- [ ] 修改 `backend/src/services/task_scheduler.py:553-561`
- [ ] 實作失敗恢復策略

**AC4: Redis 連接重試**
- [ ] 修改 `backend/src/services/redis_service.py`
- [ ] 添加重試機制和故障恢復

**AC5: 數據庫-Redis 同步**
- [ ] 修改 `backend/src/services/task_allocator.py:378-388`
- [ ] 確保數據庫和 Redis 狀態一致

**AC6: ReviewService 語義修復**
- [ ] 修改 `backend/src/services/review_service.py:128-140`
- [ ] 區分輸入和輸出字段

#### Files to Modify

| 文件 | 行號 | 問題類型 |
|-----|------|---------|
| `checkpoint_trigger.py` | 307-350 | GROUP BY 邏輯 |
| `task_allocator.py` | 189, 378-388 | 參數錯誤、競態條件 |
| `task_scheduler.py` | 553-561 | 失敗恢復 |
| `redis_service.py` | 全局 | 重試機制 |
| `review_service.py` | 128-140 | 語義混淆 |

---

### Story 10.7: Configuration 與環境變數修復

**As a** DevOps 工程師，
**I want** 修復配置和環境變數問題，
**So that** 系統能在不同環境中正確運行。

**Priority:** High
**Estimated Effort:** 6 小時

#### Acceptance Criteria

**AC1: Docker Compose 語法修復**
- [ ] 修改 `docker-compose.yml:60-61`
- [ ] 修復 shell 命令語法錯誤

**AC2: CI/CD 環境變數**
- [ ] 修改 `.github/workflows/ci.yml`
- [ ] 添加 `ANTHROPIC_API_KEY` 和 `GOOGLE_API_KEY` secrets

**AC3: 依賴版本統一**
- [ ] ⚠️ 統一 `isort` 版本（backend: 5.12.0, worker-agent: 5.13.0）
- [ ] 建議統一為 5.13.0
- [x] ✅ `coverage` 目標已達成（85%+）

**AC4: Frontend WS URL 修復**
- [ ] 修改 `frontend/lib/config/env_config.dart:11`
- [ ] 修正 WebSocket URL 路徑

**AC5: 訊息格式統一**
- [ ] 修改 `frontend/lib/services/websocket_service.dart:160-164`
- [ ] 統一前後端 WebSocket 訊息格式

#### Files to Modify

| 文件 | 修改類型 |
|-----|---------|
| `docker-compose.yml` | Shell 語法修復 |
| `.github/workflows/ci.yml` | 環境變數 |
| `backend/requirements.txt` | 版本統一 |
| `worker-agent/requirements.txt` | 版本統一 |
| `frontend/lib/config/env_config.dart` | URL 修復 |
| `frontend/lib/services/websocket_service.dart` | 訊息格式 |

---

## Implementation Schedule

```
Week 1 (Days 1-7):
├── Day 1-2: Story 10.1 (安全漏洞) ⚡ P0
├── Day 3: Story 10.2 (數據庫遷移) ⚡ P0
├── Day 4-5: Story 10.3 (API 認證) ⚡ P0
├── Day 6-7: Story 10.4 (Worker Agent) ⚡ P0

Week 2 (Days 8-14):
├── Day 8-10: Story 10.5 (測試套件)
├── Day 11-12: Story 10.6 (Services 修復)
├── Day 13-14: Story 10.7 (配置修復)

Week 3 (Days 15-17):
├── 整合測試
├── 回歸測試
└── 部署驗證
```

---

## Success Criteria

Epic 完成後應達到：

- [ ] 所有 42 個 Critical 問題已修復 (進度: ~30%)
- [ ] 所有 51 個 High 問題已修復 (進度: ~20%)
- [x] ✅ 測試覆蓋率達到 80%+ (當前: 85%+)
- [ ] 安全掃描無 Critical/High 發現
- [ ] CI/CD 流程全部通過
- [ ] 可以在生產環境部署

## 當前進度總結 (2025-12-22)

### 已完成的主要功能
1. ✅ JWT 認證系統 (Epic 10.3 部分完成)
2. ✅ WebSocket 實時日誌串流 (Epic 10.1 AC2 部分完成)
3. ✅ 錯誤處理系統 (Epic 9 - Story 9.3)
4. ✅ Agent 協作與審查機制 (Epic 6)
5. ✅ 重試機制與指數退避

### 進行中的工作
1. ⏳ CORS 配置修復 (Story 10.1 AC1)
2. ⏳ WebSocket 認證加強 (Story 10.1 AC2)
3. ⏳ 密鑰管理改進 (Story 10.1 AC3)
4. ⏳ 數據庫遷移衝突解決 (Story 10.2)

### 待完成的關鍵任務
1. ❌ API 端點認證保護 (Story 10.3)
2. ❌ Worker Agent 核心功能完善 (Story 10.4)
3. ❌ 關鍵模組測試套件 (Story 10.5)
4. ❌ Services 層錯誤修復 (Story 10.6)
5. ❌ 配置與環境變數修復 (Story 10.7)

### 測試覆蓋率狀態
- Backend Unit Tests: 150+ tests
- Backend Integration Tests: 58+ tests
- E2E Tests: 69 tests
- Worker Agent Tests: 50+ tests
- Error Handling Tests: 51 tests (96%+ pass rate)
- **總體覆蓋率**: ~85%

---

## Risk Assessment

| 風險 | 可能性 | 影響 | 緩解措施 |
|-----|--------|------|---------|
| 修復引入新問題 | 中 | 高 | 完整的測試覆蓋 |
| 遷移失敗 | 低 | 高 | 備份和回滾計劃 |
| 認證影響現有功能 | 中 | 中 | 分階段部署 |
| 時間不足 | 中 | 中 | 優先處理 P0 問題 |

---

## References

- [Deep Analysis Report](./DEEP-ANALYSIS-REPORT.md)
- [Architecture Document](./architecture.md)
- [PRD](./PRD.md)
- [Sprint 1 Plan](./sprint-1-plan.md)
