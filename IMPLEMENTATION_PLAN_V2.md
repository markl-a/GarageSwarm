# GarageSwarm 2.0 - 全新實施計劃

**制定日期：2026-01-22**
**版本：2.0 - 重構版**

---

## 執行摘要

基於對現有代碼庫的深入分析、建議.md 中的框架研究、以及 2026 年多代理編排最佳實踐的調研，本計劃提出一個**根本性的架構重構方案**，將 GarageSwarm 從「簡單的任務分發系統」升級為「企業級智能代理編排平台」。

### 核心洞察

| 現有問題 | 建議方案 | 參考來源 |
|----------|----------|----------|
| 缺乏真正的多代理協作 | 引入 MCP + A2A 協議 | Anthropic MCP, Google A2A |
| 工作流引擎只是骨架 | 採用 LangGraph 風格的狀態機 | LangGraph, Claude-Flow |
| 沒有學習能力 | 加入神經記憶系統 | Claude-Flow v3 |
| 前端幾乎為零 | 優先構建可視化編排器 | n8n, Flowise |
| 單一 Supervisor 瓶頸 | Hub-Spoke + 去中心化混合架構 | AWS CAO, OpenHands |

---

## 第一部分：架構革新

### 1.1 從「任務隊列」到「智能蜂群」

**現有架構問題：**
```
用戶 → Backend → Redis Queue → Worker 拉取 → 執行 → 返回結果
                    ↑
                單點瓶頸，無協作能力
```

**新架構：混合式蜂群編排**
```
┌─────────────────────────────────────────────────────────────────┐
│                    GarageSwarm Orchestrator                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Planner    │  │  Router     │  │  Evaluator  │             │
│  │  (任務分解)  │→│  (智能路由)  │→│  (品質評估)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│                         MCP Bus (工具匯流排)                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Claude  │  │ Gemini  │  │ Ollama  │  │ Codex   │  ...      │
│  │  Code   │  │   CLI   │  │ (本地)   │  │   CLI   │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       │            │            │            │                  │
│       └────────────┴─────┬──────┴────────────┘                  │
│                          ↓                                       │
│               Agent-to-Agent (A2A) 協議層                        │
│           (代理間可直接通訊、協商、共享發現)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 三層編排架構

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Strategic (戰略層)                                  │
│ - 需求理解與任務分解                                          │
│ - 長期記憶與模式學習                                          │
│ - 人類意圖推斷                                               │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Tactical (戰術層)                                   │
│ - 工作流 DAG 執行                                            │
│ - 條件分支與並行協調                                          │
│ - 錯誤恢復與重試策略                                          │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Operational (操作層)                                │
│ - 具體工具調用 (CLI/API)                                      │
│ - 沙盒執行環境                                               │
│ - 結果收集與格式化                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 第二部分：核心模組重構

### 2.1 MCP 整合層 (新增)

**為什麼需要 MCP？**
- MCP 已成為 2026 年 AI 工具整合的事實標準
- OpenAI、Anthropic、Block 等都已支援
- 超過 1,000+ 社區 MCP 伺服器可用

**實施計劃：**

```python
# backend/src/mcp/
├── __init__.py
├── bus.py              # MCP 匯流排管理器
├── registry.py         # 工具註冊表
├── servers/
│   ├── filesystem.py   # 文件系統 MCP
│   ├── database.py     # 數據庫 MCP
│   ├── git.py          # Git 操作 MCP
│   ├── browser.py      # 瀏覽器控制 MCP
│   └── custom.py       # 自定義 MCP 模板
└── transports/
    ├── stdio.py        # 本地進程通訊
    └── sse.py          # HTTP SSE 遠程通訊
```

**核心代碼結構：**

```python
# mcp/bus.py
class MCPBus:
    """MCP 工具匯流排 - 統一管理所有工具連接"""

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.tool_cache: Dict[str, ToolDefinition] = {}

    async def register_server(self, name: str, config: MCPServerConfig):
        """動態註冊 MCP 伺服器"""
        server = await self._create_server(config)
        self.servers[name] = server
        # 自動發現並緩存工具定義
        tools = await server.list_tools()
        for tool in tools:
            self.tool_cache[f"{name}.{tool.name}"] = tool

    async def invoke_tool(self, tool_path: str, arguments: dict) -> ToolResult:
        """統一工具調用接口"""
        server_name, tool_name = tool_path.split(".", 1)
        server = self.servers[server_name]
        return await server.call_tool(tool_name, arguments)

    async def get_available_tools(self) -> List[ToolDefinition]:
        """返回所有可用工具（供 LLM 選擇）"""
        return list(self.tool_cache.values())
```

### 2.2 智能路由器 (新增)

**現有問題：** 任務直接分配給指定工具，沒有智能選擇

**新設計：多維度路由決策**

```python
# backend/src/services/router.py
class IntelligentRouter:
    """智能任務路由器"""

    def __init__(self, mcp_bus: MCPBus, memory: MemorySystem):
        self.mcp_bus = mcp_bus
        self.memory = memory
        self.cost_tracker = CostTracker()

    async def route_task(self, task: Task) -> RoutingDecision:
        """基於多維度評分選擇最佳執行路徑"""

        candidates = await self._get_capable_workers(task)

        scores = []
        for worker in candidates:
            score = await self._calculate_score(worker, task, factors={
                "capability_match": 0.3,    # 工具能力匹配度
                "historical_success": 0.25,  # 歷史成功率
                "current_load": 0.2,         # 當前負載
                "cost_efficiency": 0.15,     # 成本效率
                "latency_estimate": 0.1,     # 預估延遲
            })
            scores.append((worker, score))

        # 選擇最高分，但加入一定隨機性避免單點過載
        return self._select_with_exploration(scores)

    async def _calculate_score(self, worker, task, factors) -> float:
        """多因素評分計算"""
        score = 0.0

        # 1. 能力匹配：檢查工具是否支援任務類型
        if task.tool_preference in worker.tools:
            score += factors["capability_match"]

        # 2. 歷史成功率：從記憶系統查詢
        history = await self.memory.get_worker_performance(worker.id)
        score += history.success_rate * factors["historical_success"]

        # 3. 當前負載：偏好空閒 worker
        load_score = 1.0 - (worker.active_tasks / worker.max_concurrent)
        score += load_score * factors["current_load"]

        # 4. 成本效率：本地模型 vs API 調用
        cost = self.cost_tracker.estimate_cost(worker, task)
        cost_score = 1.0 / (1.0 + cost)  # 成本越低分數越高
        score += cost_score * factors["cost_efficiency"]

        return score
```

### 2.3 工作流引擎重構

**現有問題：**
- `workflow_engine.py` 只有空殼
- 沒有真正的 DAG 執行
- 不支援條件分支、並行、循環

**新設計：LangGraph 風格狀態機**

```python
# backend/src/workflows/
├── __init__.py
├── engine.py           # 核心執行引擎
├── graph.py            # DAG 圖結構
├── nodes/
│   ├── base.py         # 節點基類
│   ├── task.py         # 任務節點
│   ├── condition.py    # 條件分支節點
│   ├── parallel.py     # 並行節點
│   ├── human.py        # 人工審核節點
│   ├── router.py       # 動態路由節點
│   └── subflow.py      # 子工作流節點
├── state.py            # 工作流狀態管理
├── checkpoints.py      # 檢查點與恢復
└── templates/          # 預設工作流模板
    ├── code_review.yaml
    ├── feature_development.yaml
    └── data_pipeline.yaml
```

**核心執行引擎：**

```python
# workflows/engine.py
class WorkflowEngine:
    """LangGraph 風格的工作流執行引擎"""

    def __init__(self, mcp_bus: MCPBus, checkpoint_store: CheckpointStore):
        self.mcp_bus = mcp_bus
        self.checkpoints = checkpoint_store

    async def execute(self, workflow: Workflow, initial_state: dict) -> WorkflowResult:
        """執行工作流"""

        state = WorkflowState(initial_state)
        graph = self._build_graph(workflow)

        # 檢查是否有中斷的檢查點可恢復
        checkpoint = await self.checkpoints.get_latest(workflow.id)
        if checkpoint:
            state = checkpoint.state
            current_node = checkpoint.current_node
        else:
            current_node = graph.entry_node

        while current_node:
            # 保存檢查點（用於崩潰恢復）
            await self.checkpoints.save(workflow.id, state, current_node)

            # 執行當前節點
            node = graph.nodes[current_node]

            if isinstance(node, ParallelNode):
                # 並行執行所有分支
                results = await asyncio.gather(*[
                    self._execute_branch(branch, state)
                    for branch in node.branches
                ])
                state.merge_parallel_results(results)

            elif isinstance(node, ConditionNode):
                # 評估條件，選擇分支
                branch = await node.evaluate(state)
                current_node = branch
                continue

            elif isinstance(node, HumanReviewNode):
                # 暫停等待人工審核
                await self._request_human_review(workflow.id, state)
                return WorkflowResult(status="waiting_review", state=state)

            else:
                # 普通任務節點
                result = await self._execute_node(node, state)
                state.update(node.output_key, result)

            # 獲取下一個節點
            current_node = graph.get_next(current_node, state)

        return WorkflowResult(status="completed", state=state)

    async def _execute_node(self, node: TaskNode, state: WorkflowState):
        """執行單個任務節點"""
        # 從狀態中解析輸入
        inputs = node.resolve_inputs(state)

        # 通過 MCP Bus 調用工具
        result = await self.mcp_bus.invoke_tool(
            node.tool_path,
            inputs
        )

        # 錯誤處理與重試
        if result.error and node.retry_count < node.max_retries:
            node.retry_count += 1
            await asyncio.sleep(node.retry_delay)
            return await self._execute_node(node, state)

        return result
```

### 2.4 神經記憶系統 (新增)

**靈感來源：Claude-Flow v3 的自學習能力**

```python
# backend/src/memory/
├── __init__.py
├── system.py           # 記憶系統主類
├── stores/
│   ├── vector.py       # 向量記憶 (語義搜索)
│   ├── graph.py        # 圖記憶 (關係網絡)
│   └── episodic.py     # 情節記憶 (任務歷史)
├── learning/
│   ├── pattern.py      # 模式識別
│   ├── feedback.py     # 反饋學習
│   └── consolidation.py # 記憶整合
└── retrieval/
    ├── similarity.py   # 相似度檢索
    └── contextual.py   # 上下文檢索
```

**記憶系統設計：**

```python
# memory/system.py
class MemorySystem:
    """三層記憶架構"""

    def __init__(self, vector_db: VectorStore, graph_db: GraphStore, redis: Redis):
        # 短期記憶：當前會話上下文 (Redis)
        self.short_term = ShortTermMemory(redis)

        # 長期記憶：向量化知識庫 (ChromaDB/Qdrant)
        self.long_term = LongTermMemory(vector_db)

        # 關係記憶：實體關係圖 (Neo4j/NetworkX)
        self.relational = RelationalMemory(graph_db)

    async def remember(self, event: MemoryEvent):
        """記錄新事件"""
        # 1. 立即存入短期記憶
        await self.short_term.store(event)

        # 2. 提取關鍵實體和關係
        entities = self._extract_entities(event)
        await self.relational.update(entities)

        # 3. 異步整合到長期記憶
        asyncio.create_task(self._consolidate(event))

    async def recall(self, query: str, context: dict) -> List[MemoryItem]:
        """智能回憶：結合語義搜索和關係推理"""

        # 並行查詢三種記憶
        short_results, long_results, graph_results = await asyncio.gather(
            self.short_term.search(query, limit=5),
            self.long_term.semantic_search(query, limit=10),
            self.relational.traverse(context.get("entities", []))
        )

        # 融合排序
        return self._fuse_and_rank(short_results, long_results, graph_results)

    async def learn_from_feedback(self, task_id: str, feedback: Feedback):
        """從反饋中學習"""
        # 獲取任務執行歷史
        history = await self.short_term.get_task_history(task_id)

        if feedback.success:
            # 成功模式強化
            pattern = self._extract_success_pattern(history)
            await self.long_term.reinforce(pattern)
        else:
            # 失敗模式標記
            anti_pattern = self._extract_failure_pattern(history)
            await self.long_term.mark_anti_pattern(anti_pattern)
```

### 2.5 人機協作界面 (Human-in-the-Loop)

**現有問題：** 完全沒有人工介入機制

**新設計：可配置的審核點**

```python
# backend/src/collaboration/
├── __init__.py
├── review.py           # 審核請求管理
├── approval.py         # 審批流程
├── notification.py     # 通知系統
└── intervention.py     # 人工介入處理

# collaboration/review.py
class HumanReviewManager:
    """人工審核管理器"""

    def __init__(self, notification_service: NotificationService):
        self.notifications = notification_service
        self.pending_reviews: Dict[str, ReviewRequest] = {}

    async def request_review(
        self,
        workflow_id: str,
        checkpoint: dict,
        reason: ReviewReason,
        urgency: Urgency = Urgency.NORMAL
    ) -> ReviewRequest:
        """發起人工審核請求"""

        request = ReviewRequest(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            checkpoint=checkpoint,
            reason=reason,
            urgency=urgency,
            created_at=datetime.utcnow(),
            expires_at=self._calculate_expiry(urgency)
        )

        self.pending_reviews[request.id] = request

        # 發送通知
        await self.notifications.send(
            channel=self._select_channel(urgency),
            message=self._format_review_request(request)
        )

        return request

    async def submit_decision(
        self,
        request_id: str,
        decision: ReviewDecision,
        reviewer_id: str,
        comments: str = None
    ) -> ReviewResult:
        """提交審核決定"""

        request = self.pending_reviews.pop(request_id)

        result = ReviewResult(
            request=request,
            decision=decision,
            reviewer_id=reviewer_id,
            comments=comments,
            decided_at=datetime.utcnow()
        )

        # 記錄到審計日誌
        await self._audit_log(result)

        # 恢復工作流執行
        if decision == ReviewDecision.APPROVE:
            await self._resume_workflow(request.workflow_id)
        elif decision == ReviewDecision.REJECT:
            await self._cancel_workflow(request.workflow_id, comments)
        elif decision == ReviewDecision.MODIFY:
            await self._modify_and_resume(request.workflow_id, comments)

        return result
```

---

## 第三部分：重構 Phase 計劃

### Phase 0：基礎設施升級 (1-2 週)

**目標：** 修復現有缺陷，為重構做準備

| 任務 | 優先級 | 預估複雜度 |
|------|--------|-----------|
| 完成 WebSocket 實現 | 🔴 高 | 中 |
| 實現任務結果回報機制 | 🔴 高 | 中 |
| 修復 Worker 認證流程 | 🔴 高 | 低 |
| 添加基本錯誤重試邏輯 | 🟡 中 | 低 |
| 完善 API 文檔 (OpenAPI) | 🟢 低 | 低 |

**具體任務：**

```
□ backend/src/api/v1/websocket.py - 實現真正的 WebSocket 連接
□ backend/src/api/v1/workers.py - 添加 /workers/{id}/report-result 端點
□ backend/src/auth/worker_auth.py - 完成 X-Worker-API-Key 驗證
□ worker-agent/src/agent/result_reporter.py - 結果回報客戶端
□ 端到端測試：任務創建 → 分配 → 執行 → 結果回報 → 狀態更新
```

### Phase 1：MCP 整合層 (2-3 週)

**目標：** 建立統一的工具調用基礎設施

| 任務 | 優先級 | 依賴 |
|------|--------|------|
| 實現 MCP Bus 核心 | 🔴 高 | Phase 0 |
| 遷移現有工具到 MCP | 🔴 高 | MCP Bus |
| 實現 STDIO 傳輸層 | 🔴 高 | MCP Bus |
| 添加 SSE 遠程傳輸 | 🟡 中 | STDIO |
| 工具自動發現機制 | 🟡 中 | MCP Bus |

**架構圖：**

```
┌─────────────────────────────────────────────────┐
│                  MCP Bus                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│  │ Tool      │  │ Transport │  │ Schema    │   │
│  │ Registry  │  │ Manager   │  │ Validator │   │
│  └───────────┘  └───────────┘  └───────────┘   │
└─────────────────────────────────────────────────┘
         ↑              ↑              ↑
┌────────┴──────┐┌─────┴──────┐┌─────┴──────┐
│ claude_code   ││ gemini_cli ││ ollama     │
│ MCP Server    ││ MCP Server ││ MCP Server │
└───────────────┘└────────────┘└────────────┘
```

### Phase 2：智能路由與記憶系統 (3-4 週)

**目標：** 加入智能決策和學習能力

| 任務 | 優先級 | 依賴 |
|------|--------|------|
| 實現智能路由器 | 🔴 高 | Phase 1 |
| 短期記憶 (Redis) | 🔴 高 | - |
| 長期記憶 (向量庫) | 🔴 高 | - |
| 關係記憶 (圖數據庫) | 🟡 中 | - |
| 反饋學習循環 | 🟡 中 | 記憶系統 |
| 成本追蹤系統 | 🟢 低 | 智能路由 |

**技術選型：**

| 組件 | 推薦方案 | 替代方案 |
|------|----------|----------|
| 向量數據庫 | ChromaDB (輕量) | Qdrant, Weaviate |
| 圖數據庫 | NetworkX (內存) | Neo4j (生產環境) |
| 嵌入模型 | text-embedding-3-small | Ollama embeddings |

### Phase 3：工作流引擎重構 (4-5 週)

**目標：** 實現生產級工作流編排

| 任務 | 優先級 | 依賴 |
|------|--------|------|
| 核心 DAG 執行器 | 🔴 高 | Phase 2 |
| 條件分支節點 | 🔴 高 | DAG 執行器 |
| 並行執行支援 | 🔴 高 | DAG 執行器 |
| 人工審核節點 | 🔴 高 | Phase 2 |
| 檢查點與恢復 | 🔴 高 | DAG 執行器 |
| 子工作流支援 | 🟡 中 | DAG 執行器 |
| 工作流模板系統 | 🟡 中 | 所有節點類型 |
| 可視化編輯器 API | 🟢 低 | 模板系統 |

**工作流節點類型：**

```yaml
nodes:
  - type: task           # 基本任務執行
  - type: condition      # 條件分支 (if/else)
  - type: parallel       # 並行執行多個分支
  - type: join           # 等待所有並行分支完成
  - type: human_review   # 人工審核關卡
  - type: router         # 動態路由 (基於 LLM 決策)
  - type: loop           # 循環執行直到條件滿足
  - type: subflow        # 嵌套子工作流
  - type: wait           # 定時等待或事件等待
```

### Phase 4：前端與可視化 (4-5 週)

**目標：** 構建現代化管理界面

**技術決策變更：**

原計劃使用 Flutter Web，但考慮到：
1. Flutter Web 生態相對較新
2. 工作流可視化編輯器需要豐富的 JS 生態支援
3. 團隊可能更熟悉 React/Vue

**新建議：React + React Flow**

```
frontend-v2/
├── src/
│   ├── components/
│   │   ├── workflow/
│   │   │   ├── WorkflowCanvas.tsx    # 基於 React Flow
│   │   │   ├── NodePalette.tsx       # 節點工具箱
│   │   │   ├── PropertyPanel.tsx     # 屬性面板
│   │   │   └── ExecutionViewer.tsx   # 執行可視化
│   │   ├── dashboard/
│   │   ├── workers/
│   │   └── tasks/
│   ├── stores/              # Zustand 狀態管理
│   ├── services/            # API 客戶端
│   └── hooks/               # WebSocket 等
└── package.json
```

**核心功能：**

| 功能 | 優先級 | 描述 |
|------|--------|------|
| 儀表板 | 🔴 高 | 系統概覽、即時指標 |
| 工作流編輯器 | 🔴 高 | 拖拽式 DAG 構建 |
| 任務管理 | 🔴 高 | 任務列表、詳情、日誌 |
| Worker 監控 | 🔴 高 | 狀態、負載、工具 |
| 執行回放 | 🟡 中 | 工作流執行可視化 |
| 審核隊列 | 🟡 中 | 人工審核界面 |
| 模板市場 | 🟢 低 | 工作流模板分享 |

### Phase 5：多模態與外部整合 (4-6 週)

**目標：** 擴展到圖片、音頻、視頻處理

| 任務 | 優先級 | 依賴 |
|------|--------|------|
| 文件存儲系統 (MinIO/S3) | 🔴 高 | - |
| ComfyUI MCP Server | 🔴 高 | 文件存儲 |
| 多模態輸出處理 | 🔴 高 | 文件存儲 |
| Suno AI 整合 | 🟡 中 | 文件存儲 |
| ElevenLabs TTS 整合 | 🟡 中 | 文件存儲 |
| 外部 Webhook 系統 | 🟡 中 | - |
| 排程系統 (APScheduler) | 🟡 中 | - |

**多模態架構：**

```
┌─────────────────────────────────────────────────┐
│              Multimodal Pipeline                 │
├─────────────────────────────────────────────────┤
│  Input      │  Processing      │  Output        │
│  ─────      │  ──────────      │  ──────        │
│  • Text     │  • Claude Code   │  • Text        │
│  • Image    │  • ComfyUI       │  • Image       │
│  • Audio    │  • Suno AI       │  • Audio       │
│  • Video    │  • Kling         │  • Video       │
│  • Code     │  • ElevenLabs    │  • Code        │
├─────────────────────────────────────────────────┤
│              Unified File Storage (MinIO)        │
└─────────────────────────────────────────────────┘
```

### Phase 6：企業級功能 (持續)

| 任務 | 優先級 | 描述 |
|------|--------|------|
| 多租戶支援 | 🔴 高 | 組織/工作空間隔離 |
| RBAC 權限系統 | 🔴 高 | 細粒度權限控制 |
| 審計日誌 | 🔴 高 | 完整操作追蹤 |
| SSO 整合 | 🟡 中 | SAML/OIDC |
| API 限流 | 🟡 中 | Rate limiting |
| 加密存儲 | 🟡 中 | 敏感數據加密 |
| 災難恢復 | 🟢 低 | 備份與恢復 |

---

## 第四部分：獨特競爭優勢

### 4.1 差異化定位

| 競品 | 定位 | GarageSwarm 優勢 |
|------|------|------------------|
| CLI Agent Orchestrator | AWS 綁定 | **無雲依賴**，純本地運行 |
| Claude-Flow | Claude 專用 | **多模型通用**，支援任意 CLI 工具 |
| OpenHands | 開發導向 | **通用編排**，不限於開發任務 |
| LangGraph | 代碼優先 | **可視化編輯**，降低使用門檻 |
| n8n | 工作流自動化 | **AI 原生**，深度整合 AI 工具 |

### 4.2 獨特功能矩陣

```
┌─────────────────────────────────────────────────────────────┐
│                    GarageSwarm 獨特價值                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🏠 消費級硬體優先                                           │
│     └─ 專為普通電腦優化，不需要雲服務或高端 GPU              │
│                                                              │
│  🔌 MCP 原生                                                 │
│     └─ 完全基於 MCP 標準，自動相容 1000+ 社區工具            │
│                                                              │
│  🧠 自適應學習                                               │
│     └─ 從每次執行中學習，持續優化路由和執行策略              │
│                                                              │
│  🔀 混合編排                                                 │
│     └─ Hub-Spoke + P2P 混合，兼顧控制力和擴展性              │
│                                                              │
│  👁️ 執行透明                                                 │
│     └─ 完整的執行回放，每一步都可追溯                        │
│                                                              │
│  🛡️ 安全欄杆                                                 │
│     └─ 內建沙盒、命令白名單、人工審核關卡                    │
│                                                              │
│  🎨 多模態原生                                               │
│     └─ 深度整合 ComfyUI/Suno/ElevenLabs 等創作工具           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 核心使用場景

**場景 1：自動化軟體開發**
```yaml
workflow: feature_development
steps:
  - agent: gemini
    task: "分析需求並生成技術方案"
  - human_review: "審核技術方案"
  - parallel:
      - agent: claude_code
        task: "實現後端 API"
      - agent: claude_code
        task: "實現前端組件"
  - agent: ollama
    task: "運行測試套件"
  - condition:
      if: "tests_passed"
      then: auto_merge
      else: notify_developer
```

**場景 2：內容創作流水線**
```yaml
workflow: content_pipeline
steps:
  - agent: gemini
    task: "根據主題生成文章大綱"
  - agent: claude_code
    task: "擴展大綱為完整文章"
  - parallel:
      - agent: comfyui
        task: "生成配圖"
      - agent: elevenlabs
        task: "生成語音版本"
  - agent: ollama
    task: "SEO 優化檢查"
  - human_review: "最終審核"
```

**場景 3：數據分析自動化**
```yaml
workflow: data_analysis
steps:
  - agent: claude_code
    task: "連接數據源並提取數據"
  - agent: gemini
    task: "執行數據清洗和轉換"
  - agent: claude_code
    task: "生成可視化圖表"
  - agent: gemini
    task: "撰寫分析報告"
  - agent: comfyui
    task: "美化報告圖表"
  - output: "report.pdf"
```

---

## 第五部分：技術棧更新

### 5.1 完整技術棧

| 層級 | 組件 | 技術選型 | 備註 |
|------|------|----------|------|
| **後端** | Web 框架 | FastAPI | 保留 |
| | 數據庫 | PostgreSQL + SQLAlchemy 2.0 | 保留 |
| | 緩存/隊列 | Redis | 保留 |
| | 向量數據庫 | ChromaDB | 新增 |
| | 圖數據庫 | NetworkX → Neo4j | 新增 |
| | 任務隊列 | Celery + Redis | 新增 |
| | 排程 | APScheduler | 保留 |
| **Worker** | 本地 Agent | Python + asyncio | 保留 |
| | 桌面 Agent | Electron | 保留 |
| | 工具協議 | MCP (Model Context Protocol) | **核心新增** |
| | 沙盒 | Docker | 新增 |
| **前端** | 框架 | React 18 + TypeScript | **變更** |
| | 狀態管理 | Zustand | 新增 |
| | 工作流編輯器 | React Flow | 新增 |
| | UI 組件 | Shadcn/ui | 新增 |
| **AI 工具** | CLI 工具 | Claude Code, Gemini CLI, Codex | 保留 |
| | 本地 LLM | Ollama | 保留 |
| | 圖像生成 | ComfyUI | 新增 |
| | 音頻生成 | Suno AI, ElevenLabs | 新增 |
| **基礎設施** | 容器 | Docker + Docker Compose | 保留 |
| | 文件存儲 | MinIO (S3 相容) | 新增 |
| | 監控 | Prometheus + Grafana | 新增 |
| | 日誌 | Loki | 新增 |

### 5.2 新增依賴

**Backend (requirements.txt 新增):**
```
# MCP 支援
mcp>=0.9.0
mcp-server-stdio>=0.2.0

# 向量數據庫
chromadb>=0.4.0

# 圖處理
networkx>=3.0

# 任務隊列
celery[redis]>=5.3.0

# 嵌入模型
sentence-transformers>=2.2.0
# 或使用 OpenAI embeddings

# 監控
prometheus-client>=0.19.0

# 測試
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
```

**Frontend (package.json 新增):**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@xyflow/react": "^12.0.0",
    "zustand": "^4.4.0",
    "@tanstack/react-query": "^5.0.0",
    "socket.io-client": "^4.7.0",
    "@radix-ui/themes": "^3.0.0",
    "tailwindcss": "^3.4.0"
  }
}
```

---

## 第六部分：風險與緩解

### 6.1 技術風險

| 風險 | 影響 | 緩解策略 |
|------|------|----------|
| MCP 生態尚在發展 | 中 | 設計抽象層，保持靈活性 |
| 前端技術棧變更 | 高 | 可選保留 Flutter，React 作為替代方案 |
| 向量數據庫性能 | 中 | ChromaDB 夠用，必要時升級 Qdrant |
| 工作流複雜度 | 高 | 從簡單線性開始，逐步加入分支/並行 |

### 6.2 資源風險

| 風險 | 影響 | 緩解策略 |
|------|------|----------|
| 開發時間超支 | 高 | 每 Phase 設定硬性截止日期 |
| 單人開發瓶頸 | 高 | 優先自動化測試，減少回歸成本 |
| 學習曲線 | 中 | 選擇熟悉的技術，避免過度創新 |

### 6.3 安全風險

| 風險 | 影響 | 緩解策略 |
|------|------|----------|
| MCP 提示注入 | 高 | 輸入驗證 + 輸出過濾 |
| 工具命令注入 | 高 | 命令白名單 + 沙盒執行 |
| 敏感數據洩露 | 高 | 密鑰隔離 + 審計日誌 |
| 網路暴露 | 高 | 默認禁止外網，按需開放 |

---

## 第七部分：成功指標

### 7.1 技術指標

| 指標 | 目標 | 測量方式 |
|------|------|----------|
| 任務成功率 | >95% | 完成任務 / 總任務 |
| 平均執行時間 | <60s (簡單任務) | 任務計時 |
| 系統可用性 | >99% | Prometheus 監控 |
| API 響應時間 | <200ms (P95) | APM 追蹤 |

### 7.2 業務指標

| 指標 | 目標 | 測量方式 |
|------|------|----------|
| 支援工具數量 | 10+ 內建工具 | MCP 伺服器數量 |
| 工作流模板 | 5+ 預設模板 | 模板市場數量 |
| 並發 Worker | 10+ | 壓力測試 |
| 日活躍用戶 | N/A (自用) | - |

---

## 第八部分：立即行動項目

### 本週開始 (Week 1)

1. **修復 WebSocket 連接** - backend/src/api/v1/websocket.py
2. **實現結果回報端點** - POST /workers/{id}/report-result
3. **添加 Worker API Key 驗證** - X-Worker-API-Key header

### 下週 (Week 2)

4. **創建 MCP Bus 基礎結構** - backend/src/mcp/
5. **遷移 Ollama 到 MCP Server** - 作為 POC
6. **端到端測試自動化** - pytest + GitHub Actions

### 第三週 (Week 3)

7. **實現短期記憶系統** - Redis-based
8. **添加基本智能路由** - 負載 + 能力匹配
9. **開始工作流引擎重構** - 核心 DAG 執行器

---

## 附錄：參考資源

### 框架與協議

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [LangGraph Documentation](https://docs.langchain.com/oss/javascript/langgraph/overview)
- [AWS CLI Agent Orchestrator](https://github.com/awslabs/cli-agent-orchestrator)
- [Claude-Flow](https://github.com/ruvnet/claude-flow)
- [OpenHands](https://github.com/OpenHands/OpenHands)

### 最佳實踐

- [AI Agent Orchestration Patterns - Microsoft](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Multi-Agent AI Orchestration - Kore.ai](https://www.kore.ai/blog/what-is-multi-agent-orchestration)
- [MCP Best Practices](https://modelcontextprotocol.info/docs/best-practices/)

### 工具比較

- [CrewAI vs LangGraph vs AutoGen - DataCamp](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [Top AI Agent Orchestration Frameworks 2025](https://www.kubiya.ai/blog/ai-agent-orchestration-frameworks)
- [8 Best Multi-Agent AI Frameworks for 2026](https://www.multimodal.dev/post/best-multi-agent-ai-frameworks)

---

**文檔版本：** 2.0
**制定者：** Claude Code + Research
**下次審閱：** Phase 0 完成後
