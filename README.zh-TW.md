# GarageSwarm

用你車庫裡的破電腦，組成自己的 AI 蜂群。

## 簡介

GarageSwarm 是一個跨平台的多 AI Agent 協作平台。不需要昂貴的伺服器，用家裡閒置的舊筆電、桌機、甚至角落積灰的那台老電腦，就能跑起你的 AI 軍團。

```
┌─────────────────────────────────────────────────────────────────┐
│                      Web 控制台                                  │
│                   (Flutter Web Dashboard)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    後端 API (FastAPI)                            │
│           認證 | 任務 | Worker | 工作流 | WebSocket              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  桌面 Worker  │   │ Docker Worker │   │  手機 Worker  │
│  (Electron)   │   │   (Python)    │   │  (Flutter)    │
│ Claude Code   │   │ Claude Code   │   │   API 模式    │
│ Gemini CLI    │   │ Gemini CLI    │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

## 特色

- **多平台 Worker**：桌面版 (Electron)、Docker 版 (Python)、手機版 (Flutter)
- **多 AI 工具支援**：Claude Code、Gemini CLI、Antigravity、OpenCode、Ollama、Aider、GitHub Copilot、Amazon Q、OpenAI API、ComfyUI 等
- **可擴展工具系統**：插件架構支援自訂 AI 工具整合
- **DAG 工作流**：複雜任務依賴與並行執行
- **用戶認證**：JWT 認證與用戶-Worker 綁定
- **即時更新**：WebSocket 即時狀態與任務推送
- **混合式任務分配**：Push + Pull 模式靈活調度

## 應用場景

> ⚠️ **Under Development** - The following use cases are planned features, still in development and require validation and testing.
>
> ⚠️ **開發中** - 以下應用場景為規劃中的功能，目前仍在開發階段，尚需驗證與測試。

GarageSwarm 可以用來處理各種需要多 AI 協作的任務：

### 💻 軟體開發
- **分散式程式碼審查** - 多個 AI 同時審查不同模組
- **大規模重構** - 協調多個 AI 同時修改相關檔案
- **測試生成** - 並行為多個模組生成單元測試
- **文件生成** - 自動生成 API 文件和使用說明

### 📊 資料分析 & 預測
- **股票分析** - 多 AI 分析不同指標、時間週期，綜合研判
- **博彩預測** - 並行分析歷史數據、賠率變化、統計模型
- **量化策略** - 多模型同時回測，選擇最優策略
- **日誌分析** - 分散式處理大量日誌數據

### ✍️ 內容創作
- **小說生成** - 多 AI 協作：大綱、角色、章節並行創作
- **多語言翻譯** - 同時翻譯成多種語言
- **行銷文案** - 批量生成、A/B 測試變體

### 🎨 多模態創作 (ComfyUI + AI)
- **漫畫生成** - 劇本 AI + 分鏡 AI + ComfyUI 繪圖流水線
- **音樂生成** - 作曲、編曲、混音多階段協作
- **影像生成** - 腳本 → 分鏡 → ComfyUI/Kling → 後製流程
- **角色一致性** - ComfyUI LoRA + ControlNet 保持風格統一

### 📱 社群媒體自動化
- **內容排程** - 定時發布多平台內容
- **互動回覆** - 自動回覆評論和私訊
- **數據追蹤** - 監控成效並自動優化策略

### 🎯 產品設計
- **需求分析** - 多 AI 從不同角度分析用戶需求
- **原型設計** - 並行生成多個設計方案
- **用戶測試** - 模擬不同用戶群體的反饋

### 🔄 自動化運維
- **CI/CD 整合** - AI 輔助的構建、測試、部署
- **監控告警** - 智能分析異常並建議處理方案
- **定時任務** - 排程執行重複性工作

### 🧠 持續學習優化
- **經驗累積** - 記錄每次執行結果和用戶反饋
- **策略優化** - 根據歷史數據自動調整參數
- **模型選擇** - 追蹤不同 AI 在各任務的表現，自動選擇最佳工具

## 專案結構

```
.
├── backend/           # FastAPI 後端伺服器
├── frontend/          # Flutter Web 控制台
├── worker-agent/      # Python Worker Agent (Docker)
├── worker-desktop/    # Electron 桌面 Worker (Windows/Mac/Linux)
├── docker-compose.yml # Docker 部署配置
└── ARCHITECTURE.md    # 詳細架構文件
```

## 快速開始

### 1. 啟動後端

```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

或用 Docker：

```bash
docker-compose up -d
```

### 2. 啟動桌面 Worker

```bash
cd worker-desktop
npm install
npm start
```

### 3. 啟動 Docker Worker

```bash
cd worker-agent
docker-compose up -d
```

## 開發進度

**目前版本：v0.0.1**

詳細設計請參考 [ARCHITECTURE.md](ARCHITECTURE.md)。

### Phase 1：MVP（目前）

#### 後端 ✅
- [x] 用戶認證 (JWT)
- [x] 基本 Task/Worker CRUD
- [x] Worker 註冊與心跳
- [x] WebSocket 連接

#### 桌面 Worker 🔄 進行中
- [x] Electron 應用框架
- [x] 登入頁面 (API Key 認證)
- [x] Dashboard UI
- [x] Windows 測試
- [ ] Mac 測試
- [ ] Linux 測試
- [x] 端到端任務執行流程

#### AI 工具 ✅ 核心完成
- [x] 工具註冊架構
- [x] 工具自動偵測（啟動時）
- [x] Claude Code - Anthropic CLI
- [x] Gemini CLI - Google AI
- [x] Ollama - 本地 LLM
- [ ] Aider - AI 結對編程
- [ ] Antigravity - Google AI Agent
- [ ] OpenCode - 終端 AI 助手
- [ ] GitHub Copilot CLI
- [ ] Amazon Q Developer
- [ ] Cody - Sourcegraph AI
- [ ] OpenAI API (GPT-4, o1)
- [ ] ComfyUI - Stable Diffusion 工作流
- [ ] 自訂工具插件

#### 多模態工具 🎨 計劃中
- [ ] ComfyUI API 整合 (圖像生成)
- [ ] Suno API (音樂生成)
- [ ] Kling/Runway (影片生成)
- [ ] ElevenLabs (語音生成)

#### 前端 ⏸️ 計劃中
- [ ] Flutter Web 控制台

### Phase 2：工作流引擎
- [ ] 工作流資料模型
- [ ] DAG 執行器
- [ ] 工作流編輯器 UI
- [ ] 工作流模板（可重複使用的流程模板）

### Phase 3：多模態 & 數據系統
- [ ] 檔案儲存系統 (S3/本地)
- [ ] 多模態輸出處理 (圖片/音樂/影片)
- [ ] **ComfyUI 整合** (Stable Diffusion 工作流)
- [ ] 數據源連接器 (API/爬蟲/資料庫)
- [ ] 媒體預覽和管理介面

### Phase 4：記憶 & 學習系統
- [ ] 向量資料庫整合 (經驗儲存)
- [ ] 執行歷史記錄和分析
- [ ] 反饋循環 (用戶評分 → 自動優化)
- [ ] 模型表現追蹤 (選擇最佳 AI 工具)

### Phase 5：排程 & 自動化
- [ ] Cron 定時任務
- [ ] 事件觸發器 (Webhook)
- [ ] 外部平台 API 整合 (社群媒體、交易所)
- [ ] 監控和告警系統

### Phase 6：進階功能
- [ ] A/B 測試框架
- [ ] 成本追蹤 (Token/費用統計)
- [ ] 多用戶協作
- [ ] Mobile Workers (Flutter Android/iOS)

## 發展藍圖

```
Phase 1 (MVP)          Phase 2-3              Phase 4-6
    │                      │                      │
    ▼                      ▼                      ▼
┌─────────┐          ┌──────────┐          ┌──────────────┐
│ 基礎任務 │    →     │ 工作流程  │    →     │  智能自動化   │
│  執行   │          │ 多模態    │          │  持續學習    │
└─────────┘          └──────────┘          └──────────────┘
  單一任務              DAG 流程              記憶 + 優化
  手動觸發              檔案處理              定時 + 事件
  文字輸出              多媒體輸出            自動選擇最佳策略
```

## 為什麼叫 GarageSwarm？

**Garage（車庫）**：就像矽谷車庫創業的精神，用手邊有的資源做出厲害的東西。

**Swarm（蜂群）**：多個 AI Agent 像蜜蜂一樣協同工作，完成複雜任務。

不需要資料中心，不需要雲端大預算。你的車庫，就是你的 AI 基地。

## 授權

MIT License - 詳見 [LICENSE](LICENSE)
