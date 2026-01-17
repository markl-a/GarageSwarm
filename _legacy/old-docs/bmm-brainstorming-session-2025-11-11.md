# 頭腦風暴會議報告
## Multi-Agent on the Web

**專案名稱：** Multi-Agent on the Web
**會議日期：** 2025-11-11
**主持人：** Mary (Analyst Agent)
**參與者：** sir
**會議時長：** 約 2 小時
**會議類型：** 技術架構探索 + 系統設計

---

## 📋 執行摘要

本次頭腦風暴會議針對「Multi-Agent on the Web」專案進行了深入的技術架構探索。專案目標是建立一個跨平台（桌面、手機、Web）的多代理協作平台，整合市面上主流 AI 工具（Claude Code、Gemini、Codex 等）以及本地 LLM，通過分布式 Worker 節點實現更快速、更完善的任務執行。

會議通過網絡研究、方案對比、架構細化三個階段，最終確定了基於 Flutter 前端 + 分布式 Worker Agent 的技術架構，並完成了 Worker Agent 的詳細設計和完整數據流定義。

---

## 🎯 專案背景

### 專案願景

建立一個統一的多代理協作平台，能夠：
- 🖥️ **跨平台支援**：桌面、手機、Web 統一體驗
- 🤖 **AI 工具整合**：Claude Code、Gemini CLI、Codex、各類 AI CLI
- 🚀 **Multi-Agent 協作**：通過多代理方式更快更完善地完成任務
- 💻 **Local LLM 集成**：保護隱私敏感數據

### 核心挑戰

1. 如何實現真正的分布式多機器協作？
2. 如何整合異構的 AI 工具（API、CLI、本地模型）？
3. 如何保證系統的可靠性和容錯性？
4. 如何提供良好的用戶體驗（可視化、實時更新）？

---

## 🔍 研究發現總結

### 1. 多代理協作架構模式（2025 最佳實踐）

**主流協調模式：**
- **集中式協調**：單一 orchestrator 分配任務和監控進度
- **分散式協調**：agents 之間協商角色
- **混合模式**：集中監督 + 局部代理自治

**關鍵技術：**
- 持久化記憶機制（跨 agent 交互保持上下文）
- 任務狀態分離（與對話歷史分開追蹤）
- 容錯設計（circuit breaker 模式、agent 隔離）

### 2. Claude 與 Gemini 整合方案

**Model Context Protocol (MCP)：**
- Anthropic 推出的開源框架
- 實現 Claude Code 與 Gemini CLI 無縫協作
- 支援多模型統一協調

**Dual-Agent 工作流程：**
- 一個 agent 檢測（detection）
- 一個 agent 執行（execution）
- 持續改進軟體專案

**支援框架：**
- CrewAI：整合 Claude 3、Gemini、Llama
- LangGraph：支援所有主流 LLM

### 3. 本地 LLM 整合架構

**核心優勢：**
- 每個 agent 可使用不同 LLM
- 敏感資料使用本地模型
- 簡單任務使用便宜的 API
- 複雜任務使用高級 API

**推薦框架：**
- **Langroid**：輕量級 Python 框架，支援本地 LLM
- **LlamaIndex llama-agents**：微服務架構，支援 LocalLauncher

### 4. 跨平台開發工具（2025）

**推薦技術棧：**
- **Tauri**：Rust + JS，輕量級（比 Electron 小 90%），適合桌面
- **Flutter**：單一代碼庫，支援移動/Web/桌面
- **Theia IDE**：開源 IDE，Web 和桌面，內建 AI 功能

---

## 💡 提出的架構方案

### 方案 A：MCP 為核心的統一協調平台

**核心理念：** 使用 Model Context Protocol 作為統一通信層

**技術棧：**
- 前端：Tauri (桌面) + Flutter Web (Web/移動)
- 協調層：基於 MCP 的自定義 orchestrator
- AI 整合：MCP servers + API wrappers + Ollama

**優勢：**
- ✅ MCP 是業界標準，Anthropic 官方支持
- ✅ 輕量級架構
- ✅ 跨平台統一體驗

**挑戰：**
- ⚠️ MCP 相對較新，生態系統還在成長
- ⚠️ 需要為非 MCP 原生工具編寫適配器

### 方案 B：微服務化多代理系統

**核心理念：** 每個 AI 工具作為獨立微服務，LLM 驅動的控制平面協調

**技術棧：**
- 前端：Flutter (全平台)
- 後端：LangGraph 或 CrewAI 作為控制平面
- 服務：Docker 容器化的獨立 AI 服務

**優勢：**
- ✅ 高度可擴展
- ✅ 靈活的 LLM 選擇
- ✅ 成熟的框架

**挑戰：**
- ⚠️ 部署複雜度較高
- ⚠️ 需要管理多個服務的生命周期

### 方案 C：Dual-Agent 混合協作系統

**核心理念：** 模仿 Gemini CLI + Claude Code 的雙代理模式，擴展到多工具

**技術棧：**
- 界面：Python CLI + 簡單 Flask Web UI
- 協調：自定義 Python coordinator
- 集成：直接調用各 AI 工具 API

**優勢：**
- ✅ 快速開發（MVP 2-4 週）
- ✅ 簡單易維護

**挑戰：**
- ⚠️ 跨平台體驗不如原生應用
- ⚠️ 可擴展性有限

---

## 🏆 最終選定架構

### 分布式 Worker 節點架構

**核心設計理念：**

```
Flutter 跨平台客戶端 (統一控制面板)
        ↓
後端協調服務器 (Backend)
    - 任務隊列
    - 機器註冊表
    - 負載均衡
    - Agent 協調器
        ↓
分布式 Worker 節點 (多台機器)
    - Machine-1: Claude Code + Local LLM
    - Machine-2: Gemini CLI + Codex
    - Machine-N: 自定義工具
```

**選擇理由：**

1. **真正的分布式**：利用多台機器的計算資源
2. **靈活的工具部署**：每台機器可運行不同的 AI 工具
3. **本地隱私保護**：敏感數據留在本地機器的 Local LLM
4. **可視化管理**：Flutter 前端清晰顯示所有工作節點狀態
5. **橫向擴展**：輕鬆添加新機器

**技術棧：**
- **前端**：Flutter (Desktop/Mobile/Web)
- **後端**：FastAPI (Python) + PostgreSQL + Redis
- **Worker**：Python 守護進程
- **通信**：WebSocket (實時) + REST API
- **AI 工具**：MCP (Claude), API (Gemini/Codex), Ollama (Local LLM)

---

## 🔧 Worker Agent 詳細設計亮點

### 核心架構組件

1. **Agent Core**：主控制器，管理生命周期
2. **Connection Manager**：WebSocket 連接，自動重連
3. **Task Executor**：任務執行器，並發控制
4. **Tool Manager**：AI 工具管理器，統一接口
5. **Resource Monitor**：資源監控器，CPU/內存/磁盤監控
6. **Logger**：日誌系統

### 關鍵特性

✅ **自動註冊機制**：Worker 啟動時自動向後端註冊
✅ **心跳監控**：每 30 秒發送心跳，5 分鐘無響應標記離線
✅ **智能任務分配**：基於資源狀態、工具可用性、隱私需求分配
✅ **資源保護**：CPU/內存超過閾值自動拒絕新任務
✅ **容錯機制**：任務失敗自動重試，最多 3 次
✅ **跨平台支持**：Windows/Linux/Mac 統一實現

### 通信協議

**WebSocket 消息類型：**
- `register`：Worker 註冊
- `heartbeat`：心跳
- `task`：任務分配
- `task_started`：任務開始確認
- `task_completed`：任務完成
- `task_failed`：任務失敗
- `cancel_task`：取消任務

### 配置文件設計

```yaml
agent:
  machine_id: auto-generated-uuid
  machine_name: "Home-PC"
  backend_url: "wss://your-backend.com/ws"
  api_key: "your-api-key"
  heartbeat_interval: 30
  max_concurrent_tasks: 3

tools:
  claude_code:
    enabled: true
    path: "/path/to/claude-code"
  gemini_cli:
    enabled: true
    command: "gemini"
  local_llm:
    enabled: true
    type: "ollama"
    host: "http://localhost:11434"
```

---

## 🌊 完整數據流定義

### 流程 1：系統初始化和機器註冊

```
Worker 啟動
 → 加載配置
 → 初始化組件
 → 建立 WebSocket 連接
 → 發送註冊消息 {machine_id, system_info, tools}
 → 後端驗證並保存到 Redis + PostgreSQL
 → 返回註冊確認
 → Worker 進入運行狀態 (心跳、監控、任務接收)
```

### 流程 2：持續心跳和狀態同步

```
每 30 秒觸發
 → Resource Monitor 採集數據 (CPU, Memory, Disk)
 → Task Executor 統計任務狀態
 → 發送心跳消息
 → 後端更新 Redis 機器狀態
 → 通知前端實時更新

後端健康檢查 (每 1 分鐘)
 → 檢查所有機器的最後心跳時間
 → 超過 5 分鐘無響應 → 標記離線
 → 重新分配該機器上的任務
```

### 流程 3：用戶提交任務（完整鏈路）

```
Flutter 前端
 → 用戶填寫任務表單並提交
 → POST /api/tasks {task_type, tool_preference, data}
 → 後端驗證並生成 task_id
 → 保存到 PostgreSQL

智能任務分配 (Load Balancer)
 → Step 1: 篩選候選機器
    - 狀態 = online/healthy
    - 擁有所需工具
    - available_slots > 0
    - 隱私需求檢查
 → Step 2: 評分和排序
    - 基於 CPU/內存使用率
    - 可用槽位數
    - 地理位置 (延遲)
 → Step 3: 選擇最佳機器並分配

任務派發
 → 通過 WebSocket 發送任務到選定的 Worker
 → Worker 接收並發送 task_started 確認
 → 後端更新狀態 = "running"
 → 前端實時顯示 "任務正在 machine-1 上執行"

Worker 執行任務
 → Task Executor 調用相應的 AI 工具
 → Claude Code/Gemini/Codex/Local LLM 執行
 → 獲取結果

結果返回
 → Worker 發送 task_completed {result, execution_time}
 → 後端保存結果到 PostgreSQL
 → 釋放 Worker 資源
 → 通知前端任務完成
 → Flutter 顯示結果通知
```

### 流程 4：錯誤處理和容錯機制

**場景 1：Worker 執行任務失敗**
```
Worker 發送 task_failed {error, error_code}
 → 後端更新狀態 = "failed"
 → 釋放資源
 → 決策：重試 (retry_count < 3) 或放棄
 → 如果重試：重新分配到其他機器
 → 通知前端失敗原因
```

**場景 2：Worker 突然離線**
```
後端健康檢查發現離線 (超過 5 分鐘無心跳)
 → 標記機器 = "offline"
 → 查找該機器上的活躍任務
 → 重新分配所有任務到其他機器
 → 通知前端機器狀態變化
```

**場景 3：後端服務重啟**
```
後端重啟
 → 從 PostgreSQL 恢復持久化數據
 → 重建 Redis 緩存
 → 等待 Worker 重新連接 (自動重連)
 → 重新分配中斷的任務
 → 通知前端系統已恢復
```

**場景 4：前端網絡中斷**
```
Flutter WebSocket 斷開
 → 自動重連 (指數退避)
 → 重連成功後重新訂閱更新
 → 從後端同步最新狀態
 → 如果重連失敗：顯示離線模式提示
```

---

## 📊 關鍵數據結構

### PostgreSQL Schema

**machines 表：**
- machine_id (UUID, PK)
- machine_name, status, os, cpu_count, total_memory_gb
- tools (JSONB)
- created_at, last_heartbeat

**tasks 表：**
- task_id (UUID, PK)
- user_id, task_type, status, priority, privacy_level
- assigned_machine (FK)
- task_data (JSONB), result (JSONB)
- error, retry_count, execution_time
- created_at, assigned_at, started_at, completed_at

### Redis 數據結構

```redis
# 機器信息
HSET machine:<machine_id>
  status, last_heartbeat, cpu_percent, memory_percent
  active_tasks, available_slots

# 活躍機器列表
SADD active_machines machine-1 machine-2 ...

# 工具索引
SADD tool:claude_code:machines machine-1 machine-2
SADD tool:local_llm:machines machine-1 machine-3
```

---

## 🎯 關鍵洞察與發現

### 1. 分布式架構的核心挑戰

**機器註冊和發現**
- 需要可靠的心跳機制
- 5 分鐘無響應判定為離線的平衡點

**網絡通信和安全**
- WebSocket 長連接 + TLS 加密
- JWT Token 認證必不可少
- 考慮使用 Tailscale 實現 mesh 網絡

**任務分配策略**
- 多維度評分系統：資源、工具、隱私、延遲
- 需要平衡負載和專業化

### 2. 容錯設計的重要性

**三層容錯機制：**
1. **Worker 層**：資源檢查，超載拒絕任務
2. **後端層**：任務重試（最多 3 次），機器離線處理
3. **前端層**：自動重連，離線模式

**數據持久化策略：**
- Redis：實時狀態（快速查詢）
- PostgreSQL：持久化數據（可恢復）

### 3. 用戶體驗的關鍵點

**實時可見性：**
- 機器在線狀態實時更新
- 任務執行進度可視化
- 資源使用率儀表板

**智能提示：**
- "您的任務涉及敏感數據，建議使用本地 LLM"
- "Machine-1 負載較高，已分配到 Machine-2"

### 4. 技術選型理由

**為什麼選擇 Flutter？**
- 單一代碼庫支援所有平台
- 性能優秀（原生編譯）
- 豐富的 UI 組件庫

**為什麼選擇 FastAPI？**
- 原生異步支援（高併發）
- WebSocket 支援完善
- 自動 API 文檔生成

**為什麼選擇 Redis + PostgreSQL？**
- Redis：高速緩存，適合實時狀態
- PostgreSQL：強大的 JSONB 支援，適合複雜查詢

---

## 🚀 下一步行動建議

### 立即行動（按 BMAD 流程）

1. **進入 Product Brief 階段**
   - 明確產品願景和價值主張
   - 定義目標用戶
   - 確定核心功能優先級
   - 設定成功指標

2. **完成 PRD（產品需求文檔）**
   - 詳細功能需求
   - 用戶故事和 Epic
   - 非功能性需求

3. **架構詳細設計（Architecture 階段）**
   - 後端 API 詳細設計
   - 數據庫 Schema 優化
   - Flutter 前端架構
   - 安全性設計

### MVP 開發路線圖（估時 10-15 週）

**Phase 1：核心基礎設施（2-3 週）**
- [ ] 後端 API 框架搭建
- [ ] Worker Agent 基礎實現
- [ ] Redis 任務隊列
- [ ] PostgreSQL 數據庫

**Phase 2：Flutter 前端（2-3 週）**
- [ ] 機器列表顯示
- [ ] 實時狀態更新
- [ ] 基礎任務提交界面

**Phase 3：AI 工具整合（3-4 週）**
- [ ] Claude Code MCP 整合
- [ ] Gemini CLI 包裝器
- [ ] Codex API 整合
- [ ] Ollama 本地 LLM

**Phase 4：智能協調（2-3 週）**
- [ ] 任務智能分配算法
- [ ] 負載均衡
- [ ] 失敗重試機制

**Phase 5：安全和監控（1-2 週）**
- [ ] JWT 認證
- [ ] TLS 加密
- [ ] Prometheus 監控

---

## 📝 會議產出物

### 文檔產出

1. ✅ **本報告**：完整的頭腦風暴會議記錄
2. ✅ **架構方案對比**：三個方案的優劣分析
3. ✅ **Worker Agent 設計文檔**：包含完整代碼結構
4. ✅ **數據流定義**：4 個核心流程的詳細說明
5. ✅ **數據結構設計**：PostgreSQL 和 Redis Schema

### 待辦事項

- [ ] 進入 Product Brief 工作流程
- [ ] 細化目標用戶畫像
- [ ] 確定核心功能 MVP 範圍
- [ ] 估算開發成本和時間

---

## 🎓 關鍵學習點

### 技術洞察

1. **分布式系統的本質是狀態管理**
   - 心跳機制是分布式系統的心臟
   - 狀態同步需要雙層存儲（Redis + PostgreSQL）

2. **容錯設計不是可選項**
   - 每個組件都可能失敗
   - 重試、降級、隔離是核心策略

3. **用戶體驗來自可見性**
   - 實時狀態更新
   - 清晰的錯誤提示
   - 進度可視化

### 架構決策

1. **選擇 Flutter 是正確的**
   - 跨平台統一體驗
   - 性能和開發效率平衡

2. **分布式 Worker 模式的優勢**
   - 真正利用多機器資源
   - 靈活的工具部署
   - 隱私保護（本地 LLM）

3. **WebSocket + REST API 組合**
   - WebSocket：實時通信
   - REST API：歷史數據查詢

---

## 📊 會議統計

**會議時長：** 約 2 小時
**生成想法數量：** 50+ 個技術點
**提出方案數量：** 3 個完整架構方案
**最終選定方案：** 1 個（分布式 Worker 架構）
**產出文檔頁數：** 約 40 頁（包含詳細代碼）
**定義的數據流程：** 4 個核心流程
**設計的數據結構：** 2 個數據庫表 + 5 個 Redis 結構

---

## 🎯 結論

本次頭腦風暴會議成功地：

1. ✅ 通過網絡研究了解了 2025 年最新的 Multi-Agent 技術趨勢
2. ✅ 提出並對比了三個可行的架構方案
3. ✅ 選定了最適合專案需求的分布式 Worker 架構
4. ✅ 完成了 Worker Agent 的詳細技術設計
5. ✅ 定義了完整的數據流和數據結構
6. ✅ 規劃了 MVP 開發路線圖

專案已具備清晰的技術方向和實現路徑。下一步將進入 **Product Brief** 階段，從產品和商業角度進一步明確專案願景、目標用戶和成功指標。

---

**生成時間：** 2025-11-11
**報告版本：** v1.0
**下一步工作流程：** Product Brief
**預計時長：** 2-3 小時

---

*本報告由 BMAD-METHOD 的 Analyst Agent (Mary) 生成*
*使用工作流程：brainstorm-project*
