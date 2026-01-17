# Multi-Agent on the Web - UX Design Specification

_Created on 2025-11-11 by sir_
_Generated using BMad Method - Create UX Design Workflow v1.0_

---

## Executive Summary

**Multi-Agent on the Web** is a revolutionary multi-agent orchestration platform that transforms how professional developers use AI CLI tools. This UX design specification defines the user experience for a Flutter cross-platform application (Desktop + Web + Mobile) that enables real-time visualization, monitoring, and human-supervised control of distributed AI agents.

**Design Philosophy:**

The UX is built around three core principles:

1. **Transparent Orchestration** - Users see exactly what every agent is doing in real-time
2. **Human-in-Control** - Strategic checkpoints where users maintain decision authority
3. **Effortless Efficiency** - Complex parallel agent coordination feels simple and intuitive

**Target Experience:**

When a developer submits "Build user authentication system," they should feel:
- **Empowered**: Watching 3-4 agents work in parallel for them
- **In Control**: Confident they can intervene at any moment
- **Efficient**: Seeing 2-3x speed improvement without sacrificing quality
- **Informed**: Understanding exactly what's happening at all times

**Platform:** Flutter (Desktop primary, Web secondary, Mobile tertiary)

**Key Screens:** Dashboard, Task Submission, Agent Monitoring, Checkpoint Review, Worker Management

---

## 1. Design System Foundation

### 1.1 Design System Choice

**Selected System: Material Design 3 (Material You) for Flutter**

**Rationale:**

1. **Native Flutter Support**: Material 3 is first-class in Flutter with excellent component library
2. **Professional**: Trusted by enterprise developer tools (Google Cloud Console, Firebase, Android Studio)
3. **Accessibility Built-in**: WCAG 2.1 AA compliance by default
4. **Theming System**: Dynamic color schemes, light/dark mode, customizable
5. **Comprehensive**: 50+ components covering all needed UI patterns
6. **Responsive**: Adaptive layouts for all screen sizes

**Components Provided:**

- Navigation (NavigationRail, NavigationDrawer, BottomNavigationBar)
- Data Display (Cards, Lists, DataTable)
- Input (TextField, Dropdown, Checkbox, Switch, Slider)
- Feedback (SnackBar, Dialog, ProgressIndicator, Chip)
- Actions (Button variants, FAB, IconButton)
- Layout (Scaffold, AppBar, BottomAppBar)

**Custom Components Needed:**

1. **Agent Status Card** - Real-time agent activity visualization
2. **Task Timeline Visualizer** - Parallel task execution timeline
3. **Checkpoint Decision Interface** - Accept/Correct/Reject workflow
4. **Worker Health Monitor** - Machine resource visualization
5. **Evaluation Score Display** - 5-dimension quality scoring
6. **Correction Feedback Form** - Structured agent correction input

**Version:** Material Design 3 (Flutter 3.16+, material: 3.0+)

---

## 2. Core User Experience

### 2.1 Defining Experience

**The ONE Thing:** **Watch AI agents work for you in parallel, like managing a team**

**Core User Mental Model:**

Users should feel like a **team lead delegating work to specialists**:

- Submit a complex task → Like assigning work to your team
- Watch dashboard → Like checking team status board
- Respond to checkpoints → Like approving key decisions
- Intervene when needed → Like helping a teammate who's stuck
- See completion → Like reviewing team deliverables

**Key Interaction:** "Submit task → Monitor dashboard → Checkpoint approval → Completion"

**Primary User Actions (Frequency Ranking):**

1. **View Dashboard** (Every 30 seconds during active tasks) - Most frequent
2. **Submit New Task** (3-5 times per session) - Core value action
3. **Respond to Checkpoint** (1-3 times per task) - Critical decision points
4. **Review Task Details** (After completion) - Quality verification
5. **Manage Workers** (Once per session or when issues occur) - System health

### 2.2 Novel UX Patterns

This application introduces **2 novel UX patterns** not found in existing tools:

---

#### **Novel Pattern 1: Real-Time Multi-Agent Orchestration Dashboard**

**Problem Solved:**
Developers using AI tools today have no visibility into parallel execution. They must manually switch between tools and piece together what's happening.

**UX Solution:**

A live dashboard showing all agents, machines, and tasks simultaneously with real-time WebSocket updates.

**Pattern Mechanics:**

**User Goal:** Understand at a glance what all agents are doing right now

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Top Bar: Current Task Name | Overall Progress | Controls    │
├─────────────────────────────────────────────────────────────┤
│ Left Sidebar:                                               │
│ ┌─ Active Workers (3)                                       │
│ │  • Machine-1 [Claude Code] 🟢                             │
│ │  • Machine-2 [Gemini CLI] 🟢                              │
│ │  • Machine-3 [Ollama] 🟢                                  │
│ │                                                            │
│ └─ Idle Workers (1)                                         │
│                                                              │
│ Main Content Area:                                          │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Task Timeline (Horizontal Swimlanes)                 │   │
│ │                                                        │   │
│ │ Subtask 1 ▓▓▓▓▓░░░ 60%  [Agent: Claude Code]         │   │
│ │ Subtask 2 ▓▓▓▓▓▓▓▓ 90%  [Agent: Gemini CLI]          │   │
│ │ Subtask 3 ░░░░░░░░ 0%   [Waiting for Subtask 1]      │   │
│ │                                                        │   │
│ │ ⏸ CHECKPOINT in 2 minutes (after Subtask 2 completes)│   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ Bottom: Agent Activity Log (Live Feed)                      │
│ • 12:34:05 - Claude Code: Created API endpoint              │
│ • 12:34:12 - Gemini CLI: Reviewing error handling ✓         │
│ • 12:34:18 - Evaluation: Code Quality Score 8.5/10          │
└──────────────────────────────────────────────────────────────┘
```

**Visual Feedback:**

- **Colors**: Green (working), Blue (waiting), Orange (checkpoint needed), Red (error), Gray (idle)
- **Animation**: Pulsing glow on actively working agents
- **Progress**: Real-time progress bars with percentage
- **Notifications**: Toast messages for key events (checkpoint ready, task complete, errors)

**States:**

1. **Empty State**: "No active tasks. Submit a task to get started." (with CTA button)
2. **Loading**: Skeleton screens while initial task decomposition happens
3. **Active**: Real-time updates every 2-3 seconds via WebSocket
4. **Checkpoint Paused**: Highlighted pause state with modal overlay
5. **Completed**: Success animation, summary card, option to review details
6. **Error**: Error card with agent name, error message, retry/cancel options

**Platform Considerations:**

- **Desktop (1920x1080+)**: Full 3-column layout (workers sidebar, timeline, activity log)
- **Tablet (768-1024px)**: 2-column (collapsible sidebar, timeline + activity tabs)
- **Mobile (< 768px)**: Single column with bottom navigation tabs (Workers, Timeline, Activity)

**Accessibility:**

- **Keyboard**: Tab through workers, arrow keys to navigate timeline, Enter to expand details
- **Screen Reader**: "Machine-1 running Claude Code, 60% complete on Subtask 1: Create API endpoint"
- **High Contrast**: Status colors meet WCAG AAA contrast ratios

**Inspiration:**

Similar to:
- **CI/CD Pipeline Visualizers** (GitHub Actions, GitLab CI) - pipeline stage visualization
- **Network Topology Dashboards** (Datadog, Grafana) - real-time system health
- **Trading Platforms** (Bloomberg Terminal) - live multi-stream data
- **Process Orchestration Tools** (Airflow, Prefect) - DAG execution view

**What Makes This Novel:**

While pipeline visualizers exist for **systems**, this is the first **human-facing AI agent orchestration dashboard** where:
- Users actively monitor AI agents like team members
- Real-time collaboration between heterogeneous AI tools (not just one system)
- Human checkpoints integrated into the flow

---

#### **Novel Pattern 2: Inline Agent Correction with Feedback Loop**

**Problem Solved:**

When AI goes off track, current tools require:
1. Stopping the agent
2. Manually editing its output
3. Re-running from scratch
4. Losing the context of what went wrong

**UX Solution:**

A structured correction interface that lets users provide targeted feedback to agents, which then **re-execute with the correction context preserved**.

**Pattern Mechanics:**

**User Goal:** Fix an agent's mistake without losing progress or context

**Trigger:** User clicks "Correct" button on a checkpoint review or agent card

**Interaction Flow:**

1. **Trigger**: User clicks "Correct" on Agent X's work
2. **Context Display**: Modal shows:
   - What the agent was asked to do (original task)
   - What the agent actually did (output/code)
   - Why it might be wrong (if evaluation framework flagged issues)
3. **Correction Input**: User provides structured feedback:
   ```
   ┌─────────────────────────────────────────────────────┐
   │ Correction Type:                                     │
   │ ○ Wrong Approach     ● Incomplete      ○ Bug        │
   │                                                      │
   │ Specific Guidance:                                  │
   │ ┌─────────────────────────────────────────────────┐ │
   │ │ You forgot to handle the edge case when userId  │ │
   │ │ is null. Add validation before the database     │ │
   │ │ query.                                           │ │
   │ └─────────────────────────────────────────────────┘ │
   │                                                      │
   │ Reference Documents: (optional)                     │
   │ [+] Add file or link                                │
   │                                                      │
   │ [ ] Apply this correction to similar future tasks   │
   │                                                      │
   │ [Cancel]                        [Send to Agent] → │
   └─────────────────────────────────────────────────────┘
   ```
4. **Agent Re-execution**: System sends correction back to agent with:
   - Original task
   - Agent's previous attempt
   - User's correction guidance
   - Evaluation scores (if available)
5. **Progress Update**: Dashboard shows "🔄 Re-executing with correction"
6. **Verification**: New output presented for review (may trigger another checkpoint)

**Visual Feedback:**

- **Correction Badge**: Agent card shows "🔄 Corrected 1x" badge
- **Diff View**: Side-by-side comparison of before/after (for code changes)
- **Correction Timeline**: History panel shows all corrections made to this task

**Success Indicator:**

Agent produces corrected output, evaluation scores improve, user approves

**Error Recovery:**

- **Agent Still Wrong After Correction**: User can correct again (up to 3 times), then option to reassign to different agent or manual intervention
- **Correction Too Vague**: System suggests more specific guidance patterns
- **Timeout**: After 5 minutes, option to cancel and manually fix

**Accessibility:**

- **Keyboard**: Ctrl+E to open correction modal, Tab through form fields, Ctrl+Enter to submit
- **Screen Reader**: "Correction interface for Agent X. Original task: [description]. Agent output: [summary]. Provide correction guidance."

**Inspiration:**

Blends patterns from:
- **Code Review Systems** (GitHub PR reviews) - inline commenting and suggestions
- **Content Moderation Dashboards** - flagging and providing context
- **Customer Support Ticket Systems** (Zendesk) - structured feedback categories
- **Educational Platforms** (Coursera, Khan Academy) - "Try again with hint"

**What Makes This Novel:**

- **Preserves Context**: Unlike "stop and restart," this maintains the agent's working memory
- **Structured + Flexible**: Combines predefined correction types with free-text guidance
- **Learning Loop**: Option to apply correction to future similar tasks (system learning)
- **Multi-Agent Aware**: Correction can propagate to dependent agents (e.g., if Agent A's output feeds Agent B)

---

### 2.3 Core Experience Principles

Based on the defining experience and novel patterns, these principles guide all UX decisions:

1. **Speed Through Clarity**
   - Principle: Users should instantly understand system state without searching
   - Applies to: Dashboard layout, status indicators, progress visualization
   - Example: Color-coded agent cards, real-time progress percentages

2. **Strategic Guidance**
   - Principle: Guide users at critical decision points, stay invisible otherwise
   - Applies to: Checkpoints, error states, first-time user experience
   - Example: Checkpoints appear only when configured (e.g., before destructive actions, after major milestones)

3. **Flexible Control**
   - Principle: Default to automation, enable intervention anywhere
   - Applies to: Agent monitoring, task control, correction workflows
   - Example: "Pause Task," "Correct Agent," "Take Over Manually" always accessible

4. **Informative Feedback**
   - Principle: Every action produces clear confirmation, errors explain root cause
   - Applies to: Notifications, evaluation scores, error messages
   - Example: Not "Task failed" but "Task failed: Agent timed out after 5 minutes. Retry with timeout extension?"

---

## 3. Visual Foundation

### 3.1 Color System

**Design Approach:** Professional Developer Tool with Real-Time Status Emphasis

Given the nature of this tool (developer-focused, real-time monitoring, status-heavy), the color system prioritizes:
1. **Trustworthiness** (blues, professional)
2. **Clear Status Differentiation** (distinct semantic colors)
3. **Reduced Eye Strain** (support for dark mode, softer tones)
4. **Accessibility** (WCAG AA contrast ratios minimum)

---

#### **Primary Color Theme: "Trust & Efficiency"**

**Theme Personality:** Professional, reliable, tech-forward

**Color Palette:**

**Primary Colors:**
- **Primary**: `#1976D2` (Material Blue 700) - Trust, stability, main actions
  - Usage: Primary buttons, links, selected navigation, active states
  - Rationale: Blue conveys reliability and is the standard for developer tools (VS Code, GitHub, Docker)

- **Primary Variant**: `#1565C0` (Material Blue 800) - Hover states, emphasis

- **Secondary**: `#00897B` (Material Teal 600) - Growth, success, positive feedback
  - Usage: Success states, completion indicators, "approve" actions
  - Rationale: Teal differentiates from primary while maintaining professional feel

**Semantic Status Colors:**

- **Success**: `#2E7D32` (Material Green 800)
  - Agents working successfully, tasks completed, checkpoints approved

- **Warning**: `#F57C00` (Material Orange 800)
  - Checkpoints needing attention, agents approaching timeout, moderate issues

- **Error**: `#C62828` (Material Red 800)
  - Agent failures, task errors, critical issues

- **Info**: `#0277BD` (Material Light Blue 800)
  - Informational messages, agent status updates, system notifications

- **In Progress**: `#5E35B1` (Material Deep Purple 600)
  - Agents actively executing, tasks in flight

**Neutral Grayscale:**

Light Mode:
- **Surface**: `#FFFFFF` (White) - Card backgrounds, modals
- **Background**: `#F5F5F5` (Gray 100) - Page background
- **On Surface**: `#212121` (Gray 900) - Primary text
- **On Surface Variant**: `#616161` (Gray 700) - Secondary text
- **Outline**: `#BDBDBD` (Gray 400) - Borders, dividers

Dark Mode:
- **Surface**: `#1E1E1E` (Dark Gray) - Card backgrounds
- **Background**: `#121212` (Material Dark) - Page background
- **On Surface**: `#E0E0E0` (Gray 200) - Primary text
- **On Surface Variant**: `#A0A0A0` (Gray 400) - Secondary text
- **Outline**: `#424242` (Gray 800) - Borders, dividers

**Agent-Specific Colors** (for differentiation):

When multiple agents are visible simultaneously, use distinct hues:
- **Claude Code**: `#6366F1` (Indigo) - MCP/Claude brand association
- **Gemini CLI**: `#FB923C` (Amber) - Google AI brand association
- **Ollama (Local LLM)**: `#22C55E` (Green) - Privacy/local emphasis
- **Codex**: `#8B5CF6` (Violet) - OpenAI/creative association

**Elevation & Depth:**

Material 3 uses tonal surface colors instead of hard shadows:
- **Level 0**: Background color
- **Level 1**: +5% primary color tint (cards at rest)
- **Level 2**: +8% primary color tint (elevated cards, modals)
- **Level 3**: +11% primary color tint (dialogs, critical actions)

---

### 3.2 Typography System

**Font Families:**

- **Headings**: `Roboto` (Weight: 500 Medium for H1-H3, 400 Regular for H4-H6)
  - Rationale: Roboto is Material Design standard, excellent legibility, professional

- **Body Text**: `Roboto` (Weight: 400 Regular, 300 Light for captions)
  - Rationale: Consistent family reduces cognitive load

- **Monospace** (Code, IDs, Technical Data): `Roboto Mono` (Weight: 400)
  - Rationale: Pairs with Roboto, optimized for code readability

**Type Scale:**

| Element | Size | Weight | Line Height | Usage |
|---------|------|--------|-------------|-------|
| H1 | 32px | 500 | 40px | Page title (e.g., "Dashboard") |
| H2 | 24px | 500 | 32px | Section headers (e.g., "Active Workers") |
| H3 | 20px | 500 | 28px | Card titles (e.g., "Task: Build Auth System") |
| H4 | 18px | 400 | 26px | Subsection headers |
| Body Large | 16px | 400 | 24px | Primary content, task descriptions |
| Body | 14px | 400 | 20px | Secondary content, metadata |
| Caption | 12px | 300 | 16px | Timestamps, helper text, labels |
| Overline | 12px | 500 | 16px | Category labels (uppercase) |

**Text Color Contrast:**

- **Primary Text**: 87% opacity on surface (WCAG AAA)
- **Secondary Text**: 60% opacity on surface (WCAG AA)
- **Disabled Text**: 38% opacity on surface

---

### 3.3 Spacing & Layout Foundation

**Base Unit:** 8px (Material Design standard)

**Spacing Scale:**

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon padding, tight spacing |
| sm | 8px | Component internal padding |
| md | 16px | Card padding, form field spacing |
| lg | 24px | Section spacing, card margins |
| xl | 32px | Major section gaps |
| 2xl | 48px | Page-level spacing |
| 3xl | 64px | Hero sections (rare in this app) |

**Layout Grid:**

- **Desktop (1920px)**: 12-column grid, 24px gutters, 80px margins
- **Tablet (1024px)**: 12-column grid, 16px gutters, 32px margins
- **Mobile (375px)**: 4-column grid, 16px gutters, 16px margins

**Container Max Widths:**

- **Dashboard**: Full viewport width (fluid layout)
- **Task Details**: 1280px max (readable line length for content)
- **Modals**: 640px (standard), 960px (wide for diffs/code review)

---

### 3.4 Interactive Visualizations

**Color Theme Explorer:** `docs/ux-color-themes.html` (to be generated)

Will showcase:
- All semantic colors with labels and hex codes
- Sample UI components (buttons, cards, inputs) in both light and dark modes
- Contrast ratio verification
- Agent-specific color swatches

---

## 4. Design Direction

### 4.1 Chosen Design Approach

**Direction Name:** **"Mission Control Dashboard"**

**Personality:** Professional, efficient, real-time awareness

**Best For:** Power users who need comprehensive visibility into complex parallel processes

---

#### **4.1.1 Layout Decisions**

**Navigation Pattern:** **Left Sidebar Navigation (Desktop) / Bottom Tabs (Mobile)**

- **Rationale**:
  - Desktop users benefit from persistent navigation (Dashboard, Tasks, Workers, Settings always visible)
  - Left sidebar allows main content area to remain horizontally maximized for timeline visualization
  - Mobile users need quick thumb-accessible navigation between primary views

**Content Structure:** **Multi-column adaptive layout**

- **Desktop (1920x1080+)**: 3-column layout
  ```
  ┌───────┬─────────────────────────────┬─────────┐
  │  Nav  │   Main Content Area         │ Activity│
  │ (240) │      (Flexible)             │  (320)  │
  │       │                             │  Panel  │
  └───────┴─────────────────────────────┴─────────┘
  ```

- **Tablet (768-1024px)**: 2-column layout with collapsible sidebar
  ```
  ┌────┬──────────────────────────────────────┐
  │Nav │   Main + Activity (Tabbed)           │
  │(60)│                                      │
  └────┴──────────────────────────────────────┘
  ```

- **Mobile (<768px)**: Single column with bottom nav
  ```
  ┌────────────────────────────────────────────┐
  │           Main Content (Full Width)        │
  │                                            │
  │                                            │
  └────────────────────────────────────────────┘
  ┌──────┬──────┬──────┬──────────────────────┐
  │Dash  │Tasks │Workers│Settings              │
  └──────┴──────┴──────┴──────────────────────┘
  ```

**Content Organization:** **Card-based with real-time data streams**

- All entities (workers, tasks, agents) represented as cards
- Cards update in real-time via WebSocket (subtle animations for state changes)
- Cards can be expanded inline for details without navigation

---

#### **4.1.2 Visual Hierarchy Decisions**

**Density:** **Balanced (Information-rich without overwhelming)**

- **Rationale**: Developer users want maximum information density, but real-time monitoring requires scannable layouts
- **Application**:
  - Worker cards show 4-5 key metrics (status, CPU, memory, current task, tool)
  - Task timeline shows up to 10 concurrent subtasks before scrolling
  - Activity log shows last 20 events with "Load More"

**Header Emphasis:** **Bold, Color-Coded Headers**

- All status-bearing elements (cards, rows) have prominent headers with status color accents
- Example: Task card header has left border colored by status (green=running, orange=checkpoint, blue=queued)

**Content Focus:** **Mixed: Data-driven + Actionable**

- Primary focus: Real-time data (progress %, status, metrics)
- Secondary focus: Action buttons (Pause, Correct, Retry) always visible
- Tertiary focus: Historical data (logs, past tasks) accessible via tabs/expansion

---

#### **4.1.3 Interaction Pattern Decisions**

**Primary Actions:** **Inline expansion + modal for complex workflows**

- **Simple actions**: Inline (e.g., pause task → button click → confirmation toast)
- **Complex workflows**: Modal overlays (e.g., submit new task → multi-step modal with task details, checkpoint config, tool selection)
- **Destructive actions**: Always confirmation dialog (e.g., "Cancel task" → "Are you sure? This will stop all 4 agents.")

**Information Disclosure:** **Progressive disclosure with smart defaults**

- **Default View**: High-level summary (task name, overall progress, agent count)
- **Expansion**: Click card to reveal subtasks, agent assignments, evaluation scores
- **Deep Dive**: Click "Details" to open dedicated detail page with full logs, code diffs, timeline

**User Control:** **Guided automation with flexible override**

- System auto-allocates tasks to agents, but user can manually reassign
- Default checkpoint frequency is "medium" (every 3-5 subtasks), user can adjust per task
- Auto-retry on failure (up to 3 times), but user can disable or intervene

---

#### **4.1.4 Visual Style Decisions**

**Visual Weight:** **Balanced (Clear structure with subtle elevation)**

- **Rationale**: Professional tool needs visual order, but overly heavy UI distracts from content
- **Application**:
  - Cards use Material 3 tonal surfaces (no hard drop shadows)
  - Borders: 1px solid, subtle gray (#BDBDBD in light mode)
  - Elevation: Tonal color shifts (cards 5% lighter than background)

**Depth Cues:** **Subtle elevation + color tints**

- Modals: Level 3 surface (11% tint) with backdrop overlay (60% black opacity)
- Floating action buttons: Level 2 surface with 4dp soft shadow
- Active/hover states: 8% primary color overlay

**Border Style:** **Subtle borders + accent color left-border for status**

- Default cards: 1px border all sides
- Status cards: 4px left border in semantic color (green/orange/red/blue) + 1px other sides
- Focus states: 2px primary color border (for accessibility)

---

### 4.2 Design Direction Mockups

**Interactive Mockups:** `docs/ux-design-directions.html` (to be generated)

Will include 6-8 full-screen mockups showing:

1. **Dashboard - Empty State** (First-time user, no tasks submitted yet)
2. **Dashboard - Active Task** (3 agents working in parallel, real-time updates)
3. **Checkpoint Modal** (Review agent work, accept/correct/reject interface)
4. **Task Submission Flow** (Multi-step modal with task details, tool selection, checkpoint configuration)
5. **Worker Management** (Grid of worker cards with health metrics)
6. **Task Details Page** (Deep dive into completed task with timeline, logs, code diff)
7. **Correction Interface** (Inline agent correction modal with structured feedback)
8. **Mobile Dashboard** (Responsive view with bottom navigation)

---

## 5. User Journey Flows

### 5.1 Critical User Paths

Based on PRD analysis, there are **5 critical user journeys**:

1. Submit Task and Monitor Execution
2. Respond to Checkpoint
3. Correct Agent Work
4. Review Completed Task
5. Manage Workers

---

#### **Journey 1: Submit Task and Monitor Execution**

**User Goal:** Get multiple AI agents working on a complex task in parallel and monitor their progress in real-time

**Flow Approach:** **Progressive creation (start simple, add details incrementally)**

**Entry Point:** Dashboard → "Submit New Task" FAB (Floating Action Button)

---

**Flow Steps:**

**Step 1: Task Creation Modal (Initial)**

- **User sees:**
  ```
  ┌────────────────────────────────────────────┐
  │ Submit New Task                      [X]    │
  ├────────────────────────────────────────────┤
  │                                            │
  │ Task Description:                          │
  │ ┌────────────────────────────────────────┐ │
  │ │ Build a user authentication system     │ │
  │ │ with email/password and JWT tokens     │ │
  │ └────────────────────────────────────────┘ │
  │                                            │
  │ [Skip Advanced Options]   [Next: Config →] │
  └────────────────────────────────────────────┘
  ```

- **User does:** Types task description in natural language
- **System responds:**
  - AI analyzes description and suggests task complexity (shown on next screen)
  - "Next" button becomes enabled when description is >10 characters

**Step 2: Task Configuration (Advanced)**

- **User sees:**
  ```
  ┌────────────────────────────────────────────┐
  │ Task Configuration                  [X]     │
  ├────────────────────────────────────────────┤
  │                                            │
  │ Estimated Complexity: Medium               │
  │ Suggested Agent Count: 3-4                 │
  │                                            │
  │ Checkpoint Frequency:                      │
  │ ○ Low (Only before major milestones)      │
  │ ● Medium (Every 3-5 subtasks) ← Default   │
  │ ○ High (After every subtask)              │
  │                                            │
  │ Privacy Level:                             │
  │ ● Normal (Use all available tools)        │
  │ ○ Sensitive (Prefer local LLM)            │
  │                                            │
  │ Tool Preferences: (optional)               │
  │ [Claude Code ✓] [Gemini CLI ✓] [Ollama ✓] │
  │                                            │
  │ [← Back]              [Submit Task]        │
  └────────────────────────────────────────────┘
  ```

- **User does:** Reviews defaults, optionally adjusts checkpoint frequency or tool preferences
- **System responds:**
  - Updates estimated agent count based on selections
  - Validates at least one tool is selected

**Step 3: Task Submission Confirmation**

- **User sees:** Toast notification
  ```
  ✓ Task submitted successfully
  Decomposing into subtasks... (3-5 seconds)
  ```

- **System responds:**
  - Modal closes
  - Dashboard updates with new task card in "Initializing" state
  - Backend decomposes task into subtasks using AI
  - WebSocket sends updates to frontend

**Step 4: Real-Time Monitoring (Main Dashboard)**

- **User sees:**
  ```
  ┌────────────────────────────────────────────────────────────┐
  │ Dashboard                                            [+]    │
  ├────────────────────────────────────────────────────────────┤
  │                                                             │
  │ ACTIVE TASKS (1)                                           │
  │ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
  │ ┃ Build user authentication system                    ┃  │
  │ ┃ ▓▓▓▓▓░░░░░ 45% | 3 agents working | ⏱ 4 min elapsed ┃  │
  │ ┃                                                      ┃  │
  │ ┃ Subtask 1: Create API endpoints ▓▓▓▓▓▓▓░ 85%        ┃  │
  │ ┃   Agent: Claude Code (Machine-1) 🟢                  ┃  │
  │ ┃                                                      ┃  │
  │ ┃ Subtask 2: Implement JWT logic ▓▓▓▓░░░░ 50%         ┃  │
  │ ┃   Agent: Gemini CLI (Machine-2) 🟢                   ┃  │
  │ ┃                                                      ┃  │
  │ ┃ Subtask 3: Write unit tests ░░░░░░░░ 0%             ┃  │
  │ ┃   Agent: Waiting for Subtask 1 to complete          ┃  │
  │ ┃                                                      ┃  │
  │ ┃ ⏸ CHECKPOINT in ~2 minutes (after Subtask 2)       ┃  │
  │ ┃                                                      ┃  │
  │ ┃ [Pause Task]  [View Details]                        ┃  │
  │ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
  │                                                             │
  │ ACTIVITY LOG                                               │
  │ • 12:34:22 - Subtask 1: Added authentication route         │
  │ • 12:34:18 - Subtask 2: Researching JWT best practices     │
  │ • 12:34:05 - Task decomposed into 4 subtasks               │
  └─────────────────────────────────────────────────────────────┘
  ```

- **User does:** Watches progress bars update, reads activity log, waits for checkpoint
- **System responds:**
  - WebSocket updates every 2-3 seconds (progress %, agent status, activity log)
  - Subtle pulse animation on actively working agents
  - Desktop notification when checkpoint is ready

**Decision Point: Checkpoint Triggered**

- **Branching Logic:**
  - If user configured "Medium" checkpoints → System triggers checkpoint after Subtask 2 completes
  - If user configured "Low" checkpoints → System only triggers before final submission
  - If user configured "High" checkpoints → System triggers after every subtask

---

**Step 5: Checkpoint Ready Notification**

- **User sees:**
  ```
  Desktop Notification (if app in background):
  "⏸ Checkpoint Ready: Build user authentication system"

  Dashboard (if app in foreground):
  Task card border changes to orange, "CHECKPOINT READY" badge appears
  Modal auto-opens (after 3 seconds, or immediately if user clicks)
  ```

- **User does:** Clicks notification or waits for modal to appear
- **System responds:** Opens Checkpoint Review Modal (triggers Journey 2)

---

**Step 6: Task Completion**

- **User sees:**
  ```
  Desktop Notification:
  "✓ Task Completed: Build user authentication system"

  Dashboard:
  Task card border changes to green, success animation plays
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ ✓ Build user authentication system                  ┃
  ┃ Completed in 12 minutes | 4 subtasks | 3 agents     ┃
  ┃                                                      ┃
  ┃ Quality Score: 8.5/10 (Evaluation Framework)        ┃
  ┃                                                      ┃
  ┃ [View Details]  [Download Files]  [Archive]         ┃
  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  ```

- **User does:** Clicks "View Details" to review completed work (triggers Journey 4)
- **System responds:** Opens Task Details page

---

**Error State Example:**

If Subtask 1 fails (agent timeout, API error, etc.):

- **User sees:**
  ```
  Subtask 1: Create API endpoints ❌ FAILED
    Error: Agent timed out after 5 minutes
    [Retry] [Retry with Different Agent] [Cancel Task]

  Activity Log:
  • 12:35:00 - Subtask 1 failed: Timeout after 5 minutes
  • 12:34:55 - No response from Claude Code (Machine-1)
  ```

- **User does:** Clicks "Retry" or "Retry with Different Agent"
- **System responds:**
  - Auto-retry (first 2 failures)
  - After 3rd failure, requires user decision (retry, reassign, or cancel)

---

**Success State:**

Task completes successfully:
- All subtasks green checkmarks
- Overall progress 100%
- Quality score displayed (from evaluation framework)
- CTA: "View Details" or "Start New Task"

---

#### **Journey 2: Respond to Checkpoint**

**User Goal:** Review agent work at a critical decision point and decide whether to proceed, correct, or reject

**Flow Approach:** **Guided decision flow with clear options**

**Entry Point:** Checkpoint Ready notification (from Journey 1) or Dashboard → Click task with checkpoint badge

---

**Flow Steps:**

**Step 1: Checkpoint Review Modal Opens**

- **User sees:**
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ ⏸ CHECKPOINT REVIEW                              [X]     │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │ Task: Build user authentication system                   │
  │ Checkpoint: After JWT Implementation (Subtask 2)         │
  │                                                           │
  │ What's been completed:                                   │
  │ ✓ Subtask 1: Create API endpoints (Claude Code)          │
  │ ✓ Subtask 2: Implement JWT logic (Gemini CLI)            │
  │                                                           │
  │ What's next:                                             │
  │ → Subtask 3: Write unit tests                            │
  │ → Subtask 4: Generate documentation                      │
  │                                                           │
  │ ─────────────────────────────────────────────────────── │
  │                                                           │
  │ Evaluation Scores:                                       │
  │ • Code Quality: 8.5/10 ✓                                 │
  │ • Completeness: 7.0/10 ⚠ (Missing error handling)       │
  │ • Security: 9.0/10 ✓                                     │
  │ • Architecture: 8.0/10 ✓                                 │
  │ • Testability: 6.5/10 ⚠ (Low test coverage)             │
  │                                                           │
  │ ─────────────────────────────────────────────────────── │
  │                                                           │
  │ Recent Changes:                                          │
  │ [View Code Diff] [View Full Output]                      │
  │                                                           │
  │ ┌───────────────────────────────────────────────────┐   │
  │ │ src/auth/jwt.js                                    │   │
  │ │ + 45 lines added | - 2 lines removed               │   │
  │ │                                                    │   │
  │ │ +  function generateToken(user) {                 │   │
  │ │ +    const payload = { userId: user.id, ... };    │   │
  │ │ +    return jwt.sign(payload, SECRET_KEY, ...);   │   │
  │ │ +  }                                               │   │
  │ └───────────────────────────────────────────────────┘   │
  │                                                           │
  │ Your Decision:                                           │
  │ ┌────────────┐  ┌────────────┐  ┌────────────┐          │
  │ │  ✓ Accept  │  │  🔧 Correct │  │  ✗ Reject  │          │
  │ │            │  │             │  │            │          │
  │ │ Continue   │  │ Provide     │  │ Stop task  │          │
  │ │ as planned │  │ feedback    │  │ and cancel │          │
  │ └────────────┘  └────────────┘  └────────────┘          │
  └──────────────────────────────────────────────────────────┘
  ```

- **User does:** Reviews evaluation scores, checks code diff, reads "What's next"
- **System responds:**
  - Highlights evaluation warnings (⚠ icons on scores < 7.5)
  - Code diff shows only changed files (not full codebase)

**Decision Point: User Chooses Action**

---

**Option A: User Clicks "✓ Accept"**

- **System responds:**
  ```
  Toast Notification:
  "✓ Checkpoint approved. Continuing to Subtask 3..."

  Modal closes, dashboard updates:
  Task card border returns to green (in progress)
  Subtask 3 starts executing
  ```

- **Success State:** Task continues normally, next checkpoint scheduled

---

**Option B: User Clicks "🔧 Correct" (triggers Journey 3)**

- **System responds:** Modal transitions to Correction Interface (see Journey 3)

---

**Option C: User Clicks "✗ Reject"**

- **System responds:**
  ```
  Confirmation Dialog:
  "Are you sure you want to reject and cancel this task?"

  ⚠ This will stop all agents and discard progress.

  [Cancel]  [Yes, Reject Task]
  ```

- **User does:** Confirms or cancels
- **System responds:**
  - If confirmed: Task status changes to "Rejected," all agents stop, task moves to "Completed" tab with red border
  - If canceled: Returns to checkpoint review modal

---

**Secondary Actions:**

User can also:
- **"View Code Diff"** → Opens full side-by-side diff in expanded modal
- **"View Full Output"** → Opens scrollable panel with all agent logs, files created, etc.
- **"Skip This Checkpoint"** → Proceeds without review (only if checkpoint was optional/recommended, not required)

---

#### **Journey 3: Correct Agent Work**

**User Goal:** Provide targeted feedback to an agent that produced incorrect or incomplete output, and have the agent re-execute with the correction

**Flow Approach:** **Structured feedback form with context preservation**

**Entry Point:** Checkpoint Review Modal → "🔧 Correct" button

---

**Flow Steps:**

**Step 1: Correction Interface Opens**

- **User sees:**
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ 🔧 CORRECT AGENT WORK                            [X]     │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │ Agent: Gemini CLI (Machine-2)                            │
  │ Subtask: Implement JWT logic                             │
  │                                                           │
  │ Original Request:                                        │
  │ "Implement JWT token generation and verification         │
  │  with secure secret key management"                      │
  │                                                           │
  │ What the agent did:                                      │
  │ [View Output] [View Code]                                │
  │                                                           │
  │ Evaluation Issues Detected:                              │
  │ • Completeness: 7.0/10 - Missing error handling          │
  │ • Testability: 6.5/10 - Low test coverage                │
  │                                                           │
  │ ─────────────────────────────────────────────────────── │
  │                                                           │
  │ Correction Type: (select one)                            │
  │ ○ Wrong Approach      ● Incomplete      ○ Bug            │
  │ ○ Style Issue         ○ Missing Feature  ○ Other         │
  │                                                           │
  │ Specific Guidance: *                                     │
  │ ┌───────────────────────────────────────────────────┐   │
  │ │ Add try-catch error handling for the token        │   │
  │ │ generation function. Also, add validation for     │   │
  │ │ empty or null userId before generating tokens.    │   │
  │ └───────────────────────────────────────────────────┘   │
  │                                                           │
  │ Reference Files or Docs: (optional)                      │
  │ [+] Add file, link, or example                           │
  │                                                           │
  │ Additional Options:                                      │
  │ [ ] Apply this correction pattern to similar future     │
  │     tasks (System will learn from this)                  │
  │ [ ] Escalate to different agent if re-execution fails    │
  │                                                           │
  │ [Cancel]                          [Send Correction]      │
  └──────────────────────────────────────────────────────────┘
  ```

- **User does:**
  1. Selects correction type (helps system categorize)
  2. Writes specific guidance in free-text field (required)
  3. Optionally adds reference files or links
  4. Optionally enables learning mode

- **System responds:**
  - "Send Correction" button enables only when guidance field has >10 characters
  - Character counter shows (min 10, recommended 50-200)

**Step 2: Correction Sent to Agent**

- **User sees:**
  ```
  Toast Notification:
  "🔄 Correction sent to Gemini CLI. Re-executing subtask..."

  Modal closes, dashboard updates:
  Subtask 2 shows "🔄 Re-executing with correction"
  Badge appears: "Corrected 1x"
  ```

- **System responds:**
  - Backend sends correction package to agent:
    ```json
    {
      "original_task": "Implement JWT logic...",
      "previous_attempt": {code, files, logs},
      "correction": {
        "type": "Incomplete",
        "guidance": "Add try-catch error handling...",
        "evaluation_scores": {...}
      },
      "retry_count": 1
    }
    ```
  - Agent re-executes with additional context
  - WebSocket sends real-time updates

**Step 3: Re-execution Progress**

- **User sees:**
  ```
  Dashboard:
  Subtask 2: Implement JWT logic 🔄 Re-executing
  ▓▓▓░░░░░ 35%

  Activity Log:
  • 12:40:15 - Gemini CLI: Re-executing with user correction
  • 12:40:10 - Correction applied: Add error handling
  ```

- **User does:** Monitors progress (same as Journey 1)
- **System responds:** Real-time updates via WebSocket

**Step 4: Re-execution Completes**

**Success Path:**

- **User sees:**
  ```
  Desktop Notification:
  "✓ Correction applied successfully. Subtask 2 complete."

  Dashboard:
  Subtask 2: Implement JWT logic ✓ Complete
  Badge: "Corrected 1x" (green checkmark)

  New Checkpoint Triggered (if configured):
  "Review updated JWT implementation"
  ```

- **System responds:**
  - Task continues to next subtask
  - Correction history recorded in task metadata
  - If learning mode enabled, system saves correction pattern

**Failure Path (Agent Still Wrong):**

- **User sees:**
  ```
  Desktop Notification:
  "⚠ Re-execution completed, but evaluation scores remain low"

  Dashboard:
  Subtask 2: Implement JWT logic ⚠ Needs Review
  Badge: "Corrected 1x"

  Evaluation Scores:
  • Completeness: 7.2/10 (improved from 7.0, but still low)

  [Correct Again] [Try Different Agent] [Take Over Manually]
  ```

- **User does:** Chooses one of three options:
  1. **Correct Again** → Opens Correction Interface (Step 1) with previous correction pre-filled
  2. **Try Different Agent** → Reassigns subtask to a different agent (e.g., Claude Code instead of Gemini)
  3. **Take Over Manually** → Marks subtask as "Manual intervention required," opens file editor or link to code

- **System responds:** Based on user choice

**Error Recovery:**

- **Max Correction Attempts:** 3 per subtask
  - After 3rd correction attempt, system requires user to manually intervene or cancel task

- **Agent Timeout During Re-execution:**
  - Same retry logic as initial execution (see Journey 1 error states)

**Correction History Tracking:**

- All corrections stored in task metadata:
  ```json
  {
    "subtask_id": "...",
    "corrections": [
      {
        "timestamp": "2025-11-11T12:40:10Z",
        "user": "sir",
        "type": "Incomplete",
        "guidance": "Add try-catch error handling...",
        "result": "Success",
        "evaluation_before": {completeness: 7.0},
        "evaluation_after": {completeness: 8.5}
      }
    ]
  }
  ```

- Visible in Task Details page (Journey 4)

---

#### **Journey 4: Review Completed Task**

**User Goal:** Inspect the final output of a completed task, download files, and verify quality

**Flow Approach:** **Comprehensive detail page with tabbed sections**

**Entry Point:** Dashboard → Completed task card → "View Details" button

---

**Flow Steps:**

**Step 1: Task Details Page Loads**

- **User sees:**
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ ← Back to Dashboard                                       │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │ ✓ Build user authentication system                       │
  │ Completed: 2025-11-11 12:45:00 | Duration: 12 minutes    │
  │ Agents: Claude Code, Gemini CLI, Ollama                  │
  │                                                           │
  │ Overall Quality Score: 8.5/10                            │
  │ [Download All Files] [Export Report] [Archive Task]      │
  │                                                           │
  │ ─────────────────────────────────────────────────────── │
  │                                                           │
  │ TABS:                                                    │
  │ [Summary] [Timeline] [Files] [Evaluation] [Logs]         │
  │                                                           │
  │ ══════════════════════════════════════════════════════ │
  │ SUMMARY TAB (Active):                                    │
  │                                                           │
  │ Subtasks Completed: 4/4                                  │
  │ ✓ Subtask 1: Create API endpoints (Claude Code)          │
  │    Files: src/api/auth.js, src/routes/auth.js            │
  │    Duration: 3 min | Quality: 9.0/10                     │
  │                                                           │
  │ ✓ Subtask 2: Implement JWT logic (Gemini CLI) 🔄         │
  │    Files: src/auth/jwt.js, src/utils/secret.js           │
  │    Duration: 5 min (1 correction) | Quality: 8.5/10      │
  │    Correction: Added error handling for token generation │
  │                                                           │
  │ ✓ Subtask 3: Write unit tests (Claude Code)              │
  │    Files: tests/auth.test.js                             │
  │    Duration: 2 min | Quality: 8.0/10                     │
  │                                                           │
  │ ✓ Subtask 4: Generate documentation (Ollama)             │
  │    Files: docs/AUTH.md                                   │
  │    Duration: 2 min | Quality: 8.0/10                     │
  │                                                           │
  │ Checkpoints Reviewed: 2                                  │
  │ • After Subtask 2 → Correction applied                   │
  │ • Final review → Approved                                │
  │                                                           │
  └──────────────────────────────────────────────────────────┘
  ```

- **User does:** Reads summary, clicks tabs to explore details
- **System responds:** Loads tab content on demand (lazy loading for performance)

**Step 2: User Explores Tabs**

---

**Tab 2: Timeline**

- **User sees:**
  ```
  TIMELINE (Gantt-style visualization):

  12:30 ─┬─ Task submitted
         │
  12:31 ─┼─ Decomposed into 4 subtasks
         │
         ├─ [Subtask 1: Claude Code] ▓▓▓▓▓ (3 min)
  12:34 ─┤  ✓ Complete
         │
         ├─ [Subtask 2: Gemini CLI]  ▓▓░░ (2 min) → 🔄 Correction
  12:36 ─┤                            ▓▓▓ (3 min)
  12:39 ─┤  ✓ Complete
         │
         │  ⏸ CHECKPOINT (1 min review)
  12:40 ─┤
         │
         ├─ [Subtask 3: Claude Code] ▓▓▓ (2 min)
  12:42 ─┤  ✓ Complete
         │
         ├─ [Subtask 4: Ollama]      ▓▓ (2 min)
  12:44 ─┤  ✓ Complete
         │
         │  ⏸ Final CHECKPOINT (1 min review)
  12:45 ─┴─ ✓ Task Complete

  Total Parallel Time Saved: 4 minutes
  (Sequential execution would have taken 16 minutes)
  ```

- **User does:** Visualizes which subtasks ran in parallel, where delays occurred
- **System responds:** Interactive timeline (hover to see details, click to jump to subtask)

---

**Tab 3: Files**

- **User sees:**
  ```
  FILES CREATED/MODIFIED:

  📁 src/
    📁 api/
      📄 auth.js (234 lines, +234 -0) [Claude Code]
    📁 auth/
      📄 jwt.js (145 lines, +145 -0) [Gemini CLI]
    📁 routes/
      📄 auth.js (89 lines, +89 -0) [Claude Code]
    📁 utils/
      📄 secret.js (45 lines, +45 -0) [Gemini CLI]

  📁 tests/
    📄 auth.test.js (178 lines, +178 -0) [Claude Code]

  📁 docs/
    📄 AUTH.md (120 lines, +120 -0) [Ollama]

  Actions:
  [Download All as .zip] [View Diff] [Open in IDE]
  ```

- **User does:** Clicks on a file to view contents
- **System responds:** Opens syntax-highlighted file viewer modal with download option

---

**Tab 4: Evaluation**

- **User sees:**
  ```
  EVALUATION FRAMEWORK SCORES:

  Overall: 8.5/10 ✓ GOOD

  Dimension Scores:

  1. Code Quality: 9.0/10 ✓ EXCELLENT
     • No syntax errors
     • Linting passed (ESLint)
     • Complexity: Low (avg cyclomatic complexity: 3.2)
     • Consistent code style

  2. Completeness: 8.0/10 ✓ GOOD
     • All requirements met
     • Error handling: Complete
     • Edge cases: 85% covered
     • ⚠ Missing: Rate limiting (mentioned in original PRD)

  3. Security: 9.0/10 ✓ EXCELLENT
     • No SQL injection vulnerabilities
     • Password hashing: bcrypt (secure)
     • JWT secret: Environment variable (secure)
     • HTTPS enforced
     • ⚠ Warning: JWT expiration set to 7 days (consider shorter)

  4. Architecture Alignment: 8.0/10 ✓ GOOD
     • Follows MVC pattern
     • Separation of concerns: Good
     • API consistency: RESTful
     • ⚠ Minor: Error handling could use centralized middleware

  5. Testability: 8.0/10 ✓ GOOD
     • Test coverage: 82%
     • Unit tests: Present
     • Integration tests: Present
     • Mocks: Properly used
     • ⚠ Missing: E2E tests

  [View Detailed Report] [Export as PDF]
  ```

- **User does:** Reviews scores, expands details, exports report
- **System responds:** Detailed breakdown shows exact evaluation rules applied

---

**Tab 5: Logs**

- **User sees:**
  ```
  ACTIVITY LOGS (811 events):

  Filter: [All Agents ▾] [All Events ▾] [Search...]

  12:45:23 - Task marked as complete
  12:45:20 - Final checkpoint approved by user
  12:44:58 - Subtask 4 completed (Ollama)
  12:44:55 - Evaluation: Documentation quality 8.0/10
  12:44:30 - Ollama: Generated API documentation
  12:42:45 - Subtask 3 completed (Claude Code)
  12:42:40 - Evaluation: Test coverage 82%
  12:42:10 - Claude Code: Wrote integration tests
  12:41:50 - Claude Code: Wrote unit tests for JWT
  12:40:30 - Checkpoint: User approved corrected JWT implementation
  12:39:45 - Subtask 2 re-execution completed (Gemini CLI)
  12:39:40 - Evaluation: Completeness improved to 8.5/10
  12:39:20 - Gemini CLI: Added error handling (user correction)
  12:40:10 - User correction applied: "Add try-catch error handling..."
  12:38:30 - Checkpoint: User requested correction
  12:36:45 - Subtask 2 initial completion (Gemini CLI)
  12:36:40 - Evaluation: Completeness 7.0/10 (low - triggered checkpoint)
  ...

  [Load More] [Export Logs]
  ```

- **User does:** Filters logs by agent or event type, searches for keywords
- **System responds:** Real-time filtering, lazy loading for performance

---

**Step 3: User Downloads Files or Exports Report**

- **User clicks:** "Download All Files"
- **System responds:**
  ```
  Toast Notification:
  "Preparing download... (2 seconds)"

  Browser download starts:
  "build-user-authentication-system_2025-11-11.zip" (234 KB)
  ```

- **Zip Contents:**
  - All created/modified files in folder structure
  - `TASK_REPORT.md` (summary with evaluation scores, timeline, logs)
  - `METADATA.json` (full task data for reproducibility)

---

**Secondary Actions:**

- **Archive Task:** Moves task from "Completed" to "Archived" tab (reduces clutter)
- **Export Report:** Generates PDF with summary, evaluation scores, timeline visualization
- **Open in IDE:** Deep link to VS Code/Cursor with files loaded (if configured)

---

#### **Journey 5: Manage Workers**

**User Goal:** View health status of all Worker machines, add new workers, or troubleshoot offline workers

**Flow Approach:** **Grid-based overview with drill-down details**

**Entry Point:** Dashboard sidebar → "Workers" navigation item

---

**Flow Steps:**

**Step 1: Workers Page Loads**

- **User sees:**
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ Workers Management                       [+ Add Worker]  │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │ ONLINE (3)                                               │
  │                                                           │
  │ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐│
  │ │ 🟢 Machine-1   │ │ 🟢 Machine-2   │ │ 🟢 Machine-3   ││
  │ │ Desktop PC     │ │ Laptop         │ │ Cloud VM       ││
  │ │                │ │                │ │                ││
  │ │ CPU: 45%       │ │ CPU: 23%       │ │ CPU: 67%       ││
  │ │ Memory: 60%    │ │ Memory: 40%    │ │ Memory: 55%    ││
  │ │ Disk: 30%      │ │ Disk: 72%      │ │ Disk: 20%      ││
  │ │                │ │                │ │                ││
  │ │ Tools:         │ │ Tools:         │ │ Tools:         ││
  │ │ • Claude Code  │ │ • Gemini CLI   │ │ • Ollama       ││
  │ │ • Gemini CLI   │ │ • Ollama       │ │                ││
  │ │                │ │                │ │                ││
  │ │ Current Task:  │ │ Current Task:  │ │ Current Task:  ││
  │ │ Subtask 1      │ │ Idle           │ │ Subtask 4      ││
  │ │                │ │                │ │                ││
  │ │ Heartbeat:     │ │ Heartbeat:     │ │ Heartbeat:     ││
  │ │ 5 sec ago      │ │ 3 sec ago      │ │ 8 sec ago      ││
  │ │                │ │                │ │                ││
  │ │ [Details]      │ │ [Details]      │ │ [Details]      ││
  │ └────────────────┘ └────────────────┘ └────────────────┘│
  │                                                           │
  │ OFFLINE (1)                                              │
  │ ┌────────────────┐                                       │
  │ │ 🔴 Machine-4   │                                       │
  │ │ Raspberry Pi   │                                       │
  │ │                │                                       │
  │ │ Last Seen:     │                                       │
  │ │ 2 hours ago    │                                       │
  │ │                │                                       │
  │ │ [Reconnect]    │                                       │
  │ └────────────────┘                                       │
  │                                                           │
  └──────────────────────────────────────────────────────────┘
  ```

- **User does:** Scans worker cards for health status, checks which machines are idle
- **System responds:** Real-time updates every 30 seconds (WebSocket heartbeat status)

**Step 2: User Clicks "Details" on a Worker**

- **User sees:**
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ Worker Details: Machine-1                        [X]     │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │ Machine Information:                                     │
  │ • Name: Machine-1 (Desktop PC)                           │
  │ • Machine ID: abc123-def456-...                          │
  │ • IP Address: 192.168.1.100                              │
  │ • OS: Windows 11                                         │
  │ • Registered: 2025-11-10 10:30:00                        │
  │                                                           │
  │ Resource Usage (Last 24 Hours):                          │
  │ [Line Chart: CPU, Memory, Disk over time]                │
  │                                                           │
  │ Installed Tools:                                         │
  │ ✓ Claude Code v1.2.3 (MCP connected)                     │
  │ ✓ Gemini CLI v0.8.1                                      │
  │ ✗ Ollama (Not installed)                                 │
  │                                                           │
  │ Task History (Last 10):                                  │
  │ 1. Build user auth system - Subtask 1 (12 min ago) ✓    │
  │ 2. Refactor API routes - Subtask 2 (1 hour ago) ✓       │
  │ 3. Fix bug in payment - Subtask 1 (3 hours ago) ✓       │
  │ ...                                                      │
  │                                                           │
  │ [Edit Worker] [Remove Worker] [Run Diagnostics]          │
  └──────────────────────────────────────────────────────────┘
  ```

- **User does:** Reviews resource usage chart, checks task history, optionally edits or removes worker
- **System responds:** Charts generated from historical metric data (last 24 hours)

**Step 3: User Adds New Worker**

- **User clicks:** "+ Add Worker" button on Workers page
- **User sees:**
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ Add New Worker                                   [X]     │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │ Step 1: Install Worker Agent on your machine            │
  │                                                           │
  │ Choose your platform:                                    │
  │ [Windows] [macOS] [Linux]                                │
  │                                                           │
  │ Installation Command:                                    │
  │ ┌───────────────────────────────────────────────────┐   │
  │ │ pip install multi-agent-worker                     │   │
  │ │ worker-agent register --token=abc123xyz           │   │
  │ └───────────────────────────────────────────────────┘   │
  │ [Copy Command]                                           │
  │                                                           │
  │ Step 2: Configure AI Tools                               │
  │                                                           │
  │ The worker will detect installed tools automatically.    │
  │ Supported tools:                                         │
  │ • Claude Code (requires MCP server running)              │
  │ • Gemini CLI (requires API key)                          │
  │ • Ollama (requires local installation)                   │
  │ • Codex (requires OpenAI API key)                        │
  │                                                           │
  │ Step 3: Verify Connection                                │
  │                                                           │
  │ Status: ⏳ Waiting for worker to connect...              │
  │                                                           │
  │ Once connected, the worker will appear in the Workers    │
  │ list and will be available for task allocation.          │
  │                                                           │
  │ [Close]                                                  │
  └──────────────────────────────────────────────────────────┘
  ```

- **User does:** Copies installation command, runs it on their machine, waits for connection
- **System responds:**
  - When worker connects, modal updates: "✓ Worker connected! Machine-5 is now online."
  - New worker card appears in Workers page

**Step 4: User Troubleshoots Offline Worker**

- **User clicks:** "Reconnect" on offline worker card (Machine-4)
- **User sees:**
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ Reconnect Worker: Machine-4                      [X]     │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │ Machine-4 (Raspberry Pi) has been offline for 2 hours.  │
  │                                                           │
  │ Last known status:                                       │
  │ • Last heartbeat: 2025-11-11 10:45:00                    │
  │ • Last task: None (idle)                                 │
  │ • Error: No response to ping                             │
  │                                                           │
  │ Troubleshooting steps:                                   │
  │ 1. Check if the machine is powered on                    │
  │ 2. Verify network connectivity                           │
  │ 3. Ensure worker agent service is running:               │
  │    `systemctl status worker-agent` (Linux)               │
  │ 4. Check agent logs:                                     │
  │    `worker-agent logs --tail=50`                         │
  │                                                           │
  │ Actions:                                                 │
  │ [Retry Connection] [Mark as Inactive] [Remove Worker]    │
  │                                                           │
  └──────────────────────────────────────────────────────────┘
  ```

- **User does:** Follows troubleshooting steps on the actual machine, clicks "Retry Connection"
- **System responds:**
  - Attempts WebSocket reconnection
  - If successful: Worker card moves to "Online" section, toast notification "✓ Machine-4 reconnected"
  - If fails: "Still offline. Check machine connectivity."

---

**Error States:**

- **Worker Overloaded (CPU > 90%, Memory > 90%):**
  - Worker card shows ⚠️ warning badge
  - Task allocation system deprioritizes this worker
  - User gets notification: "Machine-1 is running at high resource usage. Consider adding more workers."

- **Worker Timeout During Task:**
  - Task fails with error: "Worker Machine-1 stopped responding"
  - Auto-retry on different worker
  - Worker status changes to "⚠️ Unstable" until heartbeat recovers

---

## 6. Component Library

### 6.1 Component Strategy

**Design System Foundation:** Material Design 3 (Flutter)

**Custom Components:** 6 domain-specific components

---

#### **Custom Component 1: Agent Status Card**

**Purpose:** Display real-time status of an individual agent working on a subtask

**Anatomy:**

```
┌─────────────────────────────────────────────────────┐
│ 🟢 Claude Code (Machine-1)             [︙ Menu]    │ ← Header
├─────────────────────────────────────────────────────┤
│ Subtask: Create API endpoints                      │ ← Task Name
│ ▓▓▓▓▓▓░░░░ 60%                                      │ ← Progress Bar
│                                                     │
│ Status: Working on auth routes...                  │ ← Live Status
│ Elapsed: 2m 34s                                    │ ← Timer
│                                                     │
│ [Pause] [View Details]                             │ ← Actions
└─────────────────────────────────────────────────────┘
```

**States:**

- **Active (Working)**: Green border, pulsing glow animation, progress bar animating
- **Idle**: Gray border, no animation, "Waiting for task" text
- **Paused**: Orange border, pause icon, "Paused by user" text
- **Error**: Red border, error icon, error message
- **Complete**: Green checkmark icon, 100% progress, "Completed" badge

**Variants:**

- **Compact**: Header only (for sidebar list)
- **Expanded**: Full details (for main dashboard)
- **Mobile**: Single column layout, smaller font sizes

**Behavior:**

- **Click Card**: Expands to show subtask details (logs, files, evaluation scores)
- **Click "Pause"**: Sends pause command to backend, card transitions to Paused state
- **Click "View Details"**: Opens subtask detail modal

**Accessibility:**

- **ARIA Role**: `role="article"` with `aria-label="Agent status for Claude Code on Machine-1"`
- **Keyboard**: Tab to focus, Enter to expand, Arrow keys to navigate actions
- **Screen Reader**: "Claude Code on Machine-1, working on Create API endpoints, 60% complete, status: Working on auth routes, elapsed time 2 minutes 34 seconds"

---

#### **Custom Component 2: Task Timeline Visualizer**

**Purpose:** Display parallel execution of subtasks across time (Gantt-style)

**Anatomy:**

```
Timeline (horizontal swimlanes):

Subtask 1 ▓▓▓▓▓▓▓▓ 100% [Claude Code]  ✓
Subtask 2 ▓▓▓▓░░░░  50% [Gemini CLI]  🟢
Subtask 3 ░░░░░░░░   0% [Waiting...]   ⏸
Subtask 4 ░░░░░░░░   0% [Waiting...]   ⏸
          |-------|
          0       5 min
```

**States:**

- **Not Started**: Empty progress bar, gray color, "Waiting" label
- **In Progress**: Partial progress bar, blue/purple color, percentage, agent name
- **Complete**: Full progress bar, green color, checkmark icon
- **Error**: Red progress bar, X icon, "Failed" label
- **Paused**: Orange progress bar, pause icon, "Paused" label

**Variants:**

- **Compact**: Single line per subtask with inline progress bar
- **Detailed**: Multi-line with agent details, timestamps, dependencies

**Behavior:**

- **Hover Subtask**: Tooltip shows start time, duration, agent details
- **Click Subtask**: Expands to show subtask logs and files
- **Auto-scroll**: Automatically scrolls to show active subtasks (if long list)

**Accessibility:**

- **ARIA Role**: `role="region"` with `aria-label="Task timeline visualization"`
- **Keyboard**: Arrow keys to navigate subtasks, Enter to expand
- **Screen Reader**: "Subtask 1, Create API endpoints, 100% complete by Claude Code. Subtask 2, Implement JWT logic, 50% in progress by Gemini CLI..."

---

#### **Custom Component 3: Checkpoint Decision Interface**

**Purpose:** Present checkpoint review with clear action buttons (Accept/Correct/Reject)

**Anatomy:**

```
┌─────────────────────────────────────────────────────┐
│ ⏸ CHECKPOINT REVIEW                                │ ← Header
├─────────────────────────────────────────────────────┤
│ [Summary section with What's Done / What's Next]    │ ← Context
├─────────────────────────────────────────────────────┤
│ [Evaluation Scores with visual indicators]          │ ← Quality Info
├─────────────────────────────────────────────────────┤
│ [Code Diff Preview]                                 │ ← Output Preview
├─────────────────────────────────────────────────────┤
│ Your Decision:                                      │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│ │ ✓ Accept │  │ 🔧 Correct│  │ ✗ Reject │          │
│ └──────────┘  └──────────┘  └──────────┘          │ ← Decision Buttons
└─────────────────────────────────────────────────────┘
```

**States:**

- **Default**: All three buttons enabled, no selection
- **Decision Made**: Selected button highlighted, others disabled, "Submitting..." state
- **Loading**: Evaluation scores loading (skeleton screens)
- **Error**: Failed to load checkpoint data (retry button)

**Variants:**

- **Simple**: Binary choice (Accept / Correct only) for low-priority checkpoints
- **Detailed**: Full view with all evaluation dimensions, code diffs, logs

**Behavior:**

- **Click "Accept"**: Immediately closes modal, task continues
- **Click "Correct"**: Transitions modal to Correction Interface (Journey 3)
- **Click "Reject"**: Shows confirmation dialog before canceling task

**Accessibility:**

- **ARIA Role**: `role="dialog"` with `aria-labelledby="checkpoint-title"`
- **Keyboard**: Tab to cycle through buttons, Enter to select, Escape to cancel (shows warning)
- **Screen Reader**: "Checkpoint review dialog. Task: Build user authentication system. Evaluation scores: Code Quality 8.5 out of 10, Completeness 7.0 out of 10 with warning..."

---

#### **Custom Component 4: Worker Health Monitor**

**Purpose:** Display machine resource usage (CPU, Memory, Disk) with visual indicators

**Anatomy:**

```
┌────────────────────────────────┐
│ Machine-1 (Desktop PC)    🟢   │ ← Header with status indicator
├────────────────────────────────┤
│ CPU:    ▓▓▓▓░░░░ 45%          │ ← Progress bar with percentage
│ Memory: ▓▓▓▓▓▓░░ 60%          │
│ Disk:   ▓▓░░░░░░ 30%          │
├────────────────────────────────┤
│ Heartbeat: 5 sec ago           │ ← Connection status
└────────────────────────────────┘
```

**States:**

- **Healthy**: Green indicator, all metrics < 75%
- **Warning**: Orange indicator, any metric 75-90%
- **Critical**: Red indicator, any metric > 90%
- **Offline**: Gray indicator, "Last seen X ago" text

**Variants:**

- **Compact**: Single line with icon indicators only (for lists)
- **Detailed**: Full metrics with historical chart (24-hour trend)

**Behavior:**

- **Hover**: Tooltip shows exact percentages and absolute values (e.g., "4GB / 8GB memory used")
- **Click**: Expands to show 24-hour resource usage chart

**Accessibility:**

- **ARIA Role**: `role="region"` with `aria-label="Worker health monitor for Machine-1"`
- **Keyboard**: Tab to focus, Enter to expand details
- **Screen Reader**: "Worker Machine-1, Desktop PC, status online. CPU usage 45%, Memory usage 60%, Disk usage 30%. Heartbeat 5 seconds ago."

---

#### **Custom Component 5: Evaluation Score Display**

**Purpose:** Show 5-dimensional quality scores with visual pass/fail indicators

**Anatomy:**

```
┌─────────────────────────────────────────────┐
│ Overall Quality Score: 8.5/10 ✓ GOOD        │ ← Header
├─────────────────────────────────────────────┤
│ Code Quality:        ▓▓▓▓▓▓▓▓▓░ 9.0/10 ✓    │
│ Completeness:        ▓▓▓▓▓▓▓░░░ 7.0/10 ⚠    │
│ Security:            ▓▓▓▓▓▓▓▓▓░ 9.0/10 ✓    │
│ Architecture:        ▓▓▓▓▓▓▓▓░░ 8.0/10 ✓    │
│ Testability:         ▓▓▓▓▓▓░░░░ 6.5/10 ⚠    │
└─────────────────────────────────────────────┘
```

**States:**

- **Excellent (9-10)**: Green bar, ✓ icon, "EXCELLENT" label
- **Good (7.5-8.9)**: Light green bar, ✓ icon, "GOOD" label
- **Acceptable (6-7.4)**: Yellow bar, ⚠ icon, "ACCEPTABLE" label
- **Poor (4-5.9)**: Orange bar, ⚠ icon, "NEEDS IMPROVEMENT" label
- **Fail (0-3.9)**: Red bar, ❌ icon, "FAIL" label
- **Loading**: Skeleton bars with animation

**Variants:**

- **Compact**: Overall score only (for cards)
- **Detailed**: Full breakdown with expand/collapse for each dimension's details

**Behavior:**

- **Click Dimension**: Expands to show detailed evaluation rationale (e.g., "Completeness 7.0: Missing error handling for edge case X")
- **Hover**: Tooltip shows score calculation formula

**Accessibility:**

- **ARIA Role**: `role="region"` with `aria-label="Evaluation scores"`
- **Keyboard**: Tab through dimensions, Enter to expand details
- **Screen Reader**: "Overall quality score 8.5 out of 10, good. Code Quality 9.0 out of 10, excellent. Completeness 7.0 out of 10, acceptable with warning, missing error handling..."

---

#### **Custom Component 6: Correction Feedback Form**

**Purpose:** Structured input for users to provide correction guidance to agents

**Anatomy:**

```
┌─────────────────────────────────────────────────────┐
│ Correction Type: (select one)                       │
│ ○ Wrong Approach  ● Incomplete  ○ Bug  ○ Other      │ ← Radio buttons
├─────────────────────────────────────────────────────┤
│ Specific Guidance: *                                │
│ ┌─────────────────────────────────────────────────┐ │
│ │ [Multi-line text input]                         │ │ ← Text area
│ │                                                 │ │
│ └─────────────────────────────────────────────────┘ │
│ 25 characters (min 10, recommended 50-200)          │ ← Character count
├─────────────────────────────────────────────────────┤
│ Reference Files: (optional)                         │
│ [+] Add file, link, or code example                 │ ← File upload
├─────────────────────────────────────────────────────┤
│ [ ] Apply this correction to similar future tasks   │ ← Checkbox
└─────────────────────────────────────────────────────┘
```

**States:**

- **Empty**: Guidance field empty, "Send Correction" button disabled
- **Valid**: Guidance >= 10 characters, button enabled
- **Submitting**: Button shows spinner, "Sending correction..."
- **Error**: Red border on guidance field, error message below

**Variants:**

- **Simple**: Only guidance text field (for quick corrections)
- **Advanced**: Full form with all options (type, references, learning mode)

**Behavior:**

- **Type in Guidance**: Character counter updates in real-time
- **Select Correction Type**: Optional, but helps system categorize issue
- **Add Reference File**: Opens file picker or URL input, shows thumbnail/preview
- **Submit**: Sends correction to backend, modal transitions to "Correction sent" state

**Accessibility:**

- **ARIA Role**: `role="form"` with `aria-label="Agent correction form"`
- **Keyboard**: Tab through all fields, Ctrl+Enter to submit
- **Screen Reader**: "Correction type, radio buttons. Specific guidance, required text area, currently 0 characters, minimum 10. Reference files, optional, add file button..."

---

### 6.2 Component Customization Strategy

**Material 3 Components Requiring Customization:**

1. **Card**: Add status border colors (green/orange/red/blue left border)
2. **ProgressIndicator**: Custom color mapping for evaluation scores (green/yellow/orange/red)
3. **SnackBar**: Custom variants for success/warning/error/info with icons
4. **DataTable**: Custom row coloring for agent status, expandable rows
5. **Modal (Dialog)**: Custom sizes (standard 640px, wide 960px, full-screen for mobile)

**Theming Approach:**

Use Flutter's `ThemeData` to customize Material 3:

```dart
ThemeData(
  colorScheme: ColorScheme.fromSeed(
    seedColor: Color(0xFF1976D2), // Primary blue
    secondary: Color(0xFF00897B),  // Teal
  ),
  useMaterial3: true,

  // Custom component themes
  cardTheme: CardTheme(
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(12),
      side: BorderSide(color: Colors.grey[300]!, width: 1),
    ),
  ),

  // Custom text theme (Roboto is Material default)
  textTheme: TextTheme(
    displayLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.w500),
    headlineMedium: TextStyle(fontSize: 24, fontWeight: FontWeight.w500),
    bodyLarge: TextStyle(fontSize: 16),
    // ... rest of type scale
  ),

  // Custom spacing via extensions
  extensions: <ThemeExtension<dynamic>>[
    CustomSpacing(xs: 4, sm: 8, md: 16, lg: 24, xl: 32),
  ],
);
```

---

## 7. UX Pattern Decisions

### 7.1 Consistency Rules

To ensure users get a consistent experience across the entire application, the following UX patterns are standardized:

---

#### **Button Hierarchy**

**Primary Action** (Most important, one per screen):
- **Style**: Filled button with primary color (`#1976D2`)
- **Usage**: "Submit Task," "Send Correction," "Accept" (at checkpoints)
- **Placement**: Right side of button groups, bottom-right of modals

**Secondary Action** (Supporting actions):
- **Style**: Outlined button with primary color border
- **Usage**: "View Details," "Pause Task," "Download Files"
- **Placement**: Left of primary action, or standalone if no primary exists

**Tertiary Action** (Low-priority, optional):
- **Style**: Text button (no background, no border)
- **Usage**: "Cancel," "Skip," "Load More"
- **Placement**: Far left of button groups

**Destructive Action** (Dangerous operations):
- **Style**: Filled button with error color (`#C62828`)
- **Usage**: "Reject Task," "Delete Worker," "Cancel"
- **Confirmation**: ALWAYS requires confirmation dialog before executing

---

#### **Feedback Patterns**

**Success Feedback**:
- **Pattern**: Toast notification (SnackBar) at bottom-center, 4-second duration
- **Usage**: "Task submitted successfully," "Worker connected," "Checkpoint approved"
- **Visual**: Green background, white text, checkmark icon

**Error Feedback**:
- **Pattern**: Toast notification (SnackBar) at bottom-center, 8-second duration (longer to read)
- **Usage**: "Task failed: Agent timeout," "Worker disconnected," "Invalid input"
- **Visual**: Red background, white text, X icon
- **Additional**: If form error, also show inline red text below problematic field

**Warning Feedback**:
- **Pattern**: Banner at top of screen (persistent until dismissed)
- **Usage**: "Worker Machine-1 is running at high CPU usage," "Evaluation score below threshold"
- **Visual**: Orange background, dark text, warning icon, dismiss button

**Info Feedback**:
- **Pattern**: Toast notification (SnackBar) at bottom-center, 4-second duration
- **Usage**: "Decomposing task into subtasks...," "Checkpoint in 2 minutes"
- **Visual**: Blue background, white text, info icon

**Loading Feedback**:
- **Pattern**:
  - **Inline**: Circular spinner next to element (for component-level loading like "Loading evaluation scores...")
  - **Full-screen**: Linear progress bar at top of page (for page-level loading like initial data fetch)
  - **Skeleton Screens**: For card lists and tables while data loads
- **Duration**: If loading > 2 seconds, show progress percentage if available

---

#### **Form Patterns**

**Label Position**: Above input field (Material 3 standard)
- Rationale: Better accessibility, easier to scan vertically

**Required Field Indicator**:
- **Visual**: Asterisk (*) after label (e.g., "Task Description: *")
- **Accessible**: `aria-required="true"` on input

**Validation Timing**:
- **On Submit**: Validate all fields when user clicks submit button
- **On Blur** (after first submit attempt): If field was invalid on submit, re-validate when user leaves field
- **Real-time** (for specific cases): Character count limits, password strength meter

**Error Display**:
- **Inline**: Red text below field with specific error message (e.g., "Task description must be at least 10 characters")
- **Summary**: If 3+ errors, show error summary banner at top of form: "Please fix 3 errors below"

**Help Text**:
- **Pattern**: Caption text below input field, gray color
- **Usage**: "Describe your task in natural language" (for Task Description field)
- **Tooltips**: For complex concepts, add (?) icon next to label that shows tooltip on hover/click

---

#### **Modal Patterns**

**Size Variants**:
- **Small (480px)**: Simple confirmations ("Are you sure?")
- **Standard (640px)**: Forms, checkpoint reviews, most dialogs
- **Wide (960px)**: Code diffs, side-by-side comparisons, detailed views
- **Full-screen (mobile <768px)**: All modals on mobile devices

**Dismiss Behavior**:
- **Click Outside**: Closes modal for non-critical actions (e.g., "View Details")
- **Confirmation Required**: For critical actions (e.g., "Submit Task"), clicking outside shows warning: "Discard changes?"
- **Escape Key**: Same behavior as clicking outside
- **Explicit Close**: Always provide X button in top-right corner

**Focus Management**:
- **Auto-focus**: First input field when modal opens (if form)
- **Return Focus**: When modal closes, focus returns to element that triggered it (e.g., "Submit Task" button)
- **Trap Focus**: Tab key cycles through modal elements only (doesn't escape to page behind)

**Stacking**:
- **Maximum**: 2 modals (e.g., Checkpoint Review → Correction Interface)
- **Visual**: Each stacked modal has darker backdrop (first: 60% opacity, second: 80% opacity)
- **Behavior**: Closing top modal reveals previous modal

---

#### **Navigation Patterns**

**Active State Indication**:
- **Visual**: Active nav item has primary color background (`#1976D2`), white text, and left border accent (4px)
- **Inactive Items**: Gray text, no background, hover shows light gray background

**Breadcrumb Usage**:
- **When Shown**: Only on deep pages (e.g., Task Details page)
- **Format**: `Dashboard > Tasks > Build user authentication system`
- **Behavior**: Clicking breadcrumb navigates to that level

**Back Button Behavior**:
- **Browser Back**: Supported (uses Flutter `go_router` with proper history management)
- **App Back**: Top-left "← Back" button on detail pages (e.g., Task Details)
- **Confirmation**: If user has unsaved changes, warn: "You have unsaved changes. Discard?"

**Deep Linking**:
- **Supported Patterns**:
  - `/dashboard` (main dashboard)
  - `/tasks/:taskId` (specific task details)
  - `/workers/:workerId` (specific worker details)
  - `/settings` (settings page)
- **Shareable URLs**: All pages have unique URLs that can be bookmarked or shared

---

#### **Empty State Patterns**

**First Use (No Data Yet)**:
- **Visual**: Large icon (200x200px), headline, description, primary CTA button
- **Example**: Dashboard with no tasks
  ```
  [Icon: Rocket launching]

  No active tasks yet

  Submit your first task to see AI agents work in parallel.
  Multi-agent orchestration makes complex projects 2-3x faster.

  [Submit New Task →]
  ```

**No Results (After Search/Filter)**:
- **Visual**: Smaller icon (100x100px), helpful message, CTA to clear filters
- **Example**: Worker list filtered to "Offline" but all workers are online
  ```
  [Icon: Magnifying glass]

  No offline workers found

  All your workers are currently online and healthy.

  [Clear Filters]
  ```

**Cleared Content (User Deleted Everything)**:
- **Visual**: Icon, message, undo option (if applicable), CTA to create new
- **Example**: User archived all completed tasks
  ```
  [Icon: Archive box]

  All tasks archived

  Your completed tasks have been moved to the archive.

  [View Archive]  [Submit New Task]
  ```

---

#### **Confirmation Patterns**

**Delete Actions**:
- **Always Confirm**: Show modal dialog: "Are you sure you want to delete this worker? This action cannot be undone."
- **High-Risk Deletes**: Require typing confirmation (e.g., type worker name to confirm)

**Leave Unsaved**:
- **When**: User tries to navigate away from form with unsaved changes
- **Pattern**: Modal dialog: "You have unsaved changes. Do you want to discard them?"
  - Options: "Discard Changes," "Continue Editing"

**Irreversible Actions**:
- **Pattern**: Confirmation modal with destructive action highlighted
- **Examples**: "Cancel Task" (stops all agents, discards progress), "Reject Checkpoint" (discards agent work)
- **Additional**: If action is very destructive, add 2-second countdown before confirm button enables

---

#### **Notification Patterns**

**Placement**:
- **Desktop**: Toast notifications at bottom-center
- **Mobile**: Toast notifications at top (easier to see with thumb position)

**Duration**:
- **Success/Info**: 4 seconds
- **Warning**: 6 seconds
- **Error**: 8 seconds (longer to read and understand)
- **Persistent**: Banner notifications (warnings, errors requiring action) stay until dismissed

**Stacking**:
- **Maximum Visible**: 3 toasts simultaneously
- **Queue**: Additional notifications queue and appear as earlier ones dismiss
- **Behavior**: Hovering a toast pauses its auto-dismiss timer

**Priority Levels**:
- **Critical**: Desktop notification + in-app modal (e.g., "All workers offline, cannot allocate tasks")
- **Important**: Desktop notification + in-app toast (e.g., "Checkpoint ready")
- **Info**: In-app toast only (e.g., "Task decomposed into 4 subtasks")

---

#### **Search Patterns**

**Trigger**:
- **Auto-search**: Typing in search box triggers search after 500ms debounce
- **Manual**: "Search" button also available for users who prefer explicit action

**Results Display**:
- **Instant**: Results update in real-time as user types (for small datasets like workers)
- **On Enter**: Results load after user presses Enter (for large datasets like task history)

**Filters**:
- **Placement**: Dropdown menus or chips above search results
- **Behavior**: Filters AND with search query (e.g., search "auth" AND filter "Completed" = completed tasks containing "auth")

**No Results**:
- **Message**: "No results found for '[query]'. Try different keywords or clear filters."
- **Suggestions**: Show recent searches or popular searches (if applicable)

---

#### **Date/Time Patterns**

**Format**:
- **Relative** (for recent times): "5 minutes ago," "2 hours ago," "Yesterday"
- **Absolute** (for older times): "2025-11-10 14:35" (YYYY-MM-DD HH:MM)
- **Switch Threshold**: Use relative for < 7 days, absolute for >= 7 days

**Timezone Handling**:
- **Display**: All times shown in user's local timezone
- **Storage**: All times stored in backend as UTC
- **Indication**: Tooltip on timestamp shows timezone (e.g., "2025-11-11 12:45 PST")

**Pickers**:
- **Date Picker**: Material calendar picker (opens modal)
- **Time Picker**: Material time picker (12-hour or 24-hour based on locale)
- **Date Range Picker**: Two calendars side-by-side (for filtering task history)

---

## 8. Responsive Design & Accessibility

### 8.1 Responsive Strategy

---

#### **Breakpoints**

| Breakpoint | Range | Target Devices | Layout Adaptation |
|------------|-------|----------------|-------------------|
| **Mobile** | < 768px | Phones | Single column, bottom nav, full-width cards |
| **Tablet** | 768px - 1024px | iPads, Android tablets | 2-column, collapsible sidebar, adaptive cards |
| **Desktop** | 1024px - 1920px | Laptops, standard monitors | 3-column, persistent sidebar, grid layouts |
| **Large Desktop** | > 1920px | 4K monitors, ultrawide | 3-column with max-width constraints (1920px), centered content |

---

#### **Navigation Adaptation**

**Desktop (>= 1024px):**
- **Pattern**: Left sidebar navigation (240px width), always visible
- **Items**: Dashboard, Tasks, Workers, Settings (with icons + labels)
- **Behavior**: Active item highlighted, hover shows tooltip for long labels

**Tablet (768-1024px):**
- **Pattern**: Collapsible sidebar (60px collapsed, 240px expanded)
- **Items**: Icons only when collapsed, icons + labels when expanded
- **Behavior**: Tap hamburger icon to expand/collapse

**Mobile (< 768px):**
- **Pattern**: Bottom navigation bar (56px height)
- **Items**: 4 primary destinations (Dashboard, Tasks, Workers, Settings) with icons + labels
- **Behavior**: Tap icon to navigate, current page highlighted

---

#### **Content Layout Adaptation**

**Dashboard:**

- **Desktop (1920x1080):**
  ```
  ┌──────┬─────────────────────────────┬─────────┐
  │ Nav  │   Main Content              │ Activity│
  │ (240)│   - Active Tasks (cards)    │  Panel  │
  │      │   - Timeline Visualizer     │  (320)  │
  │      │   - Worker Summary          │         │
  └──────┴─────────────────────────────┴─────────┘
  ```

- **Tablet (1024x768):**
  ```
  ┌────┬──────────────────────────────────────┐
  │Nav │   Main Content + Tabs                │
  │(60)│   - Active Tasks                     │
  │    │   - Timeline                         │
  │    │   [Activity Tab] [Workers Tab]       │
  └────┴──────────────────────────────────────┘
  ```

- **Mobile (375x667):**
  ```
  ┌────────────────────────────────────────────┐
  │           Active Tasks (Stacked)           │
  │           - Task Card 1                    │
  │           - Task Card 2                    │
  │                                            │
  │           [Activity Feed Tab]              │
  └────────────────────────────────────────────┘
  ┌──────┬──────┬──────┬──────────────────────┐
  │Dash  │Tasks │Workers│Settings              │
  └──────┴──────┴──────┴──────────────────────┘
  ```

**Cards:**

- **Desktop**: 3-column grid (for worker cards), 2-column for large task cards
- **Tablet**: 2-column grid
- **Mobile**: Single column, full width

**Modals:**

- **Desktop/Tablet**: Fixed width (640px standard, 960px wide), centered with backdrop
- **Mobile**: Full-screen modal (covers entire viewport), slide-up animation

**Tables (if applicable):**

- **Desktop**: Standard table with all columns visible
- **Tablet**: Hide non-essential columns (e.g., hide "Last Heartbeat" column in Workers table)
- **Mobile**: Convert to card view (each row becomes a card with vertical layout)

---

#### **Touch Target Sizes**

Following Material Design and WCAG 2.1 guidelines:

**Minimum Touch Target Size**: 48x48 dp (density-independent pixels)

**Application:**
- **Buttons**: Minimum 48px height (even if text is smaller, clickable area is 48px)
- **Icons**: 24x24px visual size, but 48x48px tap area (padding around icon)
- **List Items**: Minimum 56px height for single-line items, 72px for two-line
- **Checkboxes/Radio**: 24x24px visual size, 48x48px tap area

**Spacing Between Touch Targets**: Minimum 8px gap to prevent accidental taps

---

### 8.2 Accessibility Strategy

---

#### **WCAG Compliance Level**

**Target:** **WCAG 2.1 Level AA**

**Rationale:**
- This is a developer tool, likely to be used in professional and educational contexts
- Level AA is the legally required standard for most public-facing and enterprise software
- Level AA is achievable for this application without compromising design vision
- Level AAA would impose unnecessary constraints (e.g., 7:1 contrast ratios are too restrictive for some UI elements)

---

#### **Key Accessibility Requirements**

---

##### **1. Color Contrast**

**Minimum Ratios (WCAG AA):**
- **Normal Text** (< 18pt or < 14pt bold): 4.5:1 contrast ratio
- **Large Text** (>= 18pt or >= 14pt bold): 3:1 contrast ratio
- **UI Components & Graphics**: 3:1 contrast ratio

**Application:**

| Element | Foreground | Background | Ratio | Pass |
|---------|------------|------------|-------|------|
| Body text | `#212121` | `#FFFFFF` | 16.1:1 | ✓ AAA |
| Primary button text | `#FFFFFF` | `#1976D2` | 4.7:1 | ✓ AA |
| Success status text | `#2E7D32` | `#FFFFFF` | 8.2:1 | ✓ AAA |
| Error status text | `#C62828` | `#FFFFFF` | 6.8:1 | ✓ AAA |
| Secondary text | `#616161` | `#FFFFFF` | 7.1:1 | ✓ AAA |

**Tools for Validation:**
- Chrome DevTools Lighthouse (automated scanning)
- WebAIM Contrast Checker
- Built-in Flutter contrast checks during development

---

##### **2. Keyboard Navigation**

**All Interactive Elements Accessible via Keyboard:**

- **Tab**: Move forward through interactive elements
- **Shift+Tab**: Move backward
- **Enter/Space**: Activate buttons, checkboxes, links
- **Arrow Keys**: Navigate within components (e.g., radio button groups, timeline subtasks)
- **Escape**: Close modals, dropdowns, cancel actions

**Focus Indicators:**

- **Visual**: 2px solid primary color (`#1976D2`) border around focused element
- **Offset**: 2px gap between element and focus border (for clarity)
- **Persistence**: Focus indicator remains visible until focus moves (not hidden on mouse click)

**Focus Management:**

- **Modal Open**: Focus moves to first interactive element in modal (or modal close button if no inputs)
- **Modal Close**: Focus returns to trigger element (e.g., button that opened modal)
- **Page Load**: Focus moves to main content area (skip to content link available)

**Tab Order:**

- **Logical Flow**: Top-to-bottom, left-to-right (matches visual layout)
- **No Tab Traps**: Users can always tab out of any component
- **Skip Links**: "Skip to main content" link at top of page (visible on focus) for screen reader users

---

##### **3. ARIA Labels and Roles**

**Semantic HTML + ARIA Enhancement:**

All components use semantic HTML as foundation (e.g., `<button>`, `<nav>`, `<main>`), enhanced with ARIA when needed.

**Key ARIA Attributes:**

| Element | ARIA Role | ARIA Label/Description |
|---------|-----------|------------------------|
| Dashboard | `role="main"` | `aria-label="Dashboard - Multi-Agent on the Web"` |
| Nav Sidebar | `role="navigation"` | `aria-label="Main navigation"` |
| Task Card | `role="article"` | `aria-labelledby="task-title-123"` |
| Agent Status | `role="status"` | `aria-live="polite"` (for real-time updates) |
| Progress Bar | `role="progressbar"` | `aria-valuenow="60" aria-valuemin="0" aria-valuemax="100"` |
| Checkpoint Modal | `role="dialog"` | `aria-labelledby="checkpoint-title" aria-describedby="checkpoint-desc"` |
| Close Button | `role="button"` | `aria-label="Close dialog"` |

**Live Regions for Real-Time Updates:**

- **Agent Status Changes**: `aria-live="polite"` (announces "Agent completed subtask" without interrupting)
- **Error Notifications**: `aria-live="assertive"` (immediately announces critical errors)
- **Progress Updates**: `aria-live="polite"` (announces "Task progress 75%")

---

##### **4. Screen Reader Support**

**Testing Tools:**
- **NVDA** (Windows, free)
- **JAWS** (Windows, industry standard)
- **VoiceOver** (macOS, iOS, built-in)
- **TalkBack** (Android, built-in)

**Screen Reader Experience Examples:**

**Dashboard:**
```
"Dashboard - Multi-Agent on the Web, main region.
Active tasks: 1 article.
Build user authentication system, 45% complete.
3 agents working.
4 minutes elapsed.
Subtask 1: Create API endpoints, 85% complete by Claude Code.
Subtask 2: Implement JWT logic, 50% complete by Gemini CLI.
Checkpoint in 2 minutes."
```

**Checkpoint Modal:**
```
"Checkpoint review dialog.
Task: Build user authentication system.
What's been completed: Subtask 1 and Subtask 2.
Evaluation scores:
Code Quality 8.5 out of 10, good.
Completeness 7.0 out of 10, warning, missing error handling.
Your decision: 3 buttons.
Accept button.
Correct button.
Reject button."
```

**Worker Card:**
```
"Worker article.
Machine-1, Desktop PC, status online.
CPU usage 45%, Memory usage 60%, Disk usage 30%.
Tools: Claude Code, Gemini CLI.
Current task: Subtask 1.
Heartbeat 5 seconds ago.
Details button. Pause button."
```

---

##### **5. Form Accessibility**

**Labels:**
- All input fields have associated `<label>` elements (linked via `for` attribute)
- Labels are always visible (not placeholders, which disappear when typing)

**Error Messaging:**
- Errors announced via `aria-describedby` linking input to error message
- Error messages are specific (not just "Invalid input" but "Task description must be at least 10 characters")

**Required Fields:**
- Marked with asterisk (*) in label AND `aria-required="true"` attribute
- Error summary lists all required fields if user submits incomplete form

**Help Text:**
- Associated with input via `aria-describedby`
- Available before user interacts (not hidden in tooltip that requires hover)

---

##### **6. Alternative Text**

**Images:**
- All images have `alt` text
- Decorative images (e.g., background patterns) have `alt=""` (announced as decorative by screen readers)

**Icons:**
- Functional icons (buttons) have `aria-label` (e.g., `aria-label="Close dialog"` for X button)
- Decorative icons (next to text labels) have `aria-hidden="true"`

**Charts/Visualizations:**
- Timeline visualizer has text equivalent (list of subtasks with progress)
- Resource usage charts have data table alternative (accessible via "View Data Table" link)

---

##### **7. Motion and Animation**

**Respect User Preferences:**

- Detect `prefers-reduced-motion` media query
- If user has reduced motion enabled, disable all non-essential animations:
  - Progress bar pulsing animation → static progress bar
  - Slide-in modals → instant appear
  - Fade transitions → instant state changes
- Critical animations (e.g., loading spinners indicating system is working) remain, but simplified

**Default Animation Timing:**
- **Fast**: 200ms (hover states, button clicks)
- **Medium**: 300ms (modal open/close, page transitions)
- **Slow**: 500ms (complex state changes, charts)

---

#### **8.3 Accessibility Testing Plan**

**Automated Testing:**
- **Tool**: Lighthouse (Chrome DevTools) - Run on every major component
- **Frequency**: Before every release, integrated into CI/CD pipeline
- **Pass Criteria**: Lighthouse Accessibility score >= 95/100

**Manual Testing:**
- **Keyboard Navigation**: Test all user journeys (Journeys 1-5) using keyboard only
- **Screen Reader**: Test critical flows with NVDA (Windows) and VoiceOver (macOS)
- **Contrast**: Validate all text and UI components meet 4.5:1 ratio (WebAIM Contrast Checker)
- **Focus Indicators**: Verify focus is always visible and in logical order

**User Testing:**
- **Recruit**: 2-3 users with accessibility needs (keyboard-only users, screen reader users)
- **Tasks**: Complete core workflows (submit task, respond to checkpoint, review results)
- **Feedback**: Identify pain points and iterate

---

## 9. Implementation Guidance

### 9.1 Completion Summary

**What We Created Together:**

1. **Design System**: Material Design 3 for Flutter with 6 custom domain-specific components
2. **Visual Foundation**: "Trust & Efficiency" color theme (professional blues and teals) with comprehensive typography (Roboto) and 8px spacing system
3. **Design Direction**: "Mission Control Dashboard" - balanced density, card-based, real-time data streams
4. **Novel UX Patterns**: 2 innovative patterns:
   - Real-Time Multi-Agent Orchestration Dashboard (parallel agent visualization)
   - Inline Agent Correction with Feedback Loop (contextual AI correction)
5. **User Journeys**: 5 complete flows with BDD-style step-by-step flows, error states, and accessibility notes:
   - Submit Task and Monitor Execution
   - Respond to Checkpoint
   - Correct Agent Work
   - Review Completed Task
   - Manage Workers
6. **UX Pattern Decisions**: 10 consistency rule categories (buttons, feedback, forms, modals, navigation, empty states, confirmations, notifications, search, date/time)
7. **Component Library**: 6 custom components fully specified (Agent Status Card, Task Timeline, Checkpoint Interface, Worker Health Monitor, Evaluation Display, Correction Form)
8. **Responsive Strategy**: 4 breakpoints (mobile/tablet/desktop/large desktop) with adaptive layouts
9. **Accessibility**: WCAG 2.1 Level AA compliance with keyboard navigation, screen reader support, color contrast validation

---

**Your Deliverables:**

- **UX Design Specification**: `docs/ux-design-specification.md` (this document)
- **Interactive Color Themes**: `docs/ux-color-themes.html` (to be generated)
- **Design Direction Mockups**: `docs/ux-design-directions.html` (to be generated)

---

**What Happens Next:**

Based on the BMAD workflow, the recommended next steps are:

1. **Generate Interactive Visualizations** (optional, recommended):
   - Color theme HTML visualizer with live component examples
   - Design direction mockups (6-8 full-screen mockups of key screens)

2. **Validate UX Design** (recommended):
   - Run UX design validation checklist
   - Ensure all 5 user journeys are complete and consistent

3. **Create Technical Architecture** (required before implementation):
   - Run `*create-architecture` workflow with Architect agent
   - Technical architecture will reference this UX design for frontend implementation

4. **Begin Implementation** (after architecture):
   - Sprint planning with Scrum Master agent
   - Development with Dev agent using this UX spec as reference

---

### 9.2 Developer Handoff Notes

**For Frontend Developers (Flutter):**

This UX specification provides:

1. **Component Specifications**: All 6 custom components have detailed anatomy, states, variants, behavior, and accessibility requirements. Use these as implementation blueprints.

2. **User Journey Flows**: Each flow step specifies:
   - What the user sees (UI mockup descriptions)
   - What the user does (interactions)
   - What the system responds (state changes, API calls, navigation)
   - Use these as acceptance criteria for features

3. **Design Tokens**: All colors, typography, spacing defined. Create Flutter theme constants file:
   ```dart
   // colors.dart
   class AppColors {
     static const primary = Color(0xFF1976D2);
     static const secondary = Color(0xFF00897B);
     static const success = Color(0xFF2E7D32);
     // ... etc
   }

   // typography.dart
   class AppTextStyles {
     static const h1 = TextStyle(fontSize: 32, fontWeight: FontWeight.w500);
     // ... etc
   }

   // spacing.dart
   class AppSpacing {
     static const xs = 4.0;
     static const sm = 8.0;
     static const md = 16.0;
     // ... etc
   }
   ```

4. **Accessibility Requirements**: Every component has ARIA roles, keyboard navigation, and screen reader announcements specified. Implement these using Flutter's `Semantics` widget.

5. **Responsive Breakpoints**: Defined breakpoints and layout adaptations. Use `LayoutBuilder` and `MediaQuery` to implement responsive designs.

**For Backend Developers (FastAPI):**

This UX specification implies several backend requirements:

1. **Real-Time Updates**: WebSocket connections needed for:
   - Agent status changes (every 2-3 seconds)
   - Task progress updates
   - Worker heartbeat status
   - Activity log events

2. **API Endpoints** (inferred from user journeys):
   - `POST /api/v1/tasks` - Submit new task
   - `GET /api/v1/tasks/:id` - Get task details
   - `POST /api/v1/tasks/:id/checkpoint/approve` - Approve checkpoint
   - `POST /api/v1/tasks/:id/checkpoint/correct` - Submit correction
   - `POST /api/v1/tasks/:id/cancel` - Cancel task
   - `GET /api/v1/workers` - List all workers
   - `POST /api/v1/workers` - Register new worker
   - `GET /api/v1/workers/:id` - Worker details
   - ... (see PRD for full API spec)

3. **Evaluation Framework**: Backend must calculate 5-dimensional scores:
   - Code Quality
   - Completeness
   - Security
   - Architecture Alignment
   - Testability
   - Aggregate to overall score (weighted average)

4. **Checkpoint Logic**: Backend determines when to trigger checkpoints based on:
   - User-configured frequency (low/medium/high)
   - Evaluation scores (auto-trigger if any dimension < 7.0)
   - Task complexity (trigger before major milestones)

5. **Correction Feedback Loop**: Backend must:
   - Send correction package to agent (original task, previous attempt, user guidance, evaluation scores)
   - Track correction history in task metadata
   - Support "learning mode" (apply correction pattern to future similar tasks)

**For UX Designers (if high-fidelity mockups needed):**

This specification provides:

1. **Design Direction**: "Mission Control Dashboard" with all visual style decisions (density, hierarchy, interaction patterns, visual weight)

2. **Color System**: Complete palette with hex codes, semantic colors, agent-specific colors

3. **Typography System**: Roboto font family with full type scale (H1-H6, body, caption)

4. **Component Library**: 6 custom components with anatomy diagrams and state specifications

5. **Screen Layouts**: Detailed layouts for Dashboard, Task Details, Worker Management, Checkpoint Modal, Correction Interface

**Next Steps for Designers:**
- Create high-fidelity mockups in Figma/Adobe XD using this specification
- Use provided color palette and typography system
- Follow specified component anatomy and states
- Reference user journey flows for screen sequences

---

## Appendix

### Related Documents

- **Product Requirements**: `docs/PRD.md`
- **Product Brief**: `docs/product-brief-Multi-Agent-on-the-web-2025-11-11.md`
- **Brainstorming Session**: `docs/bmm-brainstorming-session-2025-11-11.md`
- **Epic Breakdown**: `docs/epics.md`

### Core Interactive Deliverables

This UX Design Specification was created through visual collaboration and analysis of project requirements. The following interactive deliverables will be generated:

- **Color Theme Visualizer**: `docs/ux-color-themes.html`
  - Interactive HTML showing all color theme options
  - Live UI component examples in light and dark modes
  - Side-by-side comparison and semantic color usage documentation

- **Design Direction Mockups**: `docs/ux-design-directions.html`
  - Interactive HTML with 6-8 complete design approaches
  - Full-screen mockups of key screens (Dashboard, Checkpoint, Task Details, Worker Management)
  - Design philosophy and rationale for the "Mission Control Dashboard" direction

### Next Steps & Follow-Up Workflows

This UX Design Specification can serve as input to:

1. **Solution Architecture Workflow** (`*create-architecture`) - Define technical architecture with UX context
2. **Wireframe Generation Workflow** - Create detailed wireframes from user flows
3. **Interactive Prototype Workflow** - Build clickable HTML/Flutter prototypes
4. **Component Showcase Workflow** - Create interactive component library documentation
5. **Sprint Planning Workflow** (`*sprint-planning`) - Break down Epic stories into implementation tasks

### Version History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-11 | 1.0 | Initial UX Design Specification | sir |

---

_This UX Design Specification was created through collaborative design facilitation based on PRD analysis, product brief vision, and Epic breakdown requirements. All decisions are documented with rationale aligned to project goals: 2-3x speed improvement, 4-layer quality assurance, real-time visualization, and human-in-the-loop control._
