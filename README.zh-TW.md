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
- **多 AI 工具支援**：Claude Code、Gemini CLI、Ollama 等
- **DAG 工作流**：複雜任務依賴與並行執行
- **用戶認證**：JWT 認證與用戶-Worker 綁定
- **即時更新**：WebSocket 即時狀態與任務推送
- **混合式任務分配**：Push + Pull 模式靈活調度

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

### Phase 1（目前）
- [x] 用戶認證 (JWT)
- [x] 基本 Task/Worker CRUD
- [x] Worker 註冊與心跳
- [x] WebSocket 連接
- [x] 桌面 Worker (Electron)
- [x] Docker Worker

### Phase 2（計劃中）
- [ ] DAG 工作流引擎
- [ ] Web 控制台 (Flutter)
- [ ] 工作流編輯器

### Phase 3（計劃中）
- [ ] 多工具支援
- [ ] 手機 Worker

## 為什麼叫 GarageSwarm？

**Garage（車庫）**：就像矽谷車庫創業的精神，用手邊有的資源做出厲害的東西。

**Swarm（蜂群）**：多個 AI Agent 像蜜蜂一樣協同工作，完成複雜任務。

不需要資料中心，不需要雲端大預算。你的車庫，就是你的 AI 基地。

## 授權

MIT License - 詳見 [LICENSE](LICENSE)
