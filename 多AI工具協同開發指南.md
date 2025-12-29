# BMAD-METHOD 多 AI 工具協同開發指南

## 概述

本指南說明如何同時使用多種 AI 工具與 BMAD-METHOD 進行協同開發，以 Claude Code 為主要開發環境。

**目標工具整合**:
- **Claude Code** (主要環境)
- **Claude Subagent** (Claude Code 內建)
- **Codex** (GitHub Copilot)
- **Gemini CLI**
- **Claude Code on the Web**
- **Local LLM**

---

## 架構設計

### 核心原則

1. **Claude Code 為中央協調者**
   - 所有 BMAD 代理在 Claude Code 中執行
   - 工作流程狀態在 Claude Code 中管理
   - 檔案系統由 Claude Code 控制

2. **工具分工明確**
   - 避免多個工具同時操作同一檔案
   - 明確定義各工具的職責範圍
   - 使用 Git 作為協作媒介

3. **狀態同步機制**
   - 定期 Git commit 同步狀態
   - 使用 BMAD 工作流程狀態檔案追蹤進度
   - 文件化工具使用決策

---

## 工具分工策略

### 建議分工

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code (中央協調)                     │
│  - BMAD 所有代理 (Analyst, PM, Architect, SM, DEV, TEA)     │
│  - 工作流程執行 (*workflow-init, *sprint-planning 等)        │
│  - 檔案系統管理                                              │
│  - Git 版本控制                                              │
│  - Story Context 組裝                                        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐  ┌─────────▼────────┐  ┌────────▼────────┐
│ Claude Subagent│  │ Codex (Copilot)  │  │   Gemini CLI    │
│                │  │                  │  │                 │
│ - 複雜搜尋任務  │  │ - 程式碼自動完成  │  │ - 平行驗證/審查 │
│ - 程式碼庫探索  │  │ - Snippet 生成   │  │ - 多角度分析    │
│ - 背景研究     │  │ - 重構建議       │  │ - 備選方案評估  │
└────────────────┘  └──────────────────┘  └─────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐  ┌─────────▼────────┐
│ Claude Web     │  │   Local LLM      │
│                │  │                  │
│ - 獨立研究任務  │  │ - 敏感資料處理   │
│ - 文件生成     │  │ - 離線開發       │
│ - 備份思路     │  │ - 快速原型      │
└────────────────┘  └──────────────────┘
```

### 詳細職責劃分

#### 1. Claude Code (主控)

**BMAD 工作流程**:
- ✅ 執行所有 BMAD 代理
- ✅ 管理 Sprint 狀態
- ✅ Story 生命週期管理
- ✅ 程式碼審查 (`*code-review`)
- ✅ 工作流程狀態追蹤

**檔案操作**:
- ✅ 所有 BMAD 文件生成（PRD, Architecture, Stories）
- ✅ Git 提交和推送
- ✅ 專案結構管理

#### 2. Claude Subagent (Claude Code 內建)

**使用場景**:
- 🔍 複雜的程式碼庫探索 (Explore agent)
- 🔍 關鍵字搜尋任務
- 🔍 多檔案模式搜尋
- 🔍 背景研究（當主 session 忙碌時）

**BMAD 整合**:
```bash
# 在 Claude Code 中
載入 Analyst
*document-project  # 使用 Subagent 探索程式碼庫

載入 Architect
*create-architecture  # 需要深度程式碼分析時，Subagent 平行運作
```

**範例**:
```
Claude Code 主 Session:
- 載入 SM，執行 *create-story

平行使用 Subagent (背景):
- 搜尋相關現有 API 端點
- 分析類似功能的實作方式
- 回報結果給主 Session
```

#### 3. Codex / GitHub Copilot

**使用場景**:
- ⚡ 即時程式碼補全
- ⚡ 重複性程式碼生成
- ⚡ 函數簽名建議
- ⚡ 測試案例生成

**BMAD 整合**:
```bash
# Phase 4: Implementation
載入 DEV
*develop-story

# 此時 Copilot 自動啟用
# DEV 代理決策主要邏輯
# Copilot 協助快速編寫重複程式碼
```

**協作模式**:
1. DEV 代理讀取 Story Context
2. DEV 決定實作策略
3. 開始編寫程式碼時，Copilot 提供自動補全
4. DEV 審核 Copilot 建議，決定是否採用
5. DEV 執行測試驗證

**注意事項**:
- ⚠️ Copilot 建議需經 DEV 代理驗證
- ⚠️ 確保符合 Story 的 Acceptance Criteria
- ⚠️ 避免盲目接受所有建議

#### 4. Gemini CLI

**使用場景**:
- 🔄 平行驗證（第二意見）
- 🔄 架構方案評估
- 🔄 程式碼審查備援
- 🔄 測試策略驗證

**BMAD 整合**:
```bash
# 在 Claude Code 完成 Story 後
# 切換到終端機

# 使用 Gemini CLI 進行獨立審查
gemini-cli "審查 Story-001 的實作，檢查：
1. 是否符合所有 AC
2. 是否有安全漏洞
3. 程式碼品質評分
參考檔案：docs/stories/story-001.md 和 src/auth/register.js"

# 將 Gemini 的反饋提供給 Claude Code DEV 代理
```

**協作流程**:
```
1. Claude Code (DEV): 完成 Story 實作
2. Claude Code (DEV): 執行 *code-review
3. Gemini CLI: 獨立審查同一 Story (平行驗證)
4. 比對兩者結果
5. 若有衝突意見 → Party Mode 討論
```

**範例指令**:
```bash
# 架構決策驗證
gemini-cli "評估 docs/architecture.md 中的微服務架構決策，
特別是服務邊界劃分的合理性"

# 測試覆蓋率建議
gemini-cli "分析 tests/ 目錄，建議額外需要的測試案例，
參考 docs/stories/ 中的所有 AC"
```

#### 5. Claude Code on the Web

**使用場景**:
- 📄 獨立研究和文件生成
- 📄 初步方案探索
- 📄 複雜問題的備選思路
- 📄 長文本處理

**BMAD 整合**:
```bash
# 場景 1: Phase 1 Analysis
# 在 Web 版進行初步研究
- 市場調查
- 競品分析
- 技術選型研究

# 將結果整理成 Markdown
# 複製到本地專案的 docs/research.md

# 場景 2: 複雜 PRD 草稿
# 在 Web 版起草 PRD
# 整理後導入 Claude Code
載入 PM
*create-prd  # 基於 Web 版草稿優化
```

**協作流程**:
```
1. Claude Web: 深度研究，生成初稿
2. 下載/複製結果到本地
3. Git commit 研究成果
4. Claude Code: 載入 BMAD 代理，基於研究執行工作流程
```

**適用 BMAD 階段**:
- ✅ Phase 1: Analysis (研究、腦力激盪)
- ✅ 複雜文件的初稿撰寫
- ❌ Phase 4: Implementation (需要檔案系統存取)

#### 6. Local LLM (如 Ollama)

**使用場景**:
- 🔒 敏感資料處理
- 🔒 離線開發環境
- 🔒 快速原型驗證
- 🔒 內部文件分析

**BMAD 整合**:
```bash
# 場景 1: 敏感資料的 Story Context 組裝
# 使用 Local LLM 處理包含敏感資訊的現有程式碼

ollama run codellama "分析這段程式碼的結構，不要洩漏敏感資訊：
$(cat src/payment/processor.js)"

# 將分析結果手動整合到 Story Context

# 場景 2: 離線開發
# 當無網路連線時
ollama run codellama "根據這個 Story 建議實作步驟：
$(cat docs/stories/story-005.md)"
```

**協作流程**:
```
1. 識別包含敏感資料的任務
2. 使用 Local LLM 離線處理
3. 清理敏感資訊後的結果
4. 整合回 Claude Code 的 BMAD 工作流程
```

**適用場景**:
- ✅ 金融資料處理
- ✅ 個人隱私資料分析
- ✅ 內部商業機密文件
- ✅ 合規性敏感程式碼

---

## 實戰工作流程

### 範例 1: 完整 Epic 開發

#### Phase 1-2: Analysis & Planning (Claude Code 主導)

```bash
# 1. 初始化專案
Claude Code:
  載入 Analyst → *workflow-init
  載入 PM → *create-prd
  載入 PM → *create-epics-and-stories
```

**平行任務** (可選):
```bash
# Claude Web: 深度市場研究
研究主題：Todo App 競品分析
輸出：research-notes.md

# Gemini CLI: 驗證 PRD
gemini-cli "審查 docs/PRD.md 的完整性和一致性"
```

#### Phase 3: Solutioning (Claude Code + 多工具驗證)

```bash
# 1. 主要架構設計
Claude Code:
  載入 Architect → *create-architecture

# 2. 平行驗證
Gemini CLI:
  gemini-cli "評估 docs/architecture.md 的技術選型合理性"

# 3. 獲取第二意見
Claude Web:
  "針對微服務 vs 單體架構，提供決策矩陣"

# 4. Party Mode 討論 (如有衝突)
Claude Code:
  載入 BMad Master → *party-mode
  議題：「整合 Gemini 提出的架構建議」
```

#### Phase 4: Implementation (多工具協同)

```bash
# 1. Sprint 規劃
Claude Code:
  載入 SM → *sprint-planning
  載入 SM → *epic-tech-context

# 2. Story 1 開發
Claude Code:
  載入 SM → *create-story (STORY-001)
  載入 SM → *story-context

# 3. 實作 (Claude Code + Copilot)
Claude Code:
  載入 DEV → *develop-story
  # Copilot 自動提供程式碼補全
  # DEV 決策主要邏輯

# 4. 背景探索 (Subagent)
Claude Code Subagent (平行):
  搜尋現有類似實作
  分析程式碼模式
  回報給 DEV

# 5. 程式碼審查 (多重驗證)
Claude Code:
  載入 DEV → *code-review

Gemini CLI (平行):
  gemini-cli "審查 STORY-001 實作，重點檢查安全性"

# 6. 比對審查結果
- Claude DEV 的審查報告
- Gemini 的獨立審查
- 找出差異，決定修正方向

# 7. 完成 Story
Claude Code:
  載入 DEV → *story-done
```

### 範例 2: Brownfield 專案分析

```bash
# 1. 程式碼庫文件化 (Claude Code + Subagent)
Claude Code:
  載入 Tech Writer → *document-project

  # Subagent 並行執行
  - 探索程式碼結構
  - 搜尋模式和慣例
  - 識別技術債務

# 2. 敏感程式碼分析 (Local LLM)
Local LLM:
  ollama run codellama "分析 src/payment/ 的架構模式"
  # 處理包含信用卡資訊的程式碼

# 3. 競品分析 (Claude Web)
Claude Web:
  "分析三個主要競爭對手的產品功能"
  輸出：competitor-analysis.md

# 4. 整合分析 (Claude Code)
Claude Code:
  載入 Analyst → *workflow-init (Brownfield)
  # 參考所有上述分析結果
```

---

## Git 協作策略

### Commit 規範

```bash
# Claude Code 的 Commit
git commit -m "feat(story-001): implement user registration

- Add User model
- Add POST /api/auth/register endpoint
- Add email validation
- Add password hashing

Story: STORY-001
Agent: DEV (Claude Code)
Co-Authored-By: Claude <noreply@anthropic.com>"

# Gemini CLI 審查的 Commit
git commit -m "docs(review): add Gemini code review for STORY-001

Review findings:
- Security: PASSED
- Code quality: 8/10
- Suggestions: Add rate limiting

Reviewer: Gemini CLI"

# 整合多工具結果的 Commit
git commit -m "refactor(story-001): address multi-tool review feedback

Applied feedback from:
- Claude DEV code-review
- Gemini CLI security review
- Copilot refactoring suggestions

Changes:
- Add rate limiting middleware
- Improve error messages
- Extract validation logic"
```

### Branch 策略

```
main
├── feature/epic-001-auth (Claude Code 主導)
│   ├── story-001-registration (DEV 實作)
│   ├── story-001-review (多工具審查)
│   └── story-001-final (整合修正)
├── research/market-analysis (Claude Web)
└── experiment/local-llm-tests (Local LLM)
```

---

## 設定與配置

### 1. Claude Code 設定

```json
// .claude/settings.local.json
{
  "bmad": {
    "primary_tool": "claude-code",
    "enable_subagent": true,
    "parallel_validation": true
  }
}
```

### 2. 整合 Copilot

```json
// .vscode/settings.json (或對應 IDE)
{
  "github.copilot.enable": {
    "*": true,
    "markdown": false  // BMAD 文件由 Claude Code 生成
  },
  "github.copilot.editor.enableAutoCompletions": true
}
```

### 3. Gemini CLI 設定

```bash
# .env
GEMINI_API_KEY=your_api_key

# scripts/gemini-review.sh
#!/bin/bash
story_file=$1
impl_file=$2

gemini-cli "審查 Story 實作：
Story: $(cat $story_file)
實作: $(cat $impl_file)

檢查項目：
1. 所有 AC 是否滿足
2. 安全性問題
3. 效能考量
4. 程式碼品質

輸出格式：JSON"
```

### 4. Local LLM 設定

```bash
# docker-compose.yml
version: '3'
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ./models:/root/.ollama

# 拉取模型
ollama pull codellama
ollama pull mistral
```

---

## 決策樹：何時使用哪個工具

```
需要執行 BMAD 工作流程？
├─ 是 → Claude Code (主環境)
└─ 否 →
    ├─ 需要程式碼自動補全？
    │   └─ 是 → Copilot (輔助 Claude Code)
    │
    ├─ 需要平行驗證/第二意見？
    │   └─ 是 → Gemini CLI
    │
    ├─ 需要複雜搜尋/探索？
    │   └─ 是 → Claude Subagent
    │
    ├─ 需要獨立研究/長文本？
    │   └─ 是 → Claude Web
    │
    └─ 處理敏感資料/離線？
        └─ 是 → Local LLM
```

---

## 最佳實踐

### ✅ DO (建議做法)

1. **統一狀態管理**
   - 所有 BMAD 狀態文件由 Claude Code 管理
   - 定期 Git commit 同步狀態

2. **明確工具職責**
   - 主要決策：Claude Code (BMAD 代理)
   - 快速補全：Copilot
   - 平行驗證：Gemini CLI
   - 背景任務：Subagent
   - 研究任務：Claude Web
   - 敏感資料：Local LLM

3. **多重驗證關鍵決策**
   - 架構設計：Claude Architect + Gemini 驗證
   - 程式碼審查：Claude DEV + Gemini CLI
   - 安全性檢查：多工具交叉驗證

4. **版本控制一切**
   - 每個工具的貢獻都要 commit
   - 使用 Co-Authored-By 標註協作
   - 清楚記錄工具使用決策

5. **定期同步**
   ```bash
   # 每完成一個 Story
   git add .
   git commit -m "feat: complete STORY-XXX (multi-tool collab)"
   git push

   # 其他工具同步
   git pull
   ```

### ❌ DON'T (避免做法)

1. **避免多工具同時編輯同一檔案**
   - ❌ Claude Code 和 Copilot 同時大幅修改
   - ✅ Claude Code 決策，Copilot 輔助補全

2. **避免繞過 BMAD 工作流程**
   - ❌ 直接用 Gemini CLI 生成 Story
   - ✅ Claude Code 執行 BMAD 工作流程，Gemini 驗證結果

3. **避免工具決策衝突未解決**
   - ❌ Claude 和 Gemini 意見不同，隨便選一個
   - ✅ 使用 Party Mode 或人工決策

4. **避免敏感資料洩漏**
   - ❌ 將包含敏感資料的程式碼傳給雲端 AI
   - ✅ 使用 Local LLM 處理敏感部分

5. **避免失去追蹤**
   - ❌ 在多個工具間切換沒有記錄
   - ✅ 文件化每個工具的使用和結果

---

## 故障排除

### 問題 1: 多工具建議衝突

**症狀**: Claude Code DEV 和 Gemini CLI 對同一問題給出不同建議

**解決方案**:
```bash
# 1. 記錄兩者意見
echo "## 決策記錄

### Claude Code DEV 建議
- 使用 JWT 認證

### Gemini CLI 建議
- 使用 Session-based 認證

### 決策
選擇 JWT，因為：
1. 無狀態，適合微服務
2. 跨域支援較好
3. 行動應用整合容易

決策者：Architect + PM (Party Mode)
日期：$(date)
" >> docs/decisions/auth-method.md

# 2. 執行決策
git add docs/decisions/
git commit -m "docs(decision): choose JWT over session auth"
```

### 問題 2: Copilot 建議與 Story 不符

**症狀**: Copilot 自動補全的程式碼不符合 Story AC

**解決方案**:
```bash
# DEV 代理需要主動審查 Copilot 建議
載入 DEV
"審查剛才 Copilot 建議的程式碼：
[paste code]

Story AC:
[paste from Story]

是否符合？如不符合，如何修正？"
```

### 問題 3: 工具間狀態不同步

**症狀**: Claude Web 的研究結果未整合到 Claude Code

**解決方案**:
```bash
# 1. 建立整合檢查點
# scripts/sync-research.sh
#!/bin/bash
echo "檢查待整合的研究結果..."
ls -l docs/research/
git status

echo "需要整合的文件："
git status | grep "docs/research/"

# 2. 定期執行
./scripts/sync-research.sh

# 3. 整合到 BMAD 工作流程
載入 Analyst
"請參考 docs/research/ 中的所有研究結果，
整合到當前的 PRD 中"
```

---

## 效能最佳化

### 並行任務範例

```bash
# 同時進行的任務

# Terminal 1: Claude Code (主任務)
載入 SM
*create-story

# Terminal 2: Gemini CLI (平行驗證)
gemini-cli "審查上一個 Story 的實作"

# Terminal 3: Subagent (背景探索)
# Claude Code 另一個 session
/task "探索現有認證相關的程式碼模式"

# Web Browser: Claude Web (獨立研究)
"OAuth 2.0 最佳實踐 2025"
```

**時間節省**: 串行 90 分鐘 → 並行 35 分鐘

---

## 實戰檢查清單

### 專案啟動

- [ ] Claude Code 安裝 BMAD-METHOD
- [ ] 設定 GitHub Copilot
- [ ] 安裝 Gemini CLI
- [ ] 設定 Local LLM (如需要)
- [ ] 建立 Git repository
- [ ] 定義工具使用策略
- [ ] 文件化協作規範

### 每日開發

- [ ] Claude Code 檢查 workflow-status
- [ ] 執行主要 BMAD 工作流程
- [ ] Copilot 輔助程式碼編寫
- [ ] Gemini 平行驗證關鍵決策
- [ ] Git commit 包含工具協作資訊
- [ ] 定期同步所有工具的輸出

### Story 完成

- [ ] Claude Code: DEV *code-review
- [ ] Gemini CLI: 獨立審查
- [ ] 比對審查結果
- [ ] 解決衝突意見
- [ ] 整合所有反饋
- [ ] Git commit 完整變更
- [ ] Claude Code: DEV *story-done

---

## 總結

### 多工具協作的價值

1. **互補性**: 各工具專長不同，互相補充
2. **驗證性**: 多重視角降低錯誤
3. **效率性**: 並行任務節省時間
4. **靈活性**: 離線、敏感資料都能處理

### 成功關鍵

1. **Claude Code 為中心**: 所有 BMAD 流程在此執行
2. **明確分工**: 每個工具職責清晰
3. **版本控制**: Git 追蹤所有協作
4. **定期同步**: 避免狀態分歧

### 預期效果

- 開發速度提升 30-50%
- 程式碼品質提升（多重審查）
- 決策品質提升（多角度驗證）
- 風險降低（平行驗證機制）

---

**Build More, Architect Dreams - Together**

多工具協同，讓 AI 輔助開發發揮最大價值。
