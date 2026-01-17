# Multi-Agent on the Web - Product Requirements Document

**Author:** sir
**Date:** 2025-11-11
**Version:** 1.0

---

## Executive Summary

**Multi-Agent on the Web** 是一個革命性的多代理協作平台，旨在解決當前 AI 輔助開發工具的核心痛點：**效率低下、質量不穩定、缺乏協作**。通過分布式 Worker 架構和智能的多 Agent 協調機制，該平台將單一 AI 工具的線性工作流程轉變為並行、互相審查、人類監督的高效協作模式，實現 **2-3 倍速度提升**和**多層次質量保證**。

**核心價值主張：**
- ⚡ **速度提升 2-3 倍**：多 Agent 並行執行取代順序執行
- 🎯 **4 層質量保證**：Agent 互審 + 人類把關 + 投票 + 評估框架
- 👁️ **實時可視化監控**：Flutter 跨平台 UI，一目了然
- 🔧 **靈活糾偏能力**：隨時介入任何 Agent，防止跑偏
- 🌍 **分布式協作**：利用多台機器資源 + 本地 LLM 保護隱私
- 🔌 **開箱即用**：可視化產品，無需編程配置

### What Makes This Special

**產品的魔法時刻：**

當開發者提交一個複雜任務（例如："開發用戶認證系統"），系統會：

1. **自動分解任務**：智能拆分為多個子任務
2. **並行編排**：在可視化儀表板上，開發者看到 3-4 個 Agent 同時工作
3. **自動質量把關**：Agent 互相審查，評估框架自動評分
4. **關鍵時刻暫停**：在重要決策點，系統暫停並等待開發者確認
5. **即時糾偏**：開發者點擊進入任何 Agent，查看詳情，提供糾正建議
6. **12 分鐘完成**：原本需要 28 分鐘的工作，現在 12 分鐘搞定

**這不是完全自動化**（容易失控），也不是簡單工具（效率低），而是 **AI 執行 + 人類把關的理想結合**。

---

## Project Classification

**Technical Type:** Distributed System Platform
- **Frontend:** Flutter (Desktop + Web + Mobile)
- **Backend:** Python FastAPI
- **Worker Agent:** Python SDK
- **Integration:** Claude Code (MCP) + Gemini CLI + Local LLM (Ollama)

**Domain:** Developer Tools / AI Infrastructure
**Complexity:** Medium-High

**項目特點：**
- **分布式架構**：多機器協同工作
- **跨平台 UI**：Flutter 支持所有主流平台
- **多 AI 工具整合**：統一協調層
- **實時通信**：WebSocket + Redis Pub/Sub
- **創新質量框架**：量化、可擴展、自動化

---

## Success Criteria

### MVP 階段成功指標（6 個月內）

**用戶採用：**
- 🎯 100 個活躍的專業開發者用戶
- 🎯 平均每個用戶每週使用 5 次以上
- 🎯 用戶留存率 > 60%（30 天）

**效率提升：**
- 🎯 任務完成時間平均減少 40-50%（實測數據）
- 🎯 用戶報告的"時間節省"滿意度 > 8/10
- 🎯 Agent 並行執行率 > 70%

**質量指標：**
- 🎯 評估框架平均評分 > 7.5/10
- 🎯 需要糾偏的任務比例 < 30%
- 🎯 用戶對質量滿意度 > 7.5/10

**技術穩定性：**
- 🎯 Worker 在線率 > 99%
- 🎯 平均任務響應時間 < 2 秒
- 🎯 支持至少 3 種主流 AI 工具

### 開源社區成長（12 個月）

**社區指標：**
- 🎯 GitHub Stars > 1000
- 🎯 活躍貢獻者 > 20 人
- 🎯 社區提交的 PR > 50

**平台擴展：**
- 🎯 支持 5+ 種 AI 工具
- 🎯 用戶自定義工作流模板 > 50 個

**成功的真正意義：**

不僅僅是數字，而是：
- 專業開發者真正信任 AI 半自動工作
- 社區持續貢獻新的 AI 工具整合
- 成為 AI 輔助開發的新標準

---

## Product Scope

### MVP - Minimum Viable Product

**核心功能（MVP 必須有）：**

#### 1. 可視化儀表板 (Flutter 跨平台)
- **總體狀況顯示**
  - 多少機器在線
  - 多少任務運行中 / 已完成 / 失敗
  - 系統整體健康狀態
- **機器列表視圖**
  - 每台機器的狀態（在線/離線/繁忙）
  - 機器上安裝的 AI 工具
  - 資源使用（CPU、內存、磁盤）
- **任務列表視圖**
  - 當前運行任務（實時進度）
  - 歷史任務（可搜索、篩選）
- **實時日誌流**
  - Agent 輸出的實時顯示
  - 可過濾、可搜索

**技術要求：**
- Flutter 3.x+
- Material Design 3 UI
- 響應式設計（Desktop 優先，Web 同步支持）
- WebSocket 實時連接

#### 2. 分布式 Worker Agent 系統

**Worker Agent 核心功能：**
- **自動註冊和心跳**
  - Worker 啟動時自動向後端註冊
  - 每 30 秒發送心跳，報告狀態
- **AI 工具整合（MVP 支持 3 種）**
  - Claude Code (通過 MCP)
  - Gemini CLI (通過 Google AI SDK)
  - Local LLM (通過 Ollama API)
- **資源監控**
  - 實時監控 CPU、內存、磁盤使用
  - 上報給後端用於智能調度
- **任務執行**
  - 接收任務
  - 執行 AI 工具
  - 上報結果

**技術要求：**
- Python 3.11+
- asyncio 異步編程
- YAML 配置文件
- 錯誤重試機制

#### 3. 智能任務協調（後端）

**後端核心功能：**
- **任務分解**
  - 接收用戶提交的大任務
  - 智能拆分為子任務
  - 識別依賴關係
- **智能分配**
  - 根據 Worker 上的工具選擇合適的 Worker
  - 考慮資源使用情況
  - 考慮隱私需求（敏感任務用本地 LLM）
- **並行調度**
  - 支持多個 Agent 並行執行
  - 管理任務依賴（某些任務必須等待前置任務）
- **狀態管理**
  - Redis 實時狀態
  - PostgreSQL 持久化存儲

**技術要求：**
- FastAPI 0.100+
- PostgreSQL 15+
- Redis 7+
- SQLAlchemy 2.x ORM

#### 4. 人類確認檢查點

**檢查點機制：**
- **關鍵點自動暫停**
  - 在重要決策點自動暫停
  - 例如：代碼審查發現問題時
- **展示 Agent 輸出**
  - 清晰展示 Agent 生成的內容
  - 展示審查報告（如果有）
- **用戶決策介面**
  - 確認：接受並繼續
  - 糾偏：提供修改建議，Agent 修復後繼續
  - 拒絕：終止任務或重新生成

**技術要求：**
- WebSocket 實時通信
- 清晰的 UI 提示
- 支持多種用戶決策選項

#### 5. Agent 互相審查機制

**審查流程：**
- **自動觸發**
  - 代碼生成完成後，自動觸發另一個 Agent 審查
  - 例如：Claude 生成代碼 → Gemini 審查
- **審查報告**
  - 展示審查發現的問題
  - 提供改進建議
- **自動修復循環**
  - 如果問題明顯，Agent 1 根據建議自動修復
  - 如果問題複雜，暫停等待人類決策

#### 6. 基礎評估框架

**評估維度（MVP 包含 3 個）：**
1. **Code Quality（代碼質量）** - 優先級最高
   - 語法正確性
   - 代碼風格（Linting）
   - 圈複雜度
   - 整合工具：pylint, ESLint, black
2. **Completeness（完整性）** - 優先級高
   - 需求覆蓋率
   - 錯誤處理
   - 基本檢查清單
3. **Security（安全性）** - 優先級高
   - 基礎安全掃描
   - 注入攻擊檢測
   - 敏感數據洩露檢測
   - 整合工具：Bandit, npm audit

**評分機制：**
- 每個維度 0-10 分
- 加權平均：Code Quality 25%, Completeness 30%, Security 25%（剩餘 20% 留給 Post-MVP）
- 總分 < 5：自動標記"需要重做"
- 總分 5-7：標記"需要人工審查"
- 總分 > 7：可以繼續

**評分結果展示：**
- 清晰的評分卡片
- 詳細的問題列表
- 改進建議

### Growth Features (Post-MVP)

**第二階段功能（v1.1 - v1.2）：**

#### 1. 多方案投票機制
- 對於關鍵任務，3 個 Agent 並行生成方案
- 用戶可以對比選擇
- 評估框架自動選擇最佳方案

#### 2. 預設工作流模板
- "開發 REST API"
- "添加用戶認證"
- "實現支付集成"
- "代碼重構"
- 用戶可以自定義和分享模板

#### 3. 高級評估框架
- **Architecture Alignment（架構一致性）**
  - 使用 LLM 進行語義分析
  - 檢查是否符合項目架構
- **Testability（可測試性）**
  - 測試覆蓋率分析
  - 測試質量評估
- 基於機器學習的質量預測
- 代碼安全性深度掃描
- 性能評估

#### 4. 移動端完整體驗
- 移動端也能提交任務
- 移動端實時監控
- 移動端糾偏

#### 5. 更多 AI 工具整合
- Codex (OpenAI)
- GitHub Copilot API
- Anthropic Claude API（直接整合）
- Google Gemini Pro
- 開放插件系統

### Vision (Future)

**長期願景（v2.0+）：**

#### 1. 雲端部署選項
- 除了本地運行，提供雲端 SaaS 版本
- 多用戶支持
- 團隊協作功能

#### 2. 智能學習和優化
- 學習用戶的糾偏習慣
- 自動調整檢查點頻率
- 智能推薦最佳 Agent 組合

#### 3. 企業級功能
- SSO 整合
- 審計日誌
- 合規報告
- 團隊權限管理

#### 4. 社區生態
- 插件市場
- 工作流模板市場
- 自定義評估器分享

---

## Innovation & Novel Patterns

### 核心創新點

#### 1. 半自動的人機協作模式

**創新之處：**

現有的 AI 工具要麼是：
- **完全手動**：開發者必須逐步操作（Claude Code、Copilot）
- **完全自動**：AI 自己跑，容易失控（AutoGPT、AgentGPT）

**我們的創新：**

**"半自動"** = AI 執行 + 人類在關鍵點把關

- 大部分時間 AI 並行工作
- 在重要決策點自動暫停
- 用戶快速審查並決策
- 用戶可以隨時介入任何 Agent

**為什麼這是創新：**
- 保持了自動化的速度優勢
- 避免了完全自動化的失控風險
- 人類專注於高價值決策，而非瑣碎操作

#### 2. 量化評估框架

**創新之處：**

現有工具依賴：
- 人工審查（耗時）
- 簡單的靜態分析（不全面）

**我們的創新：**

**5 維度量化評估框架**：
1. Code Quality（代碼質量）
2. Completeness（完整性）
3. Security（安全性）
4. Architecture Alignment（架構一致性）
5. Testability（可測試性）

**關鍵特性：**
- **可擴展**：用戶可以自定義評估器
- **可配置**：調整權重和閾值
- **自動化**：無需人工干預
- **量化**：0-10 分，可追蹤趨勢

**為什麼這是創新：**
- 首個內建可擴展評估框架的多 Agent 平台
- 將主觀的"質量"轉化為客觀的評分
- 支持持續改進和學習

#### 3. 可視化多 Agent 監控

**創新之處：**

現有工具：
- 命令行輸出（難以追蹤）
- 日誌文件（事後查看）

**我們的創新：**

**類似任務管理器的實時監控**：
- 實時顯示所有 Agent 狀態
- 點擊進入任意 Agent 查看詳情
- 實時日誌流
- 資源使用可視化

**為什麼這是創新：**
- 首個提供可視化多 Agent 監控的產品
- 讓複雜的分布式系統一目了然
- 支持即時糾偏

### Validation Approach

**如何驗證創新的有效性：**

#### Phase 1: Alpha 測試（內部）
- 自己使用平台開發功能
- 記錄時間節省數據
- 收集質量評分數據

#### Phase 2: Beta 測試（小範圍）
- 邀請 10-20 個專業開發者
- A/B 測試：傳統方式 vs 平台
- 收集定量和定性反饋

#### Phase 3: 公開發布
- 開源發布
- 收集社區反饋
- 持續迭代改進

**成功指標：**
- 速度提升 > 40%（實測）
- 質量滿意度 > 7.5/10
- 用戶願意推薦給同事（NPS > 50）

---

## Multi-Platform Specific Requirements

### Flutter Frontend (Desktop + Web + Mobile)

#### Desktop Requirements (MVP 優先)

**平台支持：**
- Windows 10/11
- macOS 11+
- Linux (Ubuntu 20.04+)

**核心 UI 組件：**
1. **儀表板主界面**
   - 網格布局：左側機器列表，右側任務列表
   - 頂部狀態欄：總體統計
   - 底部日誌窗口（可折疊）
2. **機器詳情視圖**
   - 機器信息卡片
   - 資源使用圖表（實時更新）
   - 安裝的 AI 工具列表
3. **任務詳情視圖**
   - 任務進度條
   - Agent 輸出顯示（支持語法高亮）
   - 糾偏輸入框
4. **設置界面**
   - Worker 配置
   - 評估框架權重調整
   - 檢查點頻率設置

**技術要求：**
- Flutter 3.x+
- Riverpod 或 Bloc 狀態管理
- web_socket_channel 包
- Material Design 3 UI 組件
- 響應式設計（最小窗口：1024x768）

#### Web Requirements (MVP 同步支持)

**與 Desktop 的區別：**
- 無需安裝，瀏覽器直接訪問
- 部分快捷鍵不可用
- 文件上傳/下載需要特殊處理

**瀏覽器支持：**
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

#### Mobile Requirements (Post-MVP)

**階段 1（只讀）：**
- 查看機器狀態
- 查看任務進度
- 查看日誌

**階段 2（完整功能）：**
- 提交任務
- 糾偏操作
- 接收通知

### Backend API Specification

#### Core Endpoints

**1. Worker Management**

```
POST /api/v1/workers/register
Body: {
  "machine_id": "uuid",
  "machine_name": "string",
  "system_info": {...},
  "tools": ["claude_code", "gemini_cli", "ollama"]
}
Response: {
  "status": "registered",
  "worker_id": "uuid"
}

POST /api/v1/workers/{worker_id}/heartbeat
Body: {
  "status": "online",
  "resources": {
    "cpu_percent": 45.2,
    "memory_percent": 60.5,
    "disk_percent": 30.0
  }
}
Response: {"acknowledged": true}

GET /api/v1/workers
Response: {
  "workers": [
    {
      "worker_id": "uuid",
      "machine_name": "string",
      "status": "online",
      "tools": ["..."],
      "resources": {...}
    }
  ]
}
```

**2. Task Management**

```
POST /api/v1/tasks
Body: {
  "task_type": "develop_feature",
  "description": "開發用戶認證系統",
  "requirements": {...},
  "checkpoint_frequency": "medium"
}
Response: {
  "task_id": "uuid",
  "status": "queued",
  "estimated_subtasks": 4
}

GET /api/v1/tasks/{task_id}
Response: {
  "task_id": "uuid",
  "status": "in_progress",
  "subtasks": [...],
  "checkpoints": [...]
}

POST /api/v1/tasks/{task_id}/checkpoint/{checkpoint_id}/decision
Body: {
  "decision": "accept" | "correct" | "reject",
  "feedback": "string (if correct)"
}
Response: {"status": "resumed"}
```

**3. Evaluation Results**

```
GET /api/v1/tasks/{task_id}/evaluation
Response: {
  "overall_score": 8.2,
  "dimensions": {
    "code_quality": 8.5,
    "completeness": 9.0,
    "security": 7.0
  },
  "details": [...]
}
```

#### WebSocket Events

**Client → Server:**
- `subscribe_worker:{worker_id}` - 訂閱 Worker 更新
- `subscribe_task:{task_id}` - 訂閱任務更新

**Server → Client:**
- `worker_status_update` - Worker 狀態變化
- `task_status_update` - 任務狀態變化
- `agent_output` - Agent 實時輸出
- `checkpoint_reached` - 到達檢查點

### Authentication & Authorization

**MVP 階段：**
- **單用戶本地運行** - 無需認證
- 後端只綁定 localhost
- 敏感數據本地存儲

**Post-MVP 階段：**
- JWT Token 認證
- API Key 管理
- 多用戶支持

### Data Schemas

#### PostgreSQL Schema

```sql
-- Workers table
CREATE TABLE workers (
    worker_id UUID PRIMARY KEY,
    machine_name VARCHAR(100),
    status VARCHAR(20),
    system_info JSONB,
    tools JSONB,
    resources JSONB,
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tasks table
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY,
    task_type VARCHAR(50),
    description TEXT,
    requirements JSONB,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Subtasks table
CREATE TABLE subtasks (
    subtask_id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(task_id),
    assigned_worker UUID REFERENCES workers(worker_id),
    subtask_data JSONB,
    status VARCHAR(20),
    result JSONB,
    evaluation_score FLOAT
);

-- Checkpoints table
CREATE TABLE checkpoints (
    checkpoint_id UUID PRIMARY KEY,
    subtask_id UUID REFERENCES subtasks(subtask_id),
    checkpoint_type VARCHAR(50),
    agent_output JSONB,
    review_notes JSONB,
    user_decision VARCHAR(20),
    user_feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Redis Data Structures

```
# Worker 實時狀態
workers:{worker_id}:status = "online" | "offline" | "busy"
workers:{worker_id}:current_task = task_id

# Task 實時狀態
tasks:{task_id}:status = "queued" | "in_progress" | "waiting_checkpoint" | "completed" | "failed"
tasks:{task_id}:progress = {current_step, total_steps, percentage}

# Task Queue
task_queue = [task_id_1, task_id_2, ...]
```

---

## User Experience Principles

### UX 設計理念

**核心原則：**

1. **Clarity Over Complexity（清晰勝於複雜）**
   - 系統複雜，但 UI 必須簡單直觀
   - 一目了然當前狀態
   - 隱藏不常用的高級選項

2. **Trust Through Transparency（透明建立信任）**
   - 讓用戶看到所有 Agent 在做什麼
   - 實時日誌流
   - 清晰的評分和問題報告

3. **Control When Needed（需要時給予控制）**
   - 大部分時間自動運行
   - 關鍵時刻暫停
   - 支持隨時介入

4. **Minimize Cognitive Load（減少認知負擔）**
   - 使用顏色編碼（綠色=好，黃色=警告，紅色=問題）
   - 使用圖標和可視化
   - 避免大段文字

### Key Interactions

#### 1. 提交任務

**用戶流程：**
```
點擊 "新建任務" 按鈕
  ↓
彈出對話框：
  - 任務類型（下拉選擇）
  - 任務描述（文本框）
  - 檢查點頻率（滑塊：少/中/多）
  ↓
點擊 "提交"
  ↓
任務卡片出現在任務列表
  ↓
自動切換到任務詳情視圖
```

**交互細節：**
- 任務描述支持 Markdown
- 任務類型有預設模板（Post-MVP）
- 檢查點頻率有解釋提示

#### 2. 監控任務執行

**視覺反饋：**
```
任務卡片顯示：
  ├─ 任務名稱
  ├─ 進度條（動態更新）
  ├─ 當前階段（"任務分解中" / "Agent 1 執行中" / "審查中"）
  ├─ Agent 圖標（顯示哪些 Agent 在工作）
  └─ 評分（如果已完成）

點擊任務卡片 → 展開詳情：
  ├─ 所有子任務列表
  ├─ 每個子任務的狀態
  ├─ 實時日誌窗口（底部）
  └─ Agent 輸出（語法高亮）
```

#### 3. 處理檢查點

**暫停提示：**
```
任務卡片顏色變為黃色
  ↓
頂部顯示通知橫幅：
  "任務 [名稱] 需要你的審查"
  ↓
點擊 → 跳轉到檢查點視圖：
  ├─ 上下文信息（為什麼暫停）
  ├─ Agent 輸出（代碼/文檔）
  ├─ 審查報告（如果有）
  ├─ 評估評分（如果有）
  └─ 決策按鈕：
      [✓ 接受並繼續]  [✏️ 提供糾偏建議]  [✗ 拒絕]
```

#### 4. 糾偏操作

**糾偏界面：**
```
點擊 "提供糾偏建議"
  ↓
彈出側邊欄：
  ├─ Agent 輸出（只讀）
  ├─ 問題描述輸入框
  ├─ 建議修改輸入框
  └─ [提交建議] 按鈕
  ↓
Agent 根據建議修復
  ↓
重新審查 → 如果通過 → 繼續
```

#### 5. 查看結果

**完成後視圖：**
```
任務卡片顏色變為綠色（或紅色如果失敗）
  ↓
顯示：
  ├─ 完成時間
  ├─ 總體評分（大號數字 + 顏色）
  ├─ 各維度評分（小卡片）
  ├─ 生成的代碼/文檔（可下載）
  └─ 完整日誌（可導出）
```

---

## Functional Requirements

### FR-1: Worker Agent 管理

#### FR-1.1: Worker 註冊
**需求：** Worker Agent 啟動時必須能夠自動向後端註冊

**接受標準：**
- Worker 啟動後 5 秒內完成註冊
- 註冊失敗時自動重試（最多 3 次）
- 成功註冊後在前端顯示新機器

#### FR-1.2: Worker 心跳
**需求：** Worker 必須定期發送心跳以證明在線

**接受標準：**
- 每 30 秒發送一次心跳
- 心跳包含最新的資源使用數據
- 90 秒未收到心跳，標記為離線

#### FR-1.3: Worker 資源監控
**需求：** Worker 必須實時監控系統資源

**接受標準：**
- 監控 CPU、內存、磁盤使用率
- 每次心跳上報最新數據
- 前端實時顯示資源圖表

### FR-2: 任務管理

#### FR-2.1: 任務提交
**需求：** 用戶必須能夠提交新任務

**接受標準：**
- 支持文本描述（Markdown）
- 支持選擇檢查點頻率
- 提交後立即返回任務 ID

#### FR-2.2: 任務分解
**需求：** 後端必須能夠將大任務分解為子任務

**接受標準：**
- 識別任務類型
- 根據任務類型生成子任務列表
- 識別子任務之間的依賴關係

#### FR-2.3: 任務分配
**需求：** 後端必須智能分配任務給合適的 Worker

**接受標準：**
- 考慮 Worker 上的 AI 工具
- 考慮 Worker 資源使用情況
- 考慮任務隱私需求
- 負載均衡

#### FR-2.4: 任務執行
**需求：** Worker 必須能夠執行分配的任務

**接受標準：**
- 調用正確的 AI 工具（Claude/Gemini/Ollama）
- 捕獲 AI 輸出
- 上報執行狀態
- 處理錯誤和重試

### FR-3: Agent 協作

#### FR-3.1: Agent 互相審查
**需求：** Agent 完成任務後，另一個 Agent 自動審查

**接受標準：**
- 代碼生成完成後自動觸發審查
- 審查 Agent 檢查代碼質量和問題
- 生成審查報告
- 如果有問題，原 Agent 自動修復

#### FR-3.2: 並行執行
**需求：** 系統必須支持多個 Agent 並行工作

**接受標準：**
- 無依賴的子任務同時分配給不同 Worker
- 前端實時顯示所有並行 Agent
- 正確處理並行任務的結果聚合

### FR-4: 評估框架

#### FR-4.1: Code Quality 評估
**需求：** 自動評估生成代碼的質量

**接受標準：**
- 檢查語法錯誤
- 運行 Linting 工具（pylint/ESLint）
- 計算圈複雜度
- 生成 0-10 分評分

#### FR-4.2: Completeness 評估
**需求：** 評估是否滿足所有需求

**接受標準：**
- 基於需求描述生成檢查清單
- 檢查每個需求是否實現
- 檢查錯誤處理是否完整
- 生成 0-10 分評分

#### FR-4.3: Security 評估
**需求：** 掃描常見安全問題

**接受標準：**
- 運行安全掃描工具（Bandit/npm audit）
- 檢測注入攻擊風險
- 檢測硬編碼敏感信息
- 生成 0-10 分評分

#### FR-4.4: 聚合評分
**需求：** 計算總體評分

**接受標準：**
- 根據權重計算加權平均
- 生成質量等級（Excellent/Good/Acceptable/Poor/Fail）
- 如果 < 5 分，自動標記需要重做

### FR-5: 人類確認檢查點

#### FR-5.1: 自動檢查點觸發
**需求：** 在關鍵點自動暫停等待用戶確認

**接受標準：**
- 代碼生成完成後暫停
- 審查發現問題時暫停
- 評分低於閾值時暫停

#### FR-5.2: 檢查點 UI
**需求：** 提供清晰的檢查點界面

**接受標準：**
- 顯示為什麼暫停
- 顯示 Agent 輸出
- 顯示審查報告
- 顯示評估評分
- 提供決策按鈕

#### FR-5.3: 用戶決策處理
**需求：** 處理用戶的決策

**接受標準：**
- 接受：繼續執行
- 糾偏：傳遞反饋給 Agent，Agent 修復後繼續
- 拒絕：終止任務或重新生成

### FR-6: 實時監控

#### FR-6.1: 實時狀態更新
**需求：** 前端實時顯示所有變化

**接受標準：**
- WebSocket 連接
- Worker 狀態變化實時反映
- 任務進度實時更新
- 延遲 < 500ms

#### FR-6.2: 實時日誌流
**需求：** 顯示 Agent 的實時輸出

**接受標準：**
- 實時顯示 Agent 輸出
- 支持語法高亮
- 支持搜索和過濾
- 支持自動滾動

#### FR-6.3: 資源監控可視化
**需求：** 顯示 Worker 資源使用

**接受標準：**
- 實時更新的圖表
- 顯示 CPU、內存、磁盤
- 歷史趨勢（可選）

---

## Non-Functional Requirements

### Performance

#### NFR-P1: 響應時間
- **任務提交響應**：< 2 秒
- **WebSocket 消息延遲**：< 500ms
- **前端 UI 更新**：< 100ms
- **Worker 註冊**：< 5 秒

#### NFR-P2: 並行處理能力
- 支持至少 10 個 Worker 同時在線
- 支持至少 20 個任務並行執行
- 支持至少 50 個 WebSocket 連接

#### NFR-P3: 資源使用
- **後端內存使用**：< 500MB（空閒）
- **Worker 內存使用**：< 300MB（空閒）
- **Flutter 前端內存使用**：< 200MB

### Security

#### NFR-S1: 數據安全
- 所有 WebSocket 連接使用 WSS (TLS)
- 敏感任務使用本地 LLM（不發送到雲端）
- 用戶數據存儲在本地（MVP 階段）

#### NFR-S2: API 安全
- MVP：後端只綁定 localhost
- Post-MVP：JWT Token 認證
- Rate limiting（防止濫用）

#### NFR-S3: 依賴項安全
- 定期掃描依賴項漏洞
- 及時更新安全補丁

### Scalability

#### NFR-SC1: 橫向擴展
- Worker 可以動態添加/移除
- 無需重啟後端

#### NFR-SC2: 數據庫性能
- PostgreSQL 查詢 < 100ms (95th percentile)
- Redis 操作 < 10ms

### Reliability

#### NFR-R1: 可用性
- Worker 離線後能自動重連
- 任務失敗能自動重試（最多 3 次）
- 網絡中斷後能自動恢復

#### NFR-R2: 數據持久化
- 任務狀態持久化到 PostgreSQL
- 系統重啟後能恢復未完成任務

#### NFR-R3: 錯誤處理
- 所有錯誤必須有清晰的錯誤消息
- 關鍵錯誤記錄到日誌文件
- 用戶友好的錯誤提示

### Usability

#### NFR-U1: 學習曲線
- 新用戶能在 10 分鐘內完成首次任務
- 提供詳細的文檔和視頻教學
- UI 提供上下文提示

#### NFR-U2: 跨平台一致性
- Desktop 和 Web 提供一致的體驗
- UI 適配不同屏幕尺寸

### Maintainability

#### NFR-M1: 代碼質量
- 代碼覆蓋率 > 70%
- 遵循 PEP 8（Python）和 Effective Dart
- 詳細的 API 文檔

#### NFR-M2: 可擴展性
- 評估框架支持自定義評估器
- 支持添加新的 AI 工具
- 插件式架構

---

## Implementation Planning

### Epic Breakdown Required

這份 PRD 包含了大量的功能需求。為了便於實現，需要將需求分解為 **Epics 和 User Stories**。

**建議的 Epic 結構：**

1. **Epic 1: 核心基礎設施**
   - 數據庫設計和實現
   - 後端 API 框架
   - Worker Agent 基礎框架

2. **Epic 2: Worker 管理**
   - Worker 註冊和心跳
   - 資源監控
   - Worker 生命週期管理

3. **Epic 3: 任務協調系統**
   - 任務提交和分解
   - 智能任務分配
   - 並行調度

4. **Epic 4: Flutter 前端**
   - 儀表板主界面
   - 機器管理視圖
   - 任務管理視圖
   - WebSocket 實時通信

5. **Epic 5: AI 工具整合**
   - Claude Code (MCP) 整合
   - Gemini CLI 整合
   - Ollama (Local LLM) 整合
   - 任務執行引擎

6. **Epic 6: Agent 協作機制**
   - Agent 互相審查
   - 並行執行協調
   - 結果聚合

7. **Epic 7: 評估框架**
   - Code Quality 評估器
   - Completeness 評估器
   - Security 評估器
   - 聚合評分引擎

8. **Epic 8: 人類確認系統**
   - 檢查點機制
   - 檢查點 UI
   - 糾偏介面
   - 決策處理

9. **Epic 9: 測試和優化**
   - 端到端測試
   - 性能優化
   - 錯誤處理
   - 文檔撰寫

**Next Step:**

運行 `*create-epics-and-stories` workflow 來將以上 Epic 分解為詳細的 User Stories。

---

## References

- **Product Brief:** docs/product-brief-Multi-Agent-on-the-web-2025-11-11.md
- **Brainstorming Session:** docs/bmm-brainstorming-session-2025-11-11.md

---

## Next Steps

### 立即執行：

1. **✅ PRD 完成** - 當前文檔
2. **Epic & Story Breakdown** - 運行: `*create-epics-and-stories`
3. **UX Design** (推薦) - 運行: `*create-design`
4. **Architecture** (必須) - 運行: `*create-architecture`

### Phase 1: 規劃階段

- [x] Product Brief
- [x] PRD
- [ ] Epic & Stories
- [ ] UX Design (推薦)
- [ ] Architecture

### Phase 2: Solutioning 階段

- [ ] Architecture Document
- [ ] Solutioning Gate Check

### Phase 3: Implementation 階段

- [ ] Sprint Planning
- [ ] Story Development
- [ ] Testing & Validation

---

## Product Magic Summary

**Multi-Agent on the Web 的魔法在於：**

**"半自動的完美平衡"** - 讓 AI 並行執行大部分工作，人類只需在關鍵時刻把關和糾偏，實現速度和質量的最佳結合。

**三大核心創新**支撐這個魔法：
1. **量化評估框架** - 讓質量可見、可追蹤、可改進
2. **可視化監控** - 讓複雜的分布式系統一目了然
3. **靈活的人機協作** - 信任 AI，但保持控制

這不僅僅是一個工具，而是**重新定義 AI 輔助開發的工作方式**。

---

_Created through collaborative discovery between sir and AI PM facilitator._
_Date: 2025-11-11_
