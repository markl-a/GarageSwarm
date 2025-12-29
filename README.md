# Multi-Agent on the Web

**分布式多Agent編排平台** - 協調多個AI工具（Claude Code, Gemini, Ollama）跨分布式機器執行，實現2-3x速度提升和4層質量保證。

## 項目概覽

Multi-Agent on the Web 是一個革命性的分布式多Agent編排平台，讓開發者能夠：

- 🚀 **並行執行** - 將任務分解並分配給多台機器，實現2-3x速度提升
- 🤝 **Agent協作** - 多個Agent互相審查、並行工作、投票決策
- 🔍 **4層質量保證** - Agent互審 + 人工檢查點 + 投票機制 + 評估框架
- 📊 **實時可視化** - 看到所有Agent和機器的實時狀態
- 🎯 **半自動化** - 在關鍵決策點保持人工控制

## 核心特性

### 1. 分布式Worker管理
- 支持10+台機器作為Worker
- 實時資源監控（CPU、內存、磁盤）
- 自動故障轉移和重試

### 2. 智能任務協調
- LLM驅動的任務分解（含備援規則模板）
- 智能任務分配（工具匹配50% + 資源30% + 隱私20%）
- DAG依賴管理和並行調度

### 3. 多AI工具集成
- **Claude Code** - MCP協議整合
- **Gemini CLI** - Google AI SDK
- **Local LLM (Ollama)** - 隱私敏感任務

### 4. Agent協作與審查
- Agent B審查Agent A的工作
- 自動修復（最多3次循環）
- 超過閾值自動上報人工

### 5. 量化評估框架
- **5維度評估**：Code Quality, Completeness, Security, Architecture Alignment, Testability
- 自動化工具：pylint, ESLint, Bandit, radon
- 評分 < 7.0 自動觸發checkpoint

### 6. 人工檢查點與糾偏
- 可配置檢查頻率（low/medium/high）
- 評估驅動的智能觸發
- 結構化糾偏反饋

## 技術架構

### 前端
- **Flutter 3.16+** - 跨平台UI（Desktop + Web）
- **Riverpod** - 狀態管理
- **Material Design 3** - 設計系統

### 後端
- **FastAPI 0.100+** - 異步API框架
- **PostgreSQL 15+** - 主數據庫
- **Redis 7+** - 實時狀態和緩存
- **WebSocket** - 實時通信

### Worker Agent
- **Python 3.11+** - Worker SDK
- **asyncio** - 異步任務執行
- **psutil** - 資源監控

## 項目結構

```
bmad-test/
├── backend/              # FastAPI 後端
│   ├── src/
│   │   ├── api/         # REST API 端點
│   │   ├── services/    # 業務邏輯
│   │   ├── models/      # SQLAlchemy ORM
│   │   ├── repositories/# 數據訪問層
│   │   └── main.py      # 應用入口
│   ├── tests/           # 測試
│   ├── alembic/         # 數據庫遷移
│   └── requirements.txt
│
├── frontend/            # Flutter 前端
│   ├── lib/
│   │   ├── screens/     # UI頁面
│   │   ├── widgets/     # 自定義組件
│   │   ├── providers/   # Riverpod providers
│   │   └── services/    # API服務
│   └── pubspec.yaml
│
├── worker-agent/        # Worker Agent SDK
│   ├── src/
│   │   ├── agent/       # Agent核心
│   │   ├── tools/       # AI工具適配器
│   │   └── main.py      # CLI入口
│   └── config/          # 配置文件
│
├── docs/                # 項目文檔
│   ├── architecture.md  # 架構設計
│   ├── PRD.md          # 產品需求
│   ├── epics.md        # Epic拆分
│   └── sprint-1-plan.md# Sprint計劃
│
├── docker/              # Docker配置
└── scripts/             # 工具腳本
```

## 快速開始

### 環境要求

- Docker 24+ & Docker Compose 2.23+
- Python 3.11+
- Flutter 3.16+ (可選，用於前端開發)
- Git

### 本地開發

1. **克隆項目**
   ```bash
   git clone <repository-url>
   cd bmad-test
   ```

2. **配置環境變量**
   ```bash
   cp backend/.env.example backend/.env
   # 編輯 .env 填入必要的配置
   ```

3. **啟動所有服務**
   ```bash
   make up
   # 或
   docker-compose up -d
   ```

4. **訪問服務**
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Frontend: http://localhost:3000 (開發中)

5. **查看日誌**
   ```bash
   make logs
   ```

### 運行 Worker Agent

```bash
cd worker-agent

# 配置 Worker
cp config/agent.yaml.example config/agent.yaml
# 編輯 config/agent.yaml 填入配置

# 啟動 Worker
python src/main.py --config config/agent.yaml
```

## 開發指南

### 運行測試

```bash
# 後端測試
cd backend
pytest

# 帶覆蓋率報告
pytest --cov=src --cov-report=html
```

### 代碼風格

項目使用 pre-commit hooks 自動格式化代碼：

```bash
# 安裝 pre-commit
pip install pre-commit
pre-commit install

# 手動運行
pre-commit run --all-files
```

### 數據庫遷移

```bash
cd backend

# 創建新遷移
alembic revision --autogenerate -m "描述"

# 執行遷移
alembic upgrade head

# 回滾
alembic downgrade -1
```

## 文檔

- [架構設計](docs/architecture.md) - 完整的技術架構文檔
- [產品需求文檔](docs/PRD.md) - PRD和功能需求
- [Epic拆分](docs/epics.md) - 9個Epic，58個User Stories
- [UX設計規範](docs/ux-design-specification.md) - UI/UX設計指南
- [Sprint 1計劃](docs/sprint-1-plan.md) - 第一個Sprint的詳細計劃

## 性能目標

- ⚡ 任務提交響應時間: < 2s
- 🔄 WebSocket延遲: < 500ms
- 📊 儀表板加載時間: < 3s
- 👥 並發用戶: 100+
- 🖥️ Worker容量: 10+ 機器
- ⚙️ 並行任務: 20+

## 路線圖

### ✅ Phase 0-2: 已完成
- [x] Brainstorming & Product Brief
- [x] PRD & Epic Breakdown
- [x] UX Design Specification
- [x] Architecture Design & Validation
- [x] Sprint Planning

### 🚀 Phase 3: 實作中 (當前)
- [ ] Sprint 1: Foundation & Infrastructure (2 weeks)
- [ ] Sprint 2: Worker Management (2-3 weeks)
- [ ] Sprint 3: Task Coordination (2-3 weeks)
- [ ] Sprint 4: Flutter UI (3 weeks)
- [ ] Sprint 5: AI Integration (3-4 weeks)
- [ ] Sprint 6-8: Quality & Collaboration (6-7 weeks)
- [ ] Sprint 9: Testing & Launch (2-3 weeks)

## 貢獻指南

請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)（待創建）

## 授權

[待定]

## 聯繫方式

- **項目作者**: sir
- **創建日期**: 2025-11-11
- **當前狀態**: Sprint 1 開發中

---

**Built with ❤️ using BMAD-METHOD**
