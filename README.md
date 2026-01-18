# GarageSwarm

A cross-platform multi-AI agent collaboration platform. Run your own AI swarm on whatever machines you have lying around - old laptops, desktop PCs, even that dusty server in the corner.

## Overview

Coordinate multiple AI CLI tools (Claude Code, Gemini CLI, Ollama) across distributed workers with a centralized control panel. No fancy infrastructure needed - just your garage-tier hardware.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Web Control Panel                            │
│                    (Flutter Web Dashboard)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                         │
│         Auth | Tasks | Workers | Workflows | WebSocket          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│Desktop Worker │   │ Docker Worker │   │ Mobile Worker │
│  (Electron)   │   │   (Python)    │   │  (Flutter)    │
│ Claude Code   │   │ Claude Code   │   │   API-based   │
│ Gemini CLI    │   │ Gemini CLI    │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

## Features

- **Multi-platform Workers**: Desktop (Electron), Docker (Python), Mobile (Flutter)
- **Multiple AI Tools**: Claude Code, Gemini CLI, Antigravity, OpenCode, Ollama, Aider, GitHub Copilot, Amazon Q, OpenAI API, ComfyUI, and more
- **Extensible Tool System**: Plugin architecture for custom AI tool integration
- **DAG Workflows**: Complex task dependencies with parallel execution
- **User Authentication**: JWT-based auth with user-worker binding
- **Real-time Updates**: WebSocket for live status and task push
- **Hybrid Task Assignment**: Push + Pull modes for flexible distribution

## Use Cases

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

## Project Structure

```
.
├── backend/           # FastAPI backend server
├── frontend/          # Flutter web control panel
├── worker-agent/      # Python worker agent (Docker)
├── worker-desktop/    # Electron desktop worker (Windows/Mac/Linux)
├── docker-compose.yml # Docker deployment
└── ARCHITECTURE.md    # Detailed architecture documentation
```

## Quick Start

### 1. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

Or with Docker:

```bash
docker-compose up -d
```

### 2. Start Desktop Worker

```bash
cd worker-desktop
npm install
npm start
```

### 3. Start Docker Worker

```bash
cd worker-agent
docker-compose up -d
```

## Development Status

**Current Version: v0.0.1**

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design.

### Phase 1: MVP (Current)

#### Backend ✅
- [x] User authentication (JWT)
- [x] Basic Task/Worker CRUD
- [x] Worker registration and heartbeat
- [x] WebSocket connection

#### Desktop Worker 🔄 In Progress
- [x] Electron app structure
- [x] Login page (API Key auth)❯ 
- [x] Dashboard UI
- [x] Windows testing
- [ ] Mac testing
- [ ] Linux testing
- [x] End-to-end task execution flow

#### AI Tools ✅ Core Complete
- [x] Tool registry architecture
- [x] Tool auto-detection (startup)
- [x] Claude Code - Anthropic CLI
- [x] Gemini CLI - Google AI
- [x] Ollama - Local LLM
- [ ] Aider - AI pair programming
- [ ] Antigravity - Google AI Agent
- [ ] OpenCode - Terminal AI Assistant
- [ ] GitHub Copilot CLI
- [ ] Amazon Q Developer
- [ ] Cody - Sourcegraph AI
- [ ] OpenAI API (GPT-4, o1)
- [ ] ComfyUI - Stable Diffusion 工作流
- [ ] Custom tool plugins

#### Multimodal Tools 🎨 Planned
- [ ] ComfyUI API 整合 (圖像生成)
- [ ] Suno API (音樂生成)
- [ ] Kling/Runway (影片生成)
- [ ] ElevenLabs (語音生成)

#### Frontend ⏸️ Planned
- [ ] Flutter Web Dashboard

### Phase 2: Workflow Engine
- [ ] Workflow data models
- [ ] DAG executor
- [ ] Workflow editor UI
- [ ] Workflow templates (可重複使用的流程模板)

### Phase 3: 多模態 & 數據系統
- [ ] 檔案儲存系統 (S3/本地)
- [ ] 多模態輸出處理 (圖片/音樂/影片)
- [ ] **ComfyUI 整合** (Stable Diffusion 工作流)
- [ ] 數據源連接器 (API/爬蟲/資料庫)
- [ ] 媒體預覽和管理介面

### Phase 4: 記憶 & 學習系統
- [ ] 向量資料庫整合 (經驗儲存)
- [ ] 執行歷史記錄和分析
- [ ] 反饋循環 (用戶評分 → 自動優化)
- [ ] 模型表現追蹤 (選擇最佳 AI 工具)

### Phase 5: 排程 & 自動化
- [ ] Cron 定時任務
- [ ] 事件觸發器 (Webhook)
- [ ] 外部平台 API 整合 (社群媒體、交易所)
- [ ] 監控和告警系統

### Phase 6: 進階功能
- [ ] A/B 測試框架
- [ ] 成本追蹤 (Token/費用統計)
- [ ] 多用戶協作
- [ ] Mobile Workers (Flutter Android/iOS)

## Roadmap Vision

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

## License

MIT License - see [LICENSE](LICENSE) for details.
