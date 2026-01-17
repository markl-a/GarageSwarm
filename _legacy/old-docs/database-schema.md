# Multi-Agent on the Web - Database Schema

This document describes the complete PostgreSQL database schema for the Multi-Agent Orchestration Platform.

## Table of Contents

1. [Entity Relationship Diagram](#entity-relationship-diagram)
2. [Core Tables](#core-tables)
3. [Table Relationships](#table-relationships)
4. [Indexes and Performance](#indexes-and-performance)
5. [Data Types and Constraints](#data-types-and-constraints)

---

## Entity Relationship Diagram

```
┌─────────────────┐
│     users       │
│─────────────────│
│ PK user_id      │
│    username     │
│    email        │
│    password_hash│
│    created_at   │
│    last_login   │
└────────┬────────┘
         │
         │ 1:N
         │
         ▼
┌─────────────────────────────────────┐           ┌─────────────────┐
│             tasks                   │           │    workers      │
│─────────────────────────────────────│           │─────────────────│
│ PK task_id                          │           │ PK worker_id    │
│ FK user_id                          │           │    machine_id   │
│    description                      │           │    machine_name │
│    status                           │           │    status       │
│    progress                         │           │    system_info  │
│    checkpoint_frequency             │           │    tools        │
│    privacy_level                    │           │    cpu_percent  │
│    tool_preferences                 │           │    memory_percent│
│    metadata                         │           │    disk_percent │
│    version (optimistic lock)        │           │    last_heartbeat│
│    created_at, updated_at           │           │    registered_at│
│    started_at, completed_at         │           └────────┬────────┘
└────────┬────────────────────────────┘                    │
         │                                                  │
         │ 1:N                                             │
         │                                                  │
         ▼                                                  │
┌─────────────────────────────────────┐                   │
│            subtasks                 │                   │
│─────────────────────────────────────│                   │
│ PK subtask_id                       │                   │
│ FK task_id                          │◄──────────────────┘
│ FK assigned_worker                  │        1:N
│    name                             │
│    description                      │
│    status                           │
│    progress                         │
│    dependencies (JSONB array)       │
│    recommended_tool                 │
│    assigned_tool                    │
│    complexity                       │
│    priority                         │
│    output (JSONB)                   │
│    error                            │
│    created_at, started_at           │
│    completed_at                     │
└────────┬────────────────────────────┘
         │
         │ 1:N
         │
         ├─────────────────┬───────────────────┐
         │                 │                   │
         ▼                 ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ evaluations  │  │ corrections  │  │  checkpoints     │
│──────────────│  │──────────────│  │──────────────────│
│PK eval_id    │  │PK corr_id    │  │PK checkpoint_id  │
│FK subtask_id │  │FK checkpoint │  │FK task_id        │
│  code_quality│  │FK subtask_id │  │  status          │
│  completeness│  │  corr_type   │  │  subtasks_completed│
│  security    │  │  guidance    │  │  user_decision   │
│  architecture│  │  ref_files   │  │  decision_notes  │
│  testability │  │  result      │  │  triggered_at    │
│  overall_score│  │  retry_count │  │  reviewed_at     │
│  details     │  │  apply_future│  │                  │
│  evaluated_at│  │  created_at  │  └──────────────────┘
└──────────────┘  │  resolved_at │
                  └──────────────┘

┌─────────────────────────────────────┐
│         activity_logs               │
│─────────────────────────────────────│
│ PK log_id (BIGSERIAL)               │
│ FK task_id                          │
│ FK subtask_id                       │
│ FK worker_id                        │
│    level (info/warning/error)       │
│    message                          │
│    metadata (JSONB)                 │
│    created_at                       │
└─────────────────────────────────────┘
```

---

## Core Tables

### 1. users

**Purpose:** User authentication and management (Future feature - MVP uses simple auth)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique user identifier |
| username | VARCHAR(50) | UNIQUE, NOT NULL | Username for login |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| password_hash | VARCHAR(255) | NOT NULL | Hashed password (bcrypt) |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Account creation time |
| last_login | TIMESTAMP WITH TIME ZONE | NULL | Last login timestamp |

**Indexes:**
- `idx_users_email` ON (email)

**SQL Definition:**
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
```

---

### 2. workers

**Purpose:** Track registered Worker Agents, their capabilities, and real-time resource usage

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| worker_id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique worker identifier |
| machine_id | VARCHAR(100) | UNIQUE, NOT NULL | Physical machine identifier |
| machine_name | VARCHAR(100) | NOT NULL | Human-readable machine name |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'offline', CHECK | Worker status: online, offline, busy |
| system_info | JSONB | NOT NULL | {os, cpu, memory_total_gb, disk_total_gb} |
| tools | JSONB | NOT NULL | ["claude_code", "gemini_cli", "ollama"] |
| cpu_percent | FLOAT | NULL | Current CPU usage (0-100) |
| memory_percent | FLOAT | NULL | Current memory usage (0-100) |
| disk_percent | FLOAT | NULL | Current disk usage (0-100) |
| last_heartbeat | TIMESTAMP WITH TIME ZONE | NULL | Last heartbeat received |
| registered_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Registration time |

**Indexes:**
- `idx_workers_status` ON (status)
- `idx_workers_last_heartbeat` ON (last_heartbeat)

**SQL Definition:**
```sql
CREATE TABLE workers (
    worker_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id VARCHAR(100) UNIQUE NOT NULL,
    machine_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'offline',
    system_info JSONB NOT NULL,
    tools JSONB NOT NULL,
    cpu_percent FLOAT,
    memory_percent FLOAT,
    disk_percent FLOAT,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_status CHECK (status IN ('online', 'offline', 'busy'))
);

CREATE INDEX idx_workers_status ON workers(status);
CREATE INDEX idx_workers_last_heartbeat ON workers(last_heartbeat);
```

---

### 3. tasks

**Purpose:** Main task submissions from users, tracking overall progress and status

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| task_id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique task identifier |
| user_id | UUID | FOREIGN KEY REFERENCES users(user_id) | Task owner |
| description | TEXT | NOT NULL | Natural language task description |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending', CHECK | Task status |
| progress | INTEGER | DEFAULT 0, CHECK (0-100) | Overall progress percentage |
| checkpoint_frequency | VARCHAR(20) | NOT NULL, DEFAULT 'medium' | low, medium, high |
| privacy_level | VARCHAR(20) | NOT NULL, DEFAULT 'normal' | normal, sensitive |
| tool_preferences | JSONB | NULL | ["claude_code", "gemini_cli"] |
| metadata | JSONB | NULL | Flexible metadata storage |
| version | INTEGER | NOT NULL, DEFAULT 0 | Optimistic locking version |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Task creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Last update time |
| started_at | TIMESTAMP WITH TIME ZONE | NULL | Task execution start time |
| completed_at | TIMESTAMP WITH TIME ZONE | NULL | Task completion time |

**Valid Status Values:**
- `pending` - Task submitted, awaiting decomposition
- `initializing` - Task being decomposed into subtasks
- `in_progress` - Subtasks are being executed
- `checkpoint` - Paused for human review
- `completed` - All subtasks completed successfully
- `failed` - Task execution failed
- `cancelled` - User cancelled the task

**Indexes:**
- `idx_tasks_user` ON (user_id)
- `idx_tasks_status` ON (status)
- `idx_tasks_created_at` ON (created_at DESC)
- `idx_tasks_status_version` ON (task_id, status, version) - For optimistic locking

**SQL Definition:**
```sql
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    checkpoint_frequency VARCHAR(20) NOT NULL DEFAULT 'medium',
    privacy_level VARCHAR(20) NOT NULL DEFAULT 'normal',
    tool_preferences JSONB,
    metadata JSONB,
    version INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_task_status CHECK (status IN ('pending', 'initializing', 'in_progress', 'checkpoint', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_tasks_user ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_status_version ON tasks(task_id, status, version);
```

---

### 4. subtasks

**Purpose:** Decomposed subtasks from main tasks, forming a DAG (Directed Acyclic Graph)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| subtask_id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique subtask identifier |
| task_id | UUID | FOREIGN KEY REFERENCES tasks(task_id) ON DELETE CASCADE | Parent task |
| name | VARCHAR(255) | NOT NULL | Short subtask name |
| description | TEXT | NOT NULL | Detailed subtask description |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending', CHECK | Subtask status |
| progress | INTEGER | DEFAULT 0, CHECK (0-100) | Subtask progress percentage |
| dependencies | JSONB | DEFAULT '[]' | [uuid1, uuid2] - Dependency subtask IDs |
| recommended_tool | VARCHAR(50) | NULL | Recommended AI tool |
| assigned_worker | UUID | FOREIGN KEY REFERENCES workers(worker_id) | Assigned worker |
| assigned_tool | VARCHAR(50) | NULL | Actually assigned tool |
| complexity | INTEGER | CHECK (1-5) | Complexity rating (1=simple, 5=complex) |
| priority | INTEGER | DEFAULT 0 | Priority score (higher = more urgent) |
| output | JSONB | NULL | {text: "...", files: [...], usage: {...}} |
| error | TEXT | NULL | Error message if failed |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Subtask creation time |
| started_at | TIMESTAMP WITH TIME ZONE | NULL | Execution start time |
| completed_at | TIMESTAMP WITH TIME ZONE | NULL | Completion time |

**Valid Status Values:**
- `pending` - Not yet ready (dependencies incomplete)
- `queued` - Ready to be assigned to a worker
- `in_progress` - Currently being executed by a worker
- `completed` - Successfully completed
- `failed` - Execution failed
- `correcting` - Being corrected after checkpoint feedback

**Indexes:**
- `idx_subtasks_task` ON (task_id)
- `idx_subtasks_status` ON (status)
- `idx_subtasks_worker` ON (assigned_worker)

**SQL Definition:**
```sql
CREATE TABLE subtasks (
    subtask_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    dependencies JSONB DEFAULT '[]',
    recommended_tool VARCHAR(50),
    assigned_worker UUID REFERENCES workers(worker_id),
    assigned_tool VARCHAR(50),
    complexity INTEGER CHECK (complexity >= 1 AND complexity <= 5),
    priority INTEGER DEFAULT 0,
    output JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_subtask_status CHECK (status IN ('pending', 'queued', 'in_progress', 'completed', 'failed', 'correcting'))
);

CREATE INDEX idx_subtasks_task ON subtasks(task_id);
CREATE INDEX idx_subtasks_status ON subtasks(status);
CREATE INDEX idx_subtasks_worker ON subtasks(assigned_worker);
```

---

### 5. checkpoints

**Purpose:** Quality checkpoints for human review and decision-making

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| checkpoint_id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique checkpoint identifier |
| task_id | UUID | FOREIGN KEY REFERENCES tasks(task_id) ON DELETE CASCADE | Related task |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending_review', CHECK | Checkpoint status |
| subtasks_completed | JSONB | NOT NULL | [uuid1, uuid2] - Completed subtask IDs |
| user_decision | VARCHAR(20) | NULL | approve, correct, reject |
| decision_notes | TEXT | NULL | User's notes/feedback |
| triggered_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Checkpoint trigger time |
| reviewed_at | TIMESTAMP WITH TIME ZONE | NULL | User review time |

**Valid Status Values:**
- `pending_review` - Awaiting user review
- `approved` - User approved, continue execution
- `corrected` - Corrections applied, resume
- `rejected` - User rejected, task failed

**Indexes:**
- `idx_checkpoints_task` ON (task_id)
- `idx_checkpoints_status` ON (status)

**SQL Definition:**
```sql
CREATE TABLE checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending_review',
    subtasks_completed JSONB NOT NULL,
    user_decision VARCHAR(20),
    decision_notes TEXT,
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_checkpoint_status CHECK (status IN ('pending_review', 'approved', 'corrected', 'rejected'))
);

CREATE INDEX idx_checkpoints_task ON checkpoints(task_id);
CREATE INDEX idx_checkpoints_status ON checkpoints(status);
```

---

### 6. corrections

**Purpose:** Store correction instructions from checkpoints for subtask rework

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| correction_id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique correction identifier |
| checkpoint_id | UUID | FOREIGN KEY REFERENCES checkpoints(checkpoint_id) ON DELETE CASCADE | Related checkpoint |
| subtask_id | UUID | FOREIGN KEY REFERENCES subtasks(subtask_id) | Subtask to correct |
| correction_type | VARCHAR(20) | NOT NULL, CHECK | Type of correction needed |
| guidance | TEXT | NOT NULL | Correction instructions |
| reference_files | JSONB | DEFAULT '[]' | Reference files or links |
| result | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | Correction result |
| retry_count | INTEGER | DEFAULT 0 | Number of retry attempts |
| apply_to_future | BOOLEAN | DEFAULT FALSE | Apply to future similar tasks |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Correction creation time |
| resolved_at | TIMESTAMP WITH TIME ZONE | NULL | Correction resolution time |

**Valid Correction Types:**
- `wrong_approach` - Incorrect technical approach
- `incomplete` - Missing requirements
- `bug` - Bugs or errors
- `style` - Code style issues
- `missing_feature` - Missing functionality
- `other` - Other issues

**Indexes:**
- `idx_corrections_checkpoint` ON (checkpoint_id)
- `idx_corrections_subtask` ON (subtask_id)

**SQL Definition:**
```sql
CREATE TABLE corrections (
    correction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checkpoint_id UUID NOT NULL REFERENCES checkpoints(checkpoint_id) ON DELETE CASCADE,
    subtask_id UUID NOT NULL REFERENCES subtasks(subtask_id),
    correction_type VARCHAR(20) NOT NULL,
    guidance TEXT NOT NULL,
    reference_files JSONB DEFAULT '[]',
    result VARCHAR(20) NOT NULL DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    apply_to_future BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_correction_type CHECK (correction_type IN ('wrong_approach', 'incomplete', 'bug', 'style', 'missing_feature', 'other'))
);

CREATE INDEX idx_corrections_checkpoint ON corrections(checkpoint_id);
CREATE INDEX idx_corrections_subtask ON corrections(subtask_id);
```

---

### 7. evaluations

**Purpose:** Store automated evaluation results for subtask quality assessment

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| evaluation_id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique evaluation identifier |
| subtask_id | UUID | FOREIGN KEY REFERENCES subtasks(subtask_id) ON DELETE CASCADE | Evaluated subtask |
| code_quality | DECIMAL(3,1) | CHECK (0-10) | Code quality score |
| completeness | DECIMAL(3,1) | CHECK (0-10) | Completeness score |
| security | DECIMAL(3,1) | CHECK (0-10) | Security score |
| architecture | DECIMAL(3,1) | CHECK (0-10) | Architecture alignment score |
| testability | DECIMAL(3,1) | CHECK (0-10) | Testability score |
| overall_score | DECIMAL(3,1) | CHECK (0-10) | Weighted average score |
| details | JSONB | NULL | Detailed evaluation results |
| evaluated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Evaluation time |

**Score Weighting:**
- Security: 2.0x weight
- Code Quality: 1.5x weight
- Completeness: 1.5x weight
- Architecture: 1.0x weight
- Testability: 1.0x weight

**Indexes:**
- `idx_evaluations_subtask` ON (subtask_id)
- `idx_evaluations_overall_score` ON (overall_score)

**SQL Definition:**
```sql
CREATE TABLE evaluations (
    evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subtask_id UUID NOT NULL REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    code_quality DECIMAL(3,1) CHECK (code_quality >= 0 AND code_quality <= 10),
    completeness DECIMAL(3,1) CHECK (completeness >= 0 AND completeness <= 10),
    security DECIMAL(3,1) CHECK (security >= 0 AND security <= 10),
    architecture DECIMAL(3,1) CHECK (architecture >= 0 AND architecture <= 10),
    testability DECIMAL(3,1) CHECK (testability >= 0 AND testability <= 10),
    overall_score DECIMAL(3,1) CHECK (overall_score >= 0 AND overall_score <= 10),
    details JSONB,
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evaluations_subtask ON evaluations(subtask_id);
CREATE INDEX idx_evaluations_overall_score ON evaluations(overall_score);
```

---

### 8. activity_logs

**Purpose:** System-wide activity logging for debugging and auditing

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| log_id | BIGSERIAL | PRIMARY KEY | Auto-incrementing log ID |
| task_id | UUID | FOREIGN KEY REFERENCES tasks(task_id) ON DELETE CASCADE | Related task |
| subtask_id | UUID | FOREIGN KEY REFERENCES subtasks(subtask_id) ON DELETE CASCADE | Related subtask |
| worker_id | UUID | FOREIGN KEY REFERENCES workers(worker_id) | Related worker |
| level | VARCHAR(10) | NOT NULL | Log level: info, warning, error |
| message | TEXT | NOT NULL | Log message |
| metadata | JSONB | NULL | Additional structured data |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Log timestamp |

**Indexes:**
- `idx_activity_logs_task` ON (task_id)
- `idx_activity_logs_created_at` ON (created_at DESC)

**SQL Definition:**
```sql
CREATE TABLE activity_logs (
    log_id BIGSERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
    subtask_id UUID REFERENCES subtasks(subtask_id) ON DELETE CASCADE,
    worker_id UUID REFERENCES workers(worker_id),
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_logs_task ON activity_logs(task_id);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);
```

---

## Table Relationships

### One-to-Many Relationships

1. **users → tasks** (1:N)
   - One user can create many tasks
   - Foreign Key: `tasks.user_id` → `users.user_id`

2. **tasks → subtasks** (1:N)
   - One task decomposes into many subtasks
   - Foreign Key: `subtasks.task_id` → `tasks.task_id`
   - Cascade Delete: Deleting a task deletes all subtasks

3. **tasks → checkpoints** (1:N)
   - One task can have multiple checkpoints
   - Foreign Key: `checkpoints.task_id` → `tasks.task_id`
   - Cascade Delete: Deleting a task deletes all checkpoints

4. **workers → subtasks** (1:N)
   - One worker can be assigned many subtasks
   - Foreign Key: `subtasks.assigned_worker` → `workers.worker_id`

5. **subtasks → evaluations** (1:N)
   - One subtask can have multiple evaluations (peer review, re-evaluation)
   - Foreign Key: `evaluations.subtask_id` → `subtasks.subtask_id`
   - Cascade Delete: Deleting a subtask deletes evaluations

6. **checkpoints → corrections** (1:N)
   - One checkpoint can have multiple corrections
   - Foreign Key: `corrections.checkpoint_id` → `checkpoints.checkpoint_id`
   - Cascade Delete: Deleting a checkpoint deletes corrections

7. **subtasks → corrections** (1:N)
   - One subtask can receive multiple corrections
   - Foreign Key: `corrections.subtask_id` → `subtasks.subtask_id`

### Self-Referential Relationships

1. **subtasks → subtasks** (DAG)
   - Subtasks can depend on other subtasks
   - Stored in: `subtasks.dependencies` (JSONB array of UUIDs)
   - Constraint: Must form a Directed Acyclic Graph (no cycles)

---

## Indexes and Performance

### Primary Indexes (Automatically Created)

All primary keys automatically have B-tree indexes:
- `users.user_id`
- `workers.worker_id`
- `tasks.task_id`
- `subtasks.subtask_id`
- `checkpoints.checkpoint_id`
- `corrections.correction_id`
- `evaluations.evaluation_id`
- `activity_logs.log_id`

### Secondary Indexes (Query Optimization)

#### High-Priority Indexes (Used in every query)

```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);

-- Worker queries (status checking, heartbeat monitoring)
CREATE INDEX idx_workers_status ON workers(status);
CREATE INDEX idx_workers_last_heartbeat ON workers(last_heartbeat);

-- Task queries (user dashboard, status filtering)
CREATE INDEX idx_tasks_user ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);

-- Optimistic locking (concurrent updates)
CREATE INDEX idx_tasks_status_version ON tasks(task_id, status, version);

-- Subtask queries (task detail view, worker assignment)
CREATE INDEX idx_subtasks_task ON subtasks(task_id);
CREATE INDEX idx_subtasks_status ON subtasks(status);
CREATE INDEX idx_subtasks_worker ON subtasks(assigned_worker);

-- Checkpoint queries (review dashboard)
CREATE INDEX idx_checkpoints_task ON checkpoints(task_id);
CREATE INDEX idx_checkpoints_status ON checkpoints(status);

-- Correction tracking
CREATE INDEX idx_corrections_checkpoint ON corrections(checkpoint_id);
CREATE INDEX idx_corrections_subtask ON corrections(subtask_id);

-- Evaluation queries (quality dashboard)
CREATE INDEX idx_evaluations_subtask ON evaluations(subtask_id);
CREATE INDEX idx_evaluations_overall_score ON evaluations(overall_score);

-- Logging (debugging, auditing)
CREATE INDEX idx_activity_logs_task ON activity_logs(task_id);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);
```

#### JSONB Indexes (Future Optimization)

For complex JSONB queries, consider GIN indexes:

```sql
-- Index for tool filtering
CREATE INDEX idx_workers_tools_gin ON workers USING GIN (tools);

-- Index for metadata search
CREATE INDEX idx_tasks_metadata_gin ON tasks USING GIN (metadata);

-- Index for dependency queries
CREATE INDEX idx_subtasks_dependencies_gin ON subtasks USING GIN (dependencies);
```

### Query Performance Notes

1. **Unique Indexes** - Automatically created for UNIQUE constraints
2. **Foreign Key Indexes** - Manually created for all foreign keys to speed up joins
3. **Timestamp Indexes** - DESC order for `created_at` columns (recent first)
4. **Composite Indexes** - `idx_tasks_status_version` for optimistic locking queries

---

## Data Types and Constraints

### UUID Generation

PostgreSQL 13+ has native UUID support with `gen_random_uuid()`:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- Only needed for PostgreSQL <13

-- Use gen_random_uuid() for default values
task_id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

### JSONB vs JSON

Use **JSONB** (binary JSON) for all JSON columns:
- ✅ Faster queries (indexed, no reparsing)
- ✅ Supports indexing (GIN, GiST)
- ✅ Supports operators (`@>`, `?`, `?|`, `?&`)
- ❌ Slightly slower writes (parsing overhead)

### Timestamp with Time Zone

Always use `TIMESTAMP WITH TIME ZONE`:
- Stores UTC internally
- Converts to client timezone on retrieval
- Prevents timezone-related bugs

### Check Constraints

Enforce data integrity at the database level:

```sql
-- Status enums
CONSTRAINT chk_task_status CHECK (status IN ('pending', 'initializing', ...))

-- Percentage ranges
CHECK (progress >= 0 AND progress <= 100)

-- Score ranges
CHECK (code_quality >= 0 AND code_quality <= 10)

-- Complexity ratings
CHECK (complexity >= 1 AND complexity <= 5)
```

### Cascade Deletes

```sql
-- Delete all subtasks when task is deleted
task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE

-- Delete all checkpoints when task is deleted
task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE

-- Delete all corrections when checkpoint is deleted
checkpoint_id UUID NOT NULL REFERENCES checkpoints(checkpoint_id) ON DELETE CASCADE
```

---

## Database Setup Commands

### Initial Setup

```bash
# Create PostgreSQL database
createdb multi_agent_db

# Connect to database
psql multi_agent_db

# Enable UUID extension (PostgreSQL <13)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Schema Migration with Alembic

```bash
cd backend

# Initialize Alembic (first time only)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-12 | Initial schema design with 8 core tables |
| 1.1 | 2025-11-12 | Added `version` column to tasks for optimistic locking |

---

## References

- Architecture Document: `docs/architecture.md`
- Sprint 1 Plan: `docs/sprint-1-plan.md`
- Alembic Documentation: https://alembic.sqlalchemy.org/
- PostgreSQL JSONB: https://www.postgresql.org/docs/current/datatype-json.html
