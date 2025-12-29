# Multi-Agent on the Web - Epic Breakdown

**Author:** sir
**Date:** 2025-11-11
**Project Level:** MVP (Greenfield)
**Target Scale:** 中型分布式系統平台

---

## Overview

This document provides the complete epic and story breakdown for **Multi-Agent on the Web**, decomposing the requirements from the [PRD](./PRD.md) into implementable stories optimized for 200k context development agents.

### Epic Structure Summary

為了實現 **Multi-Agent on the Web** 平台，我們將需求組織成 **9 個 Epic**，按照自然的技術依賴和用戶價值遞增順序排列：

#### Phase 1: Foundation & Core Infrastructure (Weeks 1-3)
**Epic 1: 項目基礎設施與核心架構**
- **價值：** 建立項目骨架，讓所有後續開發有堅實基礎
- **範圍：** 項目初始化、數據庫設計、API 框架、部署配置
- **為什麼這個 Epic：** Greenfield 項目必須先建立基礎，這是所有後續工作的前提

#### Phase 2: Distributed System Core (Weeks 4-6)
**Epic 2: Worker Agent 管理系統**
- **價值：** 讓分布式 Worker 能夠註冊、心跳、監控資源
- **範圍：** Worker 註冊、心跳機制、資源監控、生命週期管理
- **為什麼這個 Epic：** Worker 是分布式系統的核心，必須先建立 Worker 管理

**Epic 3: 任務協調與調度引擎**
- **價值：** 讓後端能夠接收任務、分解、分配給 Worker
- **範圍：** 任務提交、智能分解、智能分配、並行調度
- **為什麼這個 Epic：** 有了 Worker 管理後，需要能夠協調任務

#### Phase 3: User Interface (Weeks 7-9)
**Epic 4: Flutter 可視化儀表板**
- **價值：** 讓用戶能夠看到系統狀態、提交任務、監控執行
- **範圍：** 儀表板 UI、機器列表、任務列表、實時連接
- **為什麼這個 Epic：** 前端讓用戶能夠與系統交互，是可用性的關鍵

#### Phase 4: AI Integration (Weeks 10-12)
**Epic 5: AI 工具整合引擎**
- **價值：** 讓 Worker 能夠執行 Claude、Gemini、Local LLM 任務
- **範圍：** MCP 整合、Gemini CLI 整合、Ollama 整合、任務執行
- **為什麼這個 Epic：** AI 工具是平台的核心能力

#### Phase 5: Quality & Collaboration (Weeks 13-15)
**Epic 6: Agent 協作與審查機制**
- **價值：** 實現 Agent 互相審查，提升質量
- **範圍：** 審查工作流、並行協調、結果聚合
- **為什麼這個 Epic：** 多 Agent 協作是平台的差異化特性

**Epic 7: 量化評估框架**
- **價值：** 自動評估 Agent 輸出質量，減少人工審查負擔
- **範圍：** Code Quality、Completeness、Security 評估器、聚合評分
- **為什麼這個 Epic：** 評估框架是質量保證的創新核心

**Epic 8: 人類檢查點與糾偏系統**
- **價值：** 讓用戶在關鍵時刻介入，實現"半自動"
- **範圍：** 檢查點觸發、檢查點 UI、糾偏介面、決策處理
- **為什麼這個 Epic：** 半自動人機協作是平台的核心創新

#### Phase 6: Polish & Launch (Weeks 16-18)
**Epic 9: 測試、優化與文檔**
- **價值：** 確保質量、性能、可用性達到發布標準
- **範圍：** 端到端測試、性能測試、錯誤處理、用戶文檔
- **為什麼這個 Epic：** 發布前的質量保證

---

### Epic Sequencing & Dependencies

```
Epic 1: Foundation
  ↓
Epic 2: Worker Management ─┐
  ↓                        │
Epic 3: Task Coordination  │
  ↓                        │
Epic 4: Flutter UI ←───────┘
  ↓
Epic 5: AI Integration
  ↓
Epic 6: Agent Collaboration ─┐
Epic 7: Evaluation Framework  ├→ 可並行
Epic 8: Human Checkpoints ───┘
  ↓
Epic 9: Testing & Launch
```

### Success Metrics per Epic

每個 Epic 完成後應該達到的里程碑：

- **Epic 1**: 項目能夠本地運行，數據庫和 API 框架就緒
- **Epic 2**: Worker 能夠註冊、心跳、上報資源
- **Epic 3**: 後端能夠接收任務、分解、分配給 Worker
- **Epic 4**: 用戶能夠在 UI 上看到機器和任務狀態
- **Epic 5**: Worker 能夠執行 Claude/Gemini/Ollama 任務
- **Epic 6**: Agent 能夠互相審查並並行工作
- **Epic 7**: Agent 輸出能夠自動評分（3 個維度）
- **Epic 8**: 用戶能夠在檢查點介入並糾偏
- **Epic 9**: 平台通過所有測試，文檔完整，準備發布

---

## Epic 1: 項目基礎設施與核心架構

**Epic Goal:** 建立項目的基礎骨架，包括數據庫設計、API 框架、基礎配置，為所有後續開發提供堅實基礎。

**Business Value:** 這是 Greenfield 項目的起點，沒有這個基礎，後續所有開發都無法進行。

**Estimated Duration:** 2-3 週

---

### Story 1.1: 項目初始化與開發環境配置

**As a** 開發者，
**I want** 建立完整的項目結構和開發環境，
**So that** 團隊能夠開始開發並保持一致的開發體驗。

**Acceptance Criteria:**

**Given** 空白的代碼倉庫
**When** 執行項目初始化腳本
**Then**
- 創建標準的 monorepo 結構（backend/, frontend/, worker-agent/, docs/）
- 配置 Python 虛擬環境和依賴管理（Poetry/pip-tools）
- 配置 Flutter 項目結構
- 配置 Git hooks（pre-commit, commit-msg）
- 創建 .gitignore 和 .env.example
- 生成 README.md 和 CONTRIBUTING.md

**And** 開發環境配置文件就緒
- Docker Compose 配置（PostgreSQL, Redis, Backend）
- Makefile 或 scripts/ 目錄包含常用命令
- VS Code / IDE 推薦配置

**Prerequisites:** 無（第一個 Story）

**Technical Notes:**
- 使用 Poetry 管理 Python 依賴（backend + worker-agent）
- 使用 Flutter 3.x+ 初始化前端項目
- Docker Compose 用於本地開發環境
- 考慮使用 Nx/Turborepo（可選）進行 monorepo 管理
- 設置 pre-commit hooks：black, isort, pylint

---

### Story 1.2: PostgreSQL 數據庫設計與 ORM 配置

**As a** 後端開發者，
**I want** 設計並實現核心數據模型，
**So that** 系統能夠持久化存儲 Worker、Task、Checkpoint 等數據。

**Acceptance Criteria:**

**Given** 數據庫設計需求（從 PRD 提取）
**When** 執行數據庫遷移
**Then**
- 創建 `workers` 表（worker_id, machine_name, status, system_info, tools, resources, last_heartbeat）
- 創建 `tasks` 表（task_id, task_type, description, requirements, status, created_at, completed_at）
- 創建 `subtasks` 表（subtask_id, task_id, assigned_worker, subtask_data, status, result, evaluation_score）
- 創建 `checkpoints` 表（checkpoint_id, subtask_id, checkpoint_type, agent_output, review_notes, user_decision, user_feedback）
- 所有主鍵使用 UUID
- 外鍵約束正確設置
- 索引優化（last_heartbeat, status, task_id）

**And** SQLAlchemy ORM 模型定義
- 所有表對應的 Python 模型類
- 關聯關係定義（ForeignKey, relationship）
- Alembic 遷移腳本

**Prerequisites:** Story 1.1

**Technical Notes:**
- 使用 SQLAlchemy 2.x 的新語法
- 使用 Alembic 進行數據庫遷移
- JSONB 列用於靈活的嵌套數據（system_info, subtask_data）
- 考慮軟刪除（deleted_at 列）
- 在 Docker Compose 中配置 PostgreSQL 15+

---

### Story 1.3: Redis 數據結構設計與連接配置

**As a** 後端開發者，
**I want** 設計並配置 Redis 用於實時狀態管理，
**So that** 系統能夠快速讀寫 Worker 和 Task 的實時狀態。

**Acceptance Criteria:**

**Given** Redis 運行在本地（Docker Compose）
**When** 後端應用啟動
**Then**
- Redis 連接池配置正確（使用 redis-py 或 aioredis）
- 定義 Worker 實時狀態 Key 結構：
  - `workers:{worker_id}:status` → "online" | "offline" | "busy"
  - `workers:{worker_id}:current_task` → task_id
- 定義 Task 實時狀態 Key 結構：
  - `tasks:{task_id}:status` → "queued" | "in_progress" | "waiting_checkpoint" | "completed" | "failed"
  - `tasks:{task_id}:progress` → JSON {current_step, total_steps, percentage}
- 定義 Task Queue：
  - `task_queue` → List of task_ids
- 創建 RedisClient 工具類封裝常用操作

**And** 連接測試通過
- 能夠讀寫測試數據
- 連接斷開後能夠自動重連

**Prerequisites:** Story 1.1

**Technical Notes:**
- 使用 Redis 7+
- 考慮使用 asyncio-compatible Redis 客戶端（aioredis）
- 設置合理的 TTL（Worker status: 120s）
- 在 Docker Compose 中配置 Redis
- 使用 Redis Pub/Sub 用於實時事件（為後續 WebSocket 做準備）

---

### Story 1.4: FastAPI 後端框架搭建

**As a** 後端開發者，
**I want** 建立 FastAPI 應用骨架，
**So that** 能夠開始開發 REST API 端點。

**Acceptance Criteria:**

**Given** Python 項目結構就緒
**When** 啟動 FastAPI 應用
**Then**
- FastAPI app 能夠啟動並監聽端口（默認 8000）
- 項目結構遵循最佳實踐
- 配置 CORS（允許 Flutter 前端連接）
- 配置環境變量管理（pydantic-settings）
- 健康檢查端點：`GET /health` 返回 200
- 日誌配置完成（structlog 或 loguru）

**Prerequisites:** Story 1.1, 1.2, 1.3

**Technical Notes:**
- FastAPI 0.100+, Pydantic v2
- 使用依賴注入管理 DB session 和 Redis client
- Uvicorn 作為 ASGI 服務器

---

### Story 1.5: Worker Agent Python SDK 基礎框架

**As a** Worker Agent 開發者，
**I want** 建立 Worker Agent 的基礎框架，
**So that** 能夠開始開發 Worker 的核心功能。

**Acceptance Criteria:**

**Given** Worker Agent 項目結構需求
**When** Worker Agent 啟動
**Then**
- Worker Agent 能夠成功啟動（Python CLI）
- 項目結構清晰（core.py, connection.py, executor.py, monitor.py, tools/）
- 配置文件加載（YAML）
- 能夠生成或讀取 machine_id（UUID，持久化）
- 基礎類結構定義（WorkerAgent, ConnectionManager, ResourceMonitor, TaskExecutor）

**Prerequisites:** Story 1.1

**Technical Notes:**
- Python 3.11+, asyncio, httpx, websockets, psutil, pyyaml

---

### Story 1.6: Docker Compose 多容器編排配置

**As a** 開發者，
**I want** 配置 Docker Compose 讓所有服務能夠一起運行，
**So that** 本地開發環境能夠一鍵啟動。

**Acceptance Criteria:**

**Given** Docker 和 Docker Compose 已安裝
**When** 執行 `docker-compose up`
**Then**
- postgres, redis, backend 容器成功啟動
- 容器之間網絡連接正常
- 數據持久化配置（volumes）
- 代碼熱重載（backend 掛載本地目錄）
- 提供便捷的 Makefile 命令

**Prerequisites:** Story 1.2, 1.3, 1.4

**Technical Notes:**
- Docker Compose 3.8+, 命名 volumes, healthcheck

---

### Story 1.7: CI/CD 基礎配置

**As a** DevOps 工程師，
**I want** 配置基礎的 CI/CD 流程，
**So that** 代碼推送後能夠自動運行測試和檢查。

**Acceptance Criteria:**

**Given** GitHub/GitLab 倉庫配置
**When** 代碼推送到 main 分支
**Then**
- 自動運行 Linting（black, isort, pylint）
- 自動運行單元測試（pytest）
- 自動檢查代碼覆蓋率
- 測試失敗時阻止合併

**Prerequisites:** Story 1.1, 1.4

**Technical Notes:**
- GitHub Actions 或 GitLab CI, pytest, codecov

---

## Epic 2: Worker Agent 管理系統

**Epic Goal:** 實現分布式 Worker Agent 的註冊、心跳、資源監控和生命週期管理。

**Business Value:** Worker 是分布式系統的基石，穩定的 Worker 管理是整個系統運作的前提。

**Estimated Duration:** 2-3 週

---

### Story 2.1: Worker 註冊 API 端點

**As a** Worker Agent，
**I want** 能夠向後端註冊自己，
**So that** 後端知道我的存在和能力。

**Acceptance Criteria:**

**Given** 後端 API 運行中
**When** Worker Agent 發送 `POST /api/v1/workers/register`
**Then**
- 驗證請求數據（machine_id, machine_name, system_info, tools）
- 在 PostgreSQL `workers` 表創建或更新記錄
- 在 Redis 設置 `workers:{worker_id}:status` = "online"
- 返回 200 響應：`{"status": "registered", "worker_id": "uuid"}`
- 重複註冊時更新記錄（冪等性）

**Prerequisites:** Story 1.2, 1.3, 1.4

**Technical Notes:**
- API 路由：`backend/app/api/v1/workers.py`
- Service: `backend/app/services/worker_service.py`
- 使用事務確保 PostgreSQL 和 Redis 同步

---

### Story 2.2: Worker 心跳機制實現

**As a** Worker Agent，
**I want** 定期發送心跳給後端，
**So that** 後端知道我仍然在線。

**Acceptance Criteria:**

**Given** Worker 已註冊
**When** Worker 每 30 秒發送 `POST /api/v1/workers/{worker_id}/heartbeat`
**Then**
- 請求體包含資源數據（cpu_percent, memory_percent, disk_percent）
- 後端更新 `workers.last_heartbeat` 和 Redis 狀態
- 返回 200：`{"acknowledged": true}`
- Worker 端實現異步心跳循環（asyncio）
- 後端定時任務檢測 90 秒未心跳的 Worker 標記為 offline

**Prerequisites:** Story 2.1, 1.5

**Technical Notes:**
- Worker 端：asyncio.sleep(30)
- 後端：APScheduler 定時任務

---

### Story 2.3: Worker 資源監控實現

**As a** Worker Agent，
**I want** 實時監控系統資源，
**So that** 後端能夠根據資源情況智能分配任務。

**Acceptance Criteria:**

**Given** Worker Agent 運行中
**When** 資源監控模塊啟動
**Then**
- 使用 psutil 監控 CPU、內存、磁盤使用率
- 每次心跳時包含最新資源數據
- ResourceMonitor 類實現（agent/monitor.py）
- 跨平台兼容性（Windows/Linux/macOS）

**Prerequisites:** Story 2.2

**Technical Notes:**
- psutil.cpu_percent(), virtual_memory(), disk_usage()

---

### Story 2.4: Worker 列表查詢 API

**As a** 前端開發者，
**I want** 查詢所有 Worker 的列表和狀態，
**So that** 能夠在 UI 上顯示機器信息。

**Acceptance Criteria:**

**Given** 後端有多個已註冊的 Worker
**When** 前端請求 `GET /api/v1/workers`
**Then**
- 返回 Worker 列表（worker_id, machine_name, status, tools, resources, last_heartbeat）
- 支持查詢參數（status, limit, offset）
- 從 Redis 讀取實時狀態，從 PostgreSQL 讀取靜態信息
- 響應時間 < 100ms

**Prerequisites:** Story 2.1, 2.2, 2.3

**Technical Notes:**
- 結合 PostgreSQL 和 Redis 數據
- 考慮緩存（TTL 5 秒）

---

### Story 2.5: Worker 詳情查詢 API

**As a** 前端開發者，
**I want** 查詢單個 Worker 的詳細信息，
**So that** 能夠在 UI 上顯示 Worker 詳情頁面。

**Acceptance Criteria:**

**Given** Worker ID
**When** 前端請求 `GET /api/v1/workers/{worker_id}`
**Then**
- 返回 Worker 詳細信息（system_info, current_task）
- 如果 Worker 正在執行任務，包含 `current_task` 字段
- Worker 不存在時返回 404

**Prerequisites:** Story 2.4

**Technical Notes:**
- 結合 PostgreSQL 和 Redis 數據

---

### Story 2.6: Worker 優雅關閉機制

**As a** Worker Agent，
**I want** 在收到關閉信號時優雅地退出，
**So that** 正在執行的任務不會被中斷。

**Acceptance Criteria:**

**Given** Worker 正在運行
**When** 收到 SIGINT 或 SIGTERM 信號
**Then**
- Worker 停止接收新任務
- 等待當前任務完成（最多 60 秒）
- 發送最後一次心跳，status="offline"
- 清理資源（關閉連接、保存狀態）
- 發送 `POST /api/v1/workers/{worker_id}/unregister`

**Prerequisites:** Story 2.2

**Technical Notes:**
- signal.signal 捕獲信號
- asyncio shutdown 機制

---

## Epic 3: 任務協調與調度引擎

**Epic Goal:** 實現任務提交、智能分解、智能分配和並行調度功能。

**Business Value:** 這是平台的核心協調能力，能夠將複雜任務拆分並分配給最合適的 Worker。

**Estimated Duration:** 2-3 週

---

### Story 3.1: 任務提交 API 端點

**As a** 前端用戶，
**I want** 能夠提交新任務，
**So that** 系統能夠開始執行我的任務。

**Acceptance Criteria:**

**Given** 用戶已連接到系統
**When** 提交 `POST /api/v1/tasks`
**Then**
- 請求體包含（task_type, description, requirements, checkpoint_frequency）
- 在 PostgreSQL `tasks` 表創建記錄
- 在 Redis 設置 `tasks:{task_id}:status` = "queued"
- 將任務加入 Redis `task_queue`
- 返回 201：`{"task_id": "uuid", "status": "queued"}`
- description 支持 Markdown

**Prerequisites:** Story 1.4, 1.2, 1.3

**Technical Notes:**
- API: `backend/app/api/v1/tasks.py`
- Service: `backend/app/services/task_service.py`

---

### Story 3.2: 任務分解邏輯實現

**As a** 任務協調引擎，
**I want** 能夠將大任務分解為多個子任務，
**So that** 可以並行執行。

**Acceptance Criteria:**

**Given** 新提交的任務（status="queued"）
**When** 任務分解服務處理該任務
**Then**
- 根據 task_type 和 description 分析任務
- 生成多個子任務（subtask_id, task_id, subtask_type, subtask_data, dependencies）
- 在 PostgreSQL `subtasks` 表創建記錄
- 更新父任務的 estimated_subtasks
- 簡單規則引擎（MVP）：develop_feature → 代碼生成 + 審查 + 測試 + 文檔
- 使用 DAG 表示依賴

**Prerequisites:** Story 3.1

**Technical Notes:**
- Service: `backend/app/services/task_decomposer.py`
- MVP 使用規則引擎，未來可用 LLM
- 使用 networkx 管理 DAG

---

### Story 3.3: 智能任務分配算法

**As a** 任務協調引擎，
**I want** 根據 Worker 的能力和資源分配任務，
**So that** 任務分配給最合適的 Worker。

**Acceptance Criteria:**

**Given** 待分配的子任務和在線 Worker
**When** 任務分配器運行
**Then**
- 計算最佳 Worker（工具匹配 50% + 資源評分 30% + 隱私評分 20%）
- 更新 `subtasks.assigned_worker`
- 在 Redis 設置 `workers:{worker_id}:current_task`
- 無可用 Worker 時保持在隊列，每 30 秒重試

**Prerequisites:** Story 3.2, Story 2.4

**Technical Notes:**
- Service: `backend/app/services/task_allocator.py`
- 加權評分算法

---

### Story 3.4: 並行調度引擎實現

**As a** 任務協調引擎，
**I want** 能夠並行調度多個無依賴的子任務，
**So that** 充分利用多個 Worker 實現並行加速。

**Acceptance Criteria:**

**Given** 任務的多個子任務已分解
**When** 調度引擎運行
**Then**
- 識別所有無依賴（或依賴已完成）的子任務
- 並行分配這些子任務給不同 Worker
- 更新子任務狀態為 "assigned"
- 使用 DAG 追蹤依賴
- 子任務完成後檢查新的可執行子任務
- 限制並發（單 Worker 最多 1 任務，系統最多 20 任務）

**Prerequisites:** Story 3.3

**Technical Notes:**
- Service: `backend/app/services/task_scheduler.py`
- APScheduler 定期運行調度器
- asyncio.gather 並行處理

---

### Story 3.5: 任務狀態查詢 API

**As a** 前端開發者，
**I want** 查詢任務的當前狀態和進度，
**So that** 在 UI 上實時顯示任務執行情況。

**Acceptance Criteria:**

**Given** 任務 ID
**When** 前端請求 `GET /api/v1/tasks/{task_id}`
**Then**
- 返回任務詳情（task_id, status, subtasks[], progress）
- 包含所有子任務的狀態和評分
- 從 Redis 讀取實時狀態，從 PostgreSQL 讀取靜態數據
- 任務不存在返回 404

**Prerequisites:** Story 3.1, 3.2

**Technical Notes:**
- 結合 PostgreSQL 和 Redis
- 緩存 TTL 2 秒

---

### Story 3.6: 任務列表查詢 API

**As a** 前端開發者，
**I want** 查詢所有任務的列表，
**So that** 在 UI 上顯示任務歷史。

**Acceptance Criteria:**

**Given** 系統有多個任務
**When** 前端請求 `GET /api/v1/tasks`
**Then**
- 返回任務列表（tasks[], total, page, page_size）
- 支持查詢參數（status, page, page_size, sort_by, order）
- 分頁限制（最大 100 條/頁）

**Prerequisites:** Story 3.5

**Technical Notes:**
- SQLAlchemy 分頁和排序
- 緩存 TTL 10 秒

---

### Story 3.7: 任務取消功能實現

**As a** 用戶，
**I want** 能夠取消正在執行的任務，
**So that** 可以停止不需要的任務。

**Acceptance Criteria:**

**Given** 正在執行的任務
**When** 用戶請求 `POST /api/v1/tasks/{task_id}/cancel`
**Then**
- 更新任務狀態為 "cancelled"
- 通知所有執行該任務的 Worker 停止
- Worker 停止執行並釋放資源
- 處理不同狀態（queued 直接取消，in_progress 通知 Worker，completed/failed 返回 400）

**Prerequisites:** Story 3.5

**Technical Notes:**
- WebSocket 或 Redis Pub/Sub 通知 Worker

---

## Epic 4: Flutter 可視化儀表板

**Epic Goal:** 實現跨平台的可視化儀表板，讓用戶能夠查看系統狀態、提交任務、監控執行。

**Business Value:** 前端是用戶與系統交互的入口，直接影響用戶體驗和平台可用性。

**Estimated Duration:** 3 週

---

### Story 4.1: Flutter 項目初始化與路由配置

**As a** Flutter 開發者，
**I want** 建立 Flutter 項目結構和路由系統，
**So that** 能夠開始開發 UI 頁面。

**Acceptance Criteria:**

**Given** Flutter 3.x+ 已安裝
**When** 初始化 Flutter 項目
**Then**
- 項目結構清晰（lib/screens/, lib/widgets/, lib/services/, lib/models/）
- 配置路由（go_router 或 auto_route）
- 配置狀態管理（Riverpod 或 Bloc）
- 配置主題（Material Design 3）
- 配置環境變量（flutter_dotenv）
- 應用能在 Desktop 和 Web 上運行

**Prerequisites:** Story 1.1

**Technical Notes:**
- Flutter 3.x+, go_router, riverpod, material 3

---

### Story 4.2: HTTP 和 WebSocket 通信層實現

**As a** Flutter 開發者，
**I want** 實現與後端的 HTTP 和 WebSocket 通信，
**So that** 能夠獲取數據和接收實時更新。

**Acceptance Criteria:**

**Given** 後端 API 運行中
**When** Flutter 應用啟動
**Then**
- HTTP 客戶端配置（dio 或 http）
- WebSocket 客戶端配置（web_socket_channel）
- API Service 層封裝所有端點
- 錯誤處理和重試機制
- 自動重連邏輯
- 測試連接成功

**Prerequisites:** Story 4.1, Story 2.4, Story 3.5

**Technical Notes:**
- dio for HTTP, web_socket_channel for WebSocket
- Service: ApiService, WebSocketService

---

### Story 4.3: 儀表板主界面實現

**As a** 用戶，
**I want** 看到系統的總體狀況儀表板，
**So that** 能快速了解系統狀態。

**Acceptance Criteria:**

**Given** 用戶打開應用
**When** 進入儀表板頁面
**Then**
- 顯示頂部狀態欄（在線機器數、運行中任務數、系統狀態）
- 顯示機器列表（左側）
- 顯示任務列表（右側）
- 響應式布局（適配不同屏幕尺寸）
- 最小窗口：1024x768

**Prerequisites:** Story 4.1, 4.2

**Technical Notes:**
- Screen: lib/screens/dashboard_screen.dart
- Material 3 UI 組件

---

### Story 4.4: 機器列表視圖實現

**As a** 用戶，
**I want** 查看所有 Worker 機器的列表，
**So that** 了解哪些機器在線以及它們的狀態。

**Acceptance Criteria:**

**Given** 儀表板已加載
**When** 用戶查看機器列表
**Then**
- 顯示所有 Worker（machine_name, status, tools, resources）
- 狀態顏色編碼（綠色=在線，灰色=離線，黃色=繁忙）
- 實時更新（WebSocket）
- 資源使用進度條（CPU, Memory, Disk）
- 點擊機器進入詳情頁面
- 支持過濾（在線/離線）

**Prerequisites:** Story 4.3, Story 2.4

**Technical Notes:**
- Widget: MachineListWidget
- 使用 Riverpod/Bloc 管理狀態

---

### Story 4.5: 任務列表視圖實現

**As a** 用戶，
**I want** 查看所有任務的列表，
**So that** 了解任務的執行狀況和歷史。

**Acceptance Criteria:**

**Given** 儀表板已加載
**When** 用戶查看任務列表
**Then**
- 顯示所有任務（task_id, description, status, progress, created_at）
- 狀態顏色編碼（綠色=完成，黃色=進行中，灰色=排隊，紅色=失敗）
- 實時更新進度條
- 點擊任務進入詳情頁面
- 支持篩選（queued/in_progress/completed/failed）
- 支持搜索
- 分頁加載

**Prerequisites:** Story 4.3, Story 3.6

**Technical Notes:**
- Widget: TaskListWidget
- 分頁：InfiniteScrollView

---

### Story 4.6: 任務提交表單實現

**As a** 用戶，
**I want** 能夠提交新任務，
**So that** 系統開始執行我的任務。

**Acceptance Criteria:**

**Given** 用戶在儀表板
**When** 點擊"新建任務"按鈕
**Then**
- 彈出對話框
- 任務類型下拉選擇（develop_feature, bug_fix, refactor）
- 任務描述文本框（支持 Markdown 預覽）
- 檢查點頻率滑塊（少/中/多）
- 提交按鈕
- 提交後關閉對話框，任務出現在列表中

**Prerequisites:** Story 4.5, Story 3.1

**Technical Notes:**
- Dialog: TaskSubmitDialog
- Markdown 編輯器：flutter_markdown

---

### Story 4.7: 任務詳情頁面實現

**As a** 用戶，
**I want** 查看單個任務的詳細信息，
**So that** 了解任務的執行細節。

**Acceptance Criteria:**

**Given** 用戶點擊任務卡片
**When** 進入任務詳情頁面
**Then**
- 顯示任務基本信息（description, status, created_at）
- 顯示所有子任務列表（subtask_type, status, assigned_worker, evaluation_score）
- 顯示實時日誌流（底部窗口）
- 顯示進度條
- 提供取消按鈕
- 實時更新（WebSocket）

**Prerequisites:** Story 4.5, Story 3.5

**Technical Notes:**
- Screen: TaskDetailScreen
- LogStreamWidget 自動滾動

---

### Story 4.8: 機器詳情頁面實現

**As a** 用戶，
**I want** 查看單個 Worker 機器的詳細信息，
**So that** 了解機器的狀態和資源使用。

**Acceptance Criteria:**

**Given** 用戶點擊機器卡片
**When** 進入機器詳情頁面
**Then**
- 顯示機器信息（machine_name, system_info, tools）
- 顯示資源使用圖表（CPU, Memory, Disk）
- 顯示當前執行的任務（如果有）
- 顯示歷史任務列表
- 實時更新（WebSocket）

**Prerequisites:** Story 4.4, Story 2.5

**Technical Notes:**
- Screen: MachineDetailScreen
- fl_chart 繪製圖表

---

## Epic 5: AI 工具整合引擎

**Epic Goal:** 實現 Claude Code (MCP)、Gemini CLI 和 Ollama (Local LLM) 的整合，讓 Worker 能夠執行 AI 任務。

**Business Value:** AI 工具是平台的核心能力，沒有 AI 整合，平台無法提供實際價值。

**Estimated Duration:** 3-4 週

---

### Story 5.1: AI 工具基類設計

**As a** Worker Agent 開發者，
**I want** 設計統一的 AI 工具接口，
**So that** 能夠方便地整合不同的 AI 工具。

**Acceptance Criteria:**

**Given** Worker Agent 項目結構
**When** 設計 AI 工具基類
**Then**
- 創建 `BaseTool` 抽象類（agent/tools/base.py）
- 定義統一接口：execute(task_data) → result
- 定義通用方法：validate_config(), check_availability()
- 支持錯誤處理和重試
- 支持超時控制
- 支持日誌記錄

**Prerequisites:** Story 1.5

**Technical Notes:**
- 使用 Python ABC (Abstract Base Class)
- 所有具體工具繼承 BaseTool

---

### Story 5.2: Claude Code (MCP) 整合實現

**As a** Worker Agent，
**I want** 能夠調用 Claude Code 通過 MCP，
**So that** 可以使用 Claude 生成代碼。

**Acceptance Criteria:**

**Given** Claude Code 和 MCP 已安裝
**When** Worker 執行需要 claude_code 的任務
**Then**
- ClaudeCodeTool 類實現（agent/tools/claude_code.py）
- 通過 MCP 連接 Claude Code
- 發送 prompt 並接收響應
- 處理 Claude 的流式輸出
- 解析結果並返回
- 錯誤處理（連接失敗、超時）
- 配置管理（API key, model）

**Prerequisites:** Story 5.1

**Technical Notes:**
- 使用 MCP Python SDK
- 支持流式輸出（yield）
- 配置超時（默認 300 秒）

---

### Story 5.3: Gemini CLI 整合實現

**As a** Worker Agent，
**I want** 能夠調用 Gemini CLI，
**So that** 可以使用 Gemini 審查代碼。

**Acceptance Criteria:**

**Given** Gemini CLI 已安裝並配置
**When** Worker 執行需要 gemini_cli 的任務
**Then**
- GeminiCLITool 類實現（agent/tools/gemini_cli.py）
- 使用 Google AI SDK 調用 Gemini
- 支持不同模型（gemini-pro, gemini-flash）
- 發送 prompt 並接收響應
- 解析結果並返回
- 錯誤處理和重試
- 配置管理（API key, model）

**Prerequisites:** Story 5.1

**Technical Notes:**
- 使用 google-generativeai Python SDK
- 配置超時和重試策略

---

### Story 5.4: Ollama (Local LLM) 整合實現

**As a** Worker Agent，
**I want** 能夠調用本地 Ollama LLM，
**So that** 可以處理敏感任務而不發送到雲端。

**Acceptance Criteria:**

**Given** Ollama 已安裝並運行
**When** Worker 執行需要 local_llm 的任務
**Then**
- LocalLLMTool 類實現（agent/tools/local_llm.py）
- 通過 HTTP API 調用 Ollama
- 支持不同模型（llama2, codellama, mistral）
- 發送 prompt 並接收響應
- 支持流式輸出
- 解析結果並返回
- 錯誤處理
- 配置管理（ollama_url, model）

**Prerequisites:** Story 5.1

**Technical Notes:**
- 使用 httpx 調用 Ollama HTTP API
- 默認 URL: http://localhost:11434

---

### Story 5.5: 任務執行器實現

**As a** Worker Agent，
**I want** 能夠執行分配給我的任務，
**So that** 完成用戶提交的工作。

**Acceptance Criteria:**

**Given** Worker 收到任務分配
**When** TaskExecutor 執行任務
**Then**
- 從後端接收任務數據（subtask_id, subtask_type, subtask_data）
- 根據 subtask_type 選擇合適的 AI 工具
- 調用工具執行任務
- 捕獲工具輸出
- 上報執行狀態（開始、進行中、完成）
- 上報結果到後端
- 錯誤處理和重試（最多 3 次）

**Prerequisites:** Story 5.2, 5.3, 5.4

**Technical Notes:**
- TaskExecutor 類（agent/executor.py）
- 使用工廠模式選擇工具
- asyncio 異步執行

---

### Story 5.6: Worker 任務接收機制實現

**As a** Worker Agent，
**I want** 能夠接收後端分配的任務，
**So that** 知道要執行什麼。

**Acceptance Criteria:**

**Given** Worker 已註冊並在線
**When** 後端分配任務給 Worker
**Then**
- Worker 通過 WebSocket 接收任務通知
- 或通過輪詢 `GET /api/v1/workers/{worker_id}/tasks` 接收
- 解析任務數據
- 觸發 TaskExecutor 執行
- 更新 Worker 狀態為 "busy"

**Prerequisites:** Story 5.5, Story 3.4

**Technical Notes:**
- WebSocket 優先，輪詢作為備份
- 輪詢間隔：10 秒

---

### Story 5.7: 任務結果上報 API

**As a** Worker Agent，
**I want** 能夠上報任務執行結果，
**So that** 後端知道任務完成狀態。

**Acceptance Criteria:**

**Given** Worker 完成子任務執行
**When** Worker 發送 `POST /api/v1/subtasks/{subtask_id}/result`
**Then**
- 請求體包含（status, result, execution_time）
- 後端更新 `subtasks` 表
- 後端更新 Redis 狀態
- 後端觸發調度器檢查新的可執行子任務
- 返回 200

**Prerequisites:** Story 5.5, Story 3.2

**Technical Notes:**
- API: `backend/app/api/v1/subtasks.py`
- 觸發事件驅動的調度

---

### Story 5.8: 實時日誌流實現

**As a** 用戶，
**I want** 能夠實時查看 Agent 的輸出日誌，
**So that** 了解 Agent 正在做什麼。

**Acceptance Criteria:**

**Given** Worker 正在執行任務
**When** Worker 生成日誌輸出
**Then**
- Worker 通過 WebSocket 推送日誌到後端
- 後端通過 WebSocket 推送日誌到前端
- 前端實時顯示日誌（自動滾動）
- 支持語法高亮（代碼輸出）
- 支持搜索和過濾

**Prerequisites:** Story 5.5, Story 4.7

**Technical Notes:**
- WebSocket event: "agent_output"
- 前端：LogStreamWidget

---

## Epic 6: Agent 協作與審查機制

**Epic Goal:** 實現 Agent 之間的互相審查和並行執行協調，提升代碼質量。

**Business Value:** 多 Agent 協作是平台的核心差異化特性，能夠顯著提升輸出質量。

**Estimated Duration:** 2 週

---

### Story 6.1: Agent 審查工作流設計

**As a** 任務協調引擎，
**I want** 設計 Agent 互相審查的工作流，
**So that** 能夠自動觸發審查。

**Acceptance Criteria:**

**Given** Agent 1 完成代碼生成
**When** 系統檢測到子任務完成
**Then**
- 自動創建審查子任務（subtask_type="code_review"）
- 審查子任務依賴原子任務
- 分配給不同的 Agent（不能是同一個 Worker）
- 審查任務包含原子任務的輸出作為輸入

**Prerequisites:** Story 3.2, Story 5.5

**Technical Notes:**
- 在 task_decomposer 中實現審查邏輯
- 確保審查 Agent 與生成 Agent 不同

---

### Story 6.2: 代碼審查 Prompt 模板設計

**As a** Worker Agent，
**I want** 使用結構化的 prompt 審查代碼，
**So that** 審查結果質量高且一致。

**Acceptance Criteria:**

**Given** 需要審查的代碼
**When** 審查 Agent 執行任務
**Then**
- 使用預定義的審查 prompt 模板
- Prompt 包含：代碼內容、審查維度、輸出格式
- 審查維度：語法、風格、邏輯、安全性、可讀性
- 輸出格式：JSON（score, issues[], suggestions[]）
- 模板支持自定義

**Prerequisites:** Story 6.1

**Technical Notes:**
- 模板文件：agent/prompts/code_review.txt
- 使用 Jinja2 渲染模板

---

### Story 6.3: 審查結果解析和存儲

**As a** 後端服務，
**I want** 解析和存儲審查結果，
**So that** 能夠追蹤質量和觸發後續動作。

**Acceptance Criteria:**

**Given** Agent 完成審查任務
**When** Worker 上報審查結果
**Then**
- 解析 JSON 格式的審查報告
- 提取評分、問題列表、建議列表
- 存儲到 PostgreSQL `subtasks.result` (JSONB)
- 如果評分 < 6，觸發自動修復流程
- 如果評分 >= 6，標記為通過

**Prerequisites:** Story 6.2, Story 5.7

**Technical Notes:**
- Service: `backend/app/services/review_service.py`
- 閾值可配置

---

### Story 6.4: 自動修復流程實現

**As a** 任務協調引擎，
**I want** 在審查發現問題時自動觸發修復，
**So that** 減少人工干預。

**Acceptance Criteria:**

**Given** 審查結果評分 < 6
**When** 審查結果存儲完成
**Then**
- 自動創建修復子任務（subtask_type="code_fix"）
- 修復任務包含原代碼 + 審查報告
- 分配給原始生成 Agent
- 修復完成後重新審查
- 最多循環 2 次，否則標記為需要人工干預

**Prerequisites:** Story 6.3

**Technical Notes:**
- 避免無限循環
- 循環次數可配置

---

### Story 6.5: 並行執行協調器實現

**As a** 任務協調引擎，
**I want** 協調多個 Agent 並行工作，
**So that** 充分利用資源加速執行。

**Acceptance Criteria:**

**Given** 一個任務有多個無依賴的子任務
**When** 調度器運行
**Then**
- 識別所有可並行執行的子任務
- 同時分配給不同 Worker
- 追蹤所有並行任務的狀態
- 所有並行任務完成後，聚合結果
- 更新父任務狀態

**Prerequisites:** Story 3.4, Story 5.5

**Technical Notes:**
- 使用 asyncio.gather 或 celery group
- 支持部分失敗處理

---

## Epic 7: 量化評估框架

**Epic Goal:** 實現自動化的質量評估框架，包括 Code Quality、Completeness、Security 三個維度的評估器。

**Business Value:** 評估框架是平台的創新核心，能夠自動量化 Agent 輸出質量，減少人工審查負擔。

**Estimated Duration:** 2-3 週

---

### Story 7.1: 評估框架基礎架構設計

**As a** 後端開發者，
**I want** 設計評估框架的基礎架構，
**So that** 能夠方便地添加新的評估器。

**Acceptance Criteria:**

**Given** 評估框架需求
**When** 設計架構
**Then**
- 創建 `BaseEvaluator` 抽象類
- 定義統一接口：evaluate(code, context) → EvaluationResult
- EvaluationResult 包含：score (0-10), details, suggestions
- 支持可插拔評估器
- 支持自定義權重配置
- 項目結構清晰（backend/app/evaluation/）

**Prerequisites:** Story 1.4

**Technical Notes:**
- 使用 ABC (Abstract Base Class)
- 配置文件：evaluation_config.yaml

---

### Story 7.2: Code Quality 評估器實現

**As a** 評估框架，
**I want** 評估代碼質量，
**So that** 能夠量化代碼的語法正確性和風格。

**Acceptance Criteria:**

**Given** Agent 生成的代碼
**When** Code Quality 評估器運行
**Then**
- 檢查語法錯誤（Python: ast.parse, JS: esprima）
- 運行 Linting 工具（pylint, ESLint）
- 計算圈複雜度（radon, eslint-plugin-complexity）
- 檢查註釋覆蓋率
- 計算評分（0-10）：基礎分 10 - 語法錯誤（-5） - Linting 警告（-0.5 each） - 高複雜度（-1 each）
- 返回詳細報告（issues[], suggestions[]）

**Prerequisites:** Story 7.1

**Technical Notes:**
- Evaluator: `backend/app/evaluation/code_quality.py`
- 整合：pylint, ESLint, radon
- 使用 subprocess 運行工具

---

### Story 7.3: Completeness 評估器實現

**As a** 評估框架，
**I want** 評估代碼完整性，
**So that** 確保所有需求都被實現。

**Acceptance Criteria:**

**Given** Agent 生成的代碼和原始需求
**When** Completeness 評估器運行
**Then**
- 從需求描述提取關鍵功能點
- 檢查每個功能點是否在代碼中實現
- 檢查錯誤處理是否完整
- 檢查是否有測試代碼
- 檢查是否有文檔/註釋
- 計算評分：功能覆蓋率 × 8 + 錯誤處理（+1） + 測試（+1）
- 返回詳細報告

**Prerequisites:** Story 7.1

**Technical Notes:**
- Evaluator: `backend/app/evaluation/completeness.py`
- 使用簡單的關鍵詞匹配（MVP）
- 未來可用 LLM 輔助分析

---

### Story 7.4: Security 評估器實現

**As a** 評估框架，
**I want** 評估代碼安全性，
**So that** 識別常見的安全漏洞。

**Acceptance Criteria:**

**Given** Agent 生成的代碼
**When** Security 評估器運行
**Then**
- 運行安全掃描工具（Bandit for Python, npm audit for JS）
- 檢測注入攻擊風險（SQL injection, XSS, Command injection）
- 檢測硬編碼敏感信息（密碼、API key）
- 掃描依賴項漏洞
- 計算評分：基礎分 10 - 高危（-3 each） - 中危（-1 each） - 低危（-0.5 each）
- 分數 < 4 自動標記"需要人工審查"
- 返回詳細報告

**Prerequisites:** Story 7.1

**Technical Notes:**
- Evaluator: `backend/app/evaluation/security.py`
- 整合：Bandit, npm audit
- 使用正則表達式檢測硬編碼敏感信息

---

### Story 7.5: 聚合評分引擎實現

**As a** 評估框架，
**I want** 聚合所有維度的評分，
**So that** 得出總體質量評分。

**Acceptance Criteria:**

**Given** 所有評估器的結果
**When** 聚合評分引擎運行
**Then**
- 根據配置的權重計算加權平均：
  - Code Quality: 25%
  - Completeness: 30%
  - Security: 25%
  - (剩餘 20% 為 Post-MVP 評估器預留)
- 計算總分（0-10）
- 生成質量等級：Excellent (9-10), Good (7-8.9), Acceptable (5-6.9), Poor (3-4.9), Fail (0-2.9)
- 聚合所有問題和建議
- 返回完整評估報告

**Prerequisites:** Story 7.2, 7.3, 7.4

**Technical Notes:**
- Service: `backend/app/evaluation/aggregator.py`
- 權重可配置（evaluation_config.yaml）

---

### Story 7.6: 評估結果存儲和查詢 API

**As a** 後端服務，
**I want** 存儲評估結果並提供查詢 API，
**So that** 前端能夠顯示評估報告。

**Acceptance Criteria:**

**Given** 評估框架完成評估
**When** 評估結果生成
**Then**
- 存儲到 `subtasks.evaluation_score` (FLOAT)
- 存儲詳細報告到 `subtasks.result` (JSONB)
- 提供查詢 API：`GET /api/v1/subtasks/{subtask_id}/evaluation`
- 返回完整評估報告（overall_score, dimensions, details）
- 前端能夠解析和顯示報告

**Prerequisites:** Story 7.5, Story 3.2

**Technical Notes:**
- API: `backend/app/api/v1/subtasks.py`
- Schema: EvaluationReport

---

## Epic 8: 人類檢查點與糾偏系統

**Epic Goal:** 實現"半自動"的人機協作模式，讓用戶能夠在關鍵時刻介入、審查和糾偏。

**Business Value:** 這是平台的核心創新之一，實現 AI 執行 + 人類把關的完美平衡。

**Estimated Duration:** 2 週

---

### Story 8.1: 檢查點觸發邏輯實現

**As a** 任務協調引擎，
**I want** 在關鍵時刻自動觸發檢查點，
**So that** 用戶能夠審查並決策。

**Acceptance Criteria:**

**Given** 子任務執行完成
**When** 檢查檢查點觸發條件
**Then**
- 觸發條件：
  - 代碼生成完成後
  - 審查發現問題時
  - 評估評分 < 7
  - 用戶配置的 checkpoint_frequency
- 創建 checkpoint 記錄（PostgreSQL `checkpoints` 表）
- 更新任務狀態為 "waiting_checkpoint"
- 通知前端（WebSocket event: "checkpoint_reached"）

**Prerequisites:** Story 3.2, Story 7.5

**Technical Notes:**
- Service: `backend/app/services/checkpoint_service.py`
- 配置不同 checkpoint_frequency 的觸發策略

---

### Story 8.2: 檢查點 UI 實現

**As a** 用戶，
**I want** 清晰的檢查點界面，
**So that** 能夠快速審查並決策。

**Acceptance Criteria:**

**Given** 任務到達檢查點
**When** 用戶收到通知
**Then**
- 前端顯示通知橫幅："任務 [名稱] 需要你的審查"
- 任務卡片顏色變為黃色
- 點擊進入檢查點視圖：
  - 上下文信息（為什麼暫停）
  - Agent 輸出（代碼/文檔，支持語法高亮）
  - 審查報告（如果有）
  - 評估評分（如果有）
  - 決策按鈕：[✓ 接受並繼續] [✏️ 提供糾偏建議] [✗ 拒絕]

**Prerequisites:** Story 8.1, Story 4.7

**Technical Notes:**
- Widget: CheckpointReviewDialog
- 語法高亮：flutter_syntax_view

---

### Story 8.3: 糾偏介面實現

**As a** 用戶，
**I want** 能夠提供糾偏建議，
**So that** Agent 能夠根據我的建議修復問題。

**Acceptance Criteria:**

**Given** 用戶在檢查點視圖
**When** 點擊"提供糾偏建議"
**Then**
- 彈出側邊欄或對話框
- 顯示 Agent 輸出（只讀）
- 問題描述輸入框（多行文本）
- 建議修改輸入框（多行文本）
- [提交建議] 按鈕
- 提交後，建議發送到後端
- 後端創建修復子任務，包含用戶反饋

**Prerequisites:** Story 8.2

**Technical Notes:**
- Widget: CorrectionDialog
- 支持 Markdown 格式

---

### Story 8.4: 用戶決策處理邏輯

**As a** 後端服務，
**I want** 處理用戶的檢查點決策，
**So that** 能夠繼續或調整執行流程。

**Acceptance Criteria:**

**Given** 用戶在檢查點做出決策
**When** 前端發送 `POST /api/v1/tasks/{task_id}/checkpoint/{checkpoint_id}/decision`
**Then**
- 請求體包含（decision, feedback）
- decision = "accept" | "correct" | "reject"
- 處理邏輯：
  - accept: 繼續執行下一個子任務
  - correct: 創建修復子任務，包含 feedback
  - reject: 標記任務為 "cancelled"
- 更新 checkpoint 記錄（user_decision, user_feedback）
- 更新任務狀態
- 返回 200

**Prerequisites:** Story 8.3, Story 3.7

**Technical Notes:**
- API: `backend/app/api/v1/checkpoints.py`
- Service: CheckpointService

---

### Story 8.5: 檢查點歷史追蹤

**As a** 用戶，
**I want** 查看任務的所有檢查點歷史，
**So that** 了解我做過哪些決策。

**Acceptance Criteria:**

**Given** 任務有多個檢查點
**When** 用戶查看任務詳情
**Then**
- 顯示所有檢查點的時間線
- 每個檢查點顯示：時間、類型、用戶決策、反饋
- 支持展開查看詳細的 Agent 輸出和審查報告
- 支持搜索和過濾

**Prerequisites:** Story 8.4, Story 4.7

**Technical Notes:**
- Widget: CheckpointTimelineWidget
- 使用 timeline_tile 包

---

## Epic 9: 測試、優化與文檔

**Epic Goal:** 確保平台質量、性能和可用性達到發布標準，提供完整的用戶文檔。

**Business Value:** 發布前的質量保證，確保用戶有良好的體驗和能夠順利使用平台。

**Estimated Duration:** 2-3 週

---

### Story 9.1: 端到端測試套件實現

**As a** QA 工程師，
**I want** 實現端到端測試，
**So that** 驗證整個系統的功能正確性。

**Acceptance Criteria:**

**Given** 完整的系統部署
**When** 運行端到端測試
**Then**
- 測試場景 1：Worker 註冊和心跳
- 測試場景 2：任務提交和執行
- 測試場景 3：多 Agent 並行執行
- 測試場景 4：Agent 審查工作流
- 測試場景 5：評估框架
- 測試場景 6：檢查點和糾偏
- 所有測試通過
- 測試覆蓋率 > 70%

**Prerequisites:** All previous stories

**Technical Notes:**
- 使用 pytest 和 pytest-asyncio
- 使用 Docker Compose 搭建測試環境
- 測試文件：tests/e2e/

---

### Story 9.2: 性能測試和優化

**As a** 性能工程師，
**I want** 測試系統性能並優化瓶頸，
**So that** 確保系統滿足 NFR 要求。

**Acceptance Criteria:**

**Given** 系統部署完成
**When** 運行性能測試
**Then**
- 測試場景 1：10 個 Worker 同時在線
- 測試場景 2：20 個任務並行執行
- 測試場景 3：50 個 WebSocket 連接
- 測試響應時間：
  - 任務提交 < 2 秒
  - WebSocket 延遲 < 500ms
  - Worker 註冊 < 5 秒
- 識別並優化瓶頸
- 所有 NFR 指標達標

**Prerequisites:** Story 9.1

**Technical Notes:**
- 使用 locust 或 k6 進行負載測試
- 使用 cProfile 分析 Python 性能
- 優化數據庫查詢和索引

---

### Story 9.3: 錯誤處理完善

**As a** 開發者，
**I want** 完善所有錯誤處理，
**So that** 用戶遇到問題時有清晰的錯誤提示。

**Acceptance Criteria:**

**Given** 系統運行中
**When** 發生各種錯誤情況
**Then**
- 所有 API 錯誤返回標準格式（status, message, details）
- 前端顯示用戶友好的錯誤消息
- 關鍵錯誤記錄到日誌文件
- Worker 斷線後自動重連
- 任務失敗後自動重試（最多 3 次）
- 提供錯誤恢復機制

**Prerequisites:** Story 9.1

**Technical Notes:**
- 統一錯誤處理中間件
- 前端：全局錯誤處理器
- 後端：自定義異常類

---

### Story 9.4: 用戶文檔撰寫

**As a** 技術作家，
**I want** 撰寫完整的用戶文檔，
**So that** 用戶能夠順利使用平台。

**Acceptance Criteria:**

**Given** 平台功能完整
**When** 撰寫用戶文檔
**Then**
- README.md：項目介紹、快速開始、貢獻指南
- docs/installation.md：詳細安裝步驟
- docs/user-guide.md：使用教程（配置、提交任務、監控、糾偏）
- docs/architecture.md：系統架構說明
- docs/api-reference.md：API 文檔
- docs/troubleshooting.md：常見問題和解決方案
- 提供截圖和示例

**Prerequisites:** All previous stories

**Technical Notes:**
- 使用 Markdown 格式
- 考慮使用 MkDocs 或 Docusaurus 生成網站

---

### Story 9.5: 開發者文檔撰寫

**As a** 開源貢獻者，
**I want** 詳細的開發者文檔，
**So that** 能夠理解代碼並貢獻。

**Acceptance Criteria:**

**Given** 完整的代碼庫
**When** 撰寫開發者文檔
**Then**
- docs/development.md：開發環境設置
- docs/architecture-deep-dive.md：詳細架構說明
- docs/contributing.md：貢獻指南（代碼規範、PR 流程）
- docs/adding-ai-tools.md：如何添加新的 AI 工具
- docs/extending-evaluation.md：如何添加新的評估器
- 代碼註釋完整

**Prerequisites:** Story 9.4

**Technical Notes:**
- 遵循 Markdown 最佳實踐
- 提供代碼示例

---

### Story 9.6: 發布準備和 GitHub 配置

**As a** 項目維護者，
**I want** 準備開源發布，
**So that** 能夠順利發布到 GitHub。

**Acceptance Criteria:**

**Given** 所有開發和測試完成
**When** 準備發布
**Then**
- 創建 LICENSE 文件（MIT 或 Apache 2.0）
- 配置 .github/ISSUE_TEMPLATE（bug, feature request）
- 配置 .github/PULL_REQUEST_TEMPLATE
- 配置 CODE_OF_CONDUCT.md
- 配置 CHANGELOG.md
- 打 v1.0.0 tag
- 創建 GitHub Release
- 撰寫發布公告
- 提交到 Hacker News / Reddit

**Prerequisites:** Story 9.4, 9.5

**Technical Notes:**
- 遵循 Semantic Versioning
- 使用 GitHub Actions 自動化發布流程

---

## Epic Breakdown Summary

**總結：**

✅ **Epic 1: 基礎設施** - 7 個 Stories
✅ **Epic 2: Worker 管理** - 6 個 Stories
✅ **Epic 3: 任務協調** - 7 個 Stories
✅ **Epic 4: Flutter UI** - 8 個 Stories
✅ **Epic 5: AI 整合** - 8 個 Stories
✅ **Epic 6: Agent 協作** - 5 個 Stories
✅ **Epic 7: 評估框架** - 6 個 Stories
✅ **Epic 8: 檢查點系統** - 5 個 Stories
✅ **Epic 9: 測試與發布** - 6 個 Stories

**總計：58 個詳細的 User Stories**

每個 Story 都包含：
- User Story 格式（As a / I want / So that）
- BDD 格式的接受標準（Given / When / Then）
- Prerequisites（依賴關係）
- Technical Notes（實現指導）

所有 Stories 都是**垂直切片**，可以由單個 dev agent 在一個 session 中完成。

---

_For implementation: Use the `create-story` workflow to generate individual story implementation plans from this epic breakdown._

