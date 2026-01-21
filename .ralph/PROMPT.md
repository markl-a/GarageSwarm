# GarageSwarm 2.0 - Ralph Development Instructions

## Project Overview

GarageSwarm 是一個多 AI 代理編排平台，目標是在消費級硬體上協調多個 AI CLI 工具（Claude Code, Gemini CLI, Ollama 等）。

## Current Development Phase

**Phase 0: 基礎設施修復** - 修復現有缺陷，為重構做準備

## Development Guidelines

### Code Style
- **Backend (Python)**: 使用 async/await，遵循 FastAPI 最佳實踐
- **Worker (Python)**: asyncio + typing hints
- **Frontend**: 暫時保留 Flutter，後續可能遷移到 React

### Testing
- 所有新功能必須有測試
- 運行 `pytest backend/tests/` 驗證後端
- 運行 `pytest worker-agent/tests/` 驗證 Worker

### Git Workflow
- 使用 conventional commits: `feat:`, `fix:`, `docs:`, `test:`
- 小步提交，每個功能完成後立即 commit

## Current Priority Tasks

請參考 `.ralph/@fix_plan.md` 獲取詳細任務列表。當前優先級：

1. **WebSocket 實現** - 完成 backend/src/api/v1/websocket.py
2. **結果回報端點** - 添加 POST /workers/{id}/report-result
3. **Worker API Key 驗證** - 完成 X-Worker-API-Key header 驗證

## Project Structure

```
bmad-test/
├── backend/           # FastAPI 後端 (port 8080)
│   ├── src/
│   │   ├── api/v1/    # API 端點
│   │   ├── models/    # SQLAlchemy 模型
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # 業務邏輯
│   │   └── auth/      # 認證
│   └── tests/
├── worker-agent/      # Python Docker Worker
│   ├── src/
│   │   ├── agent/     # 核心代理邏輯
│   │   ├── tools/     # AI 工具整合
│   │   └── auth/      # 工具認證
│   └── tests/
├── worker-desktop/    # Electron 桌面 Worker
└── frontend/          # Flutter Web (暫緩)
```

## Key Files to Modify

### Phase 0 Files
- `backend/src/api/v1/websocket.py` - WebSocket 連接處理
- `backend/src/api/v1/workers.py` - 添加結果回報端點
- `backend/src/auth/worker_auth.py` - Worker API Key 驗證
- `worker-agent/src/agent/connection.py` - WebSocket 客戶端
- `worker-agent/src/agent/result_reporter.py` - 結果回報 (新增)

## Build and Run Commands

```bash
# 啟動後端
cd backend && python -m uvicorn src.main:app --host 0.0.0.0 --port 8080

# 運行後端測試
cd backend && pytest tests/ -v

# 運行 Worker 測試
cd worker-agent && pytest tests/ -v

# 啟動 Docker 環境
docker-compose up -d
```

## Exit Conditions

當以下條件滿足時，標記 `EXIT_SIGNAL: true`：

1. 當前 Phase 的所有任務在 `@fix_plan.md` 中標記為完成
2. 所有測試通過
3. 代碼已 commit 並 push

## RALPH_STATUS Output Format

每次完成任務後，請輸出：

```
RALPH_STATUS:
STATUS: IN_PROGRESS | COMPLETE
WORK_TYPE: feature | bugfix | refactor | test | docs
FILES_MODIFIED: [list of files]
TASKS_COMPLETED: [list of completed tasks]
NEXT_PRIORITY: [next task to work on]
EXIT_SIGNAL: false | true
NOTES: [any relevant notes]
```

## Important Notes

- Backend 運行在 port 8080（port 8000 被 lemonade_server 佔用）
- 使用 IPv4 (127.0.0.1) 而非 localhost
- 所有數據庫操作使用 async/await
- 敏感信息不要硬編碼，使用環境變量
