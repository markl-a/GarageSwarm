# ADR 002: Database Schema Design

**Status:** Accepted

**Date:** 2025-11-11

**Authors:** sir

**Decision Makers:** Product Team, Engineering Team

---

## Context

Multi-Agent on the Web requires a database schema that supports:

1. **Task Management** - Tasks, subtasks, dependencies, execution flow
2. **Worker Management** - Worker registration, status, capabilities, health
3. **Quality Control** - Checkpoints, evaluations, peer reviews, corrections
4. **Audit Trail** - Activity logs, state transitions, decision history
5. **Performance** - Fast queries, efficient joins, scalable design
6. **Flexibility** - Evolving requirements, extensible metadata

Key challenges:
- Complex task decomposition with dependencies (DAG structure)
- Real-time status updates for 10+ workers and 20+ parallel tasks
- Multi-agent collaboration and review workflow
- Storing evaluation scores and metrics
- Historical data for analytics and debugging

---

## Decision

We have designed a normalized relational schema with the following core principles:

### Design Principles

1. **Normalized Schema (3NF)** - Minimize data redundancy, maintain consistency
2. **JSONB for Flexibility** - Use JSONB for extensible metadata and configurations
3. **Explicit Relationships** - Foreign keys with ON DELETE CASCADE for data integrity
4. **Timestamps Everywhere** - Track creation and modification times for all entities
5. **Status Fields** - Enum types for state machines (task status, worker status)
6. **Soft Deletes (Optional)** - Consider `deleted_at` for auditing (TBD)
7. **Indexes for Performance** - Index foreign keys and frequently queried fields

### Schema Overview

We have defined 8 core tables:

```
users          - System users and authentication
  ↓
workers        - Registered worker machines
  ↓
tasks          - High-level tasks submitted by users
  ↓
subtasks       - Decomposed subtasks with dependencies (DAG)
  ↓
evaluations    - Quality scores for subtask results
  ↓
checkpoints    - Human review checkpoints
  ↓
corrections    - Feedback and correction requests
  ↓
activity_logs  - Audit trail of all activities
```

---

## Database Schema

### 1. Users Table

Stores user accounts for authentication and task ownership.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

**Design Decisions:**
- UUID for ID (distributed system friendly, no collisions)
- Email and username unique constraints
- `is_active` for soft account disabling
- `is_superuser` for admin privileges
- Timestamps for audit trail

**Alternatives Considered:**
- Integer ID: Rejected due to distributed nature and potential collisions
- No authentication: Rejected for production security requirements
- OAuth only: May add in future, but start with simple auth

### 2. Workers Table

Stores registered worker machines and their capabilities.

```sql
CREATE TYPE worker_status AS ENUM ('online', 'offline', 'busy', 'error');

CREATE TABLE workers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id VARCHAR(255) UNIQUE NOT NULL,  -- Hardware/MAC address
    machine_name VARCHAR(255) NOT NULL,
    status worker_status DEFAULT 'offline',
    available_tools TEXT[],  -- Array of tool names: ['claude', 'gemini']

    -- System Information
    system_info JSONB,  -- OS, CPU, RAM, GPU details

    -- Resource Metrics (updated via heartbeat)
    cpu_percent DECIMAL(5, 2),
    memory_percent DECIMAL(5, 2),
    disk_percent DECIMAL(5, 2),

    -- Connection
    last_heartbeat TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workers_status ON workers(status);
CREATE INDEX idx_workers_machine_id ON workers(machine_id);
CREATE INDEX idx_workers_last_heartbeat ON workers(last_heartbeat);
```

**Design Decisions:**
- `machine_id` as unique identifier (stable across restarts)
- ENUM for status (finite state machine)
- `available_tools` as TEXT[] for fast querying
- JSONB `system_info` for flexible hardware details
- Resource metrics updated frequently (not historical)
- `last_heartbeat` to detect offline workers

**Alternatives Considered:**
- Separate `worker_capabilities` table: Rejected as overkill for limited tool types
- Store historical metrics: Use Redis/time-series DB instead
- String status: ENUM provides type safety and better performance

### 3. Tasks Table

High-level tasks submitted by users.

```sql
CREATE TYPE task_status AS ENUM (
    'pending',
    'decomposing',
    'allocated',
    'in_progress',
    'paused',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE checkpoint_frequency AS ENUM ('low', 'medium', 'high');

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Task Definition
    description TEXT NOT NULL,
    task_type VARCHAR(50) NOT NULL,  -- code_generation, code_review, etc.
    requirements JSONB,  -- Task-specific requirements

    -- Status
    status task_status DEFAULT 'pending',
    priority INTEGER DEFAULT 5,  -- 1 (highest) to 10 (lowest)

    -- Quality Control
    checkpoint_frequency checkpoint_frequency DEFAULT 'medium',

    -- Progress Tracking
    total_subtasks INTEGER DEFAULT 0,
    completed_subtasks INTEGER DEFAULT 0,

    -- Results
    result JSONB,  -- Final aggregated result
    error_message TEXT,

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
```

**Design Decisions:**
- `task_type` as VARCHAR for flexibility (not ENUM - may add new types)
- JSONB `requirements` for task-specific parameters
- ENUM `status` for well-defined lifecycle
- `priority` integer (1-10 scale) for scheduling
- `checkpoint_frequency` controls review intensity
- Separate `started_at` and `completed_at` for timing analysis
- `result` as JSONB for flexible output structure

**Alternatives Considered:**
- Separate `task_types` table: Rejected as premature optimization
- String arrays for results: JSONB more flexible and queryable
- Separate `task_metadata` table: JSONB avoids extra joins

### 4. Subtasks Table

Decomposed subtasks with dependencies (DAG structure).

```sql
CREATE TYPE subtask_status AS ENUM (
    'pending',
    'ready',  -- Dependencies satisfied
    'allocated',
    'in_progress',
    'completed',
    'failed',
    'requires_review'
);

CREATE TYPE subtask_type AS ENUM (
    'analysis',
    'design',
    'implementation',
    'testing',
    'review',
    'documentation'
);

CREATE TABLE subtasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    parent_subtask_id UUID REFERENCES subtasks(id) ON DELETE CASCADE,

    -- Subtask Definition
    description TEXT NOT NULL,
    subtask_type subtask_type NOT NULL,
    instructions JSONB,  -- Specific instructions for the AI agent

    -- Allocation
    assigned_worker_id UUID REFERENCES workers(id) ON DELETE SET NULL,
    assigned_tool VARCHAR(50),  -- claude, gemini, ollama

    -- Status
    status subtask_status DEFAULT 'pending',
    order_index INTEGER NOT NULL,  -- Execution order within task

    -- Dependencies
    depends_on UUID[],  -- Array of subtask IDs that must complete first

    -- Results
    result JSONB,
    error_message TEXT,

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_subtasks_task_id ON subtasks(task_id);
CREATE INDEX idx_subtasks_status ON subtasks(status);
CREATE INDEX idx_subtasks_assigned_worker_id ON subtasks(assigned_worker_id);
CREATE INDEX idx_subtasks_order_index ON subtasks(task_id, order_index);
CREATE INDEX idx_subtasks_parent ON subtasks(parent_subtask_id);
```

**Design Decisions:**
- Self-referencing `parent_subtask_id` for hierarchical decomposition
- `depends_on` as UUID[] for DAG dependencies (simple and queryable)
- ENUM `subtask_type` categorizes work type
- `order_index` for deterministic ordering within a task
- `assigned_worker_id` and `assigned_tool` track allocation
- JSONB `instructions` for flexible AI prompts
- JSONB `result` stores output (code, analysis, etc.)

**Alternatives Considered:**
- Separate `subtask_dependencies` table (normalized):
  ```sql
  CREATE TABLE subtask_dependencies (
      subtask_id UUID REFERENCES subtasks(id),
      depends_on_subtask_id UUID REFERENCES subtasks(id),
      PRIMARY KEY (subtask_id, depends_on_subtask_id)
  );
  ```
  **Rejected:** UUID[] array simpler for our scale (typically < 100 dependencies per task)

- String-based dependency graph: Rejected for type safety and query efficiency
- Materialized path for hierarchy: UUID[] sufficient for current needs

### 5. Evaluations Table

Quality assessment scores for subtask results.

```sql
CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subtask_id UUID NOT NULL REFERENCES subtasks(id) ON DELETE CASCADE,

    -- Scores (0.0 - 10.0)
    code_quality_score DECIMAL(3, 1),
    completeness_score DECIMAL(3, 1),
    security_score DECIMAL(3, 1),
    architecture_score DECIMAL(3, 1),
    testability_score DECIMAL(3, 1),

    -- Aggregated Score
    overall_score DECIMAL(3, 1),

    -- Details
    evaluation_details JSONB,  -- Tool-specific metrics (pylint, bandit, etc.)
    issues_found TEXT[],
    recommendations TEXT[],

    -- Metadata
    evaluated_by VARCHAR(50),  -- automated|human|agent_review
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evaluations_subtask_id ON evaluations(subtask_id);
CREATE INDEX idx_evaluations_overall_score ON evaluations(overall_score);
CREATE INDEX idx_evaluations_created_at ON evaluations(created_at DESC);
```

**Design Decisions:**
- 5 core scoring dimensions (aligned with PRD requirements)
- DECIMAL(3,1) for scores (0.0 - 10.0 with one decimal place)
- `overall_score` computed from dimension scores
- JSONB `evaluation_details` stores tool-specific metrics
- TEXT[] for issues and recommendations (simple, queryable)
- `evaluated_by` tracks evaluation source

**Alternatives Considered:**
- Separate tables per score dimension: Rejected as over-normalization
- Integer scores (0-100): Decimal provides better granularity
- Separate `evaluation_metrics` table: JSONB more flexible

### 6. Checkpoints Table

Human review checkpoints for quality control.

```sql
CREATE TYPE checkpoint_status AS ENUM (
    'pending',
    'in_review',
    'approved',
    'rejected',
    'requires_correction'
);

CREATE TABLE checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    subtask_id UUID REFERENCES subtasks(id) ON DELETE CASCADE,

    -- Checkpoint Context
    checkpoint_type VARCHAR(50) NOT NULL,  -- scheduled|evaluation_triggered|milestone
    trigger_reason TEXT,

    -- Work Under Review
    work_content JSONB NOT NULL,  -- Code, analysis, or other output
    context JSONB,  -- Additional context for reviewer

    -- Review
    status checkpoint_status DEFAULT 'pending',
    reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Decision
    decision VARCHAR(50),  -- approve|correct|reject
    feedback TEXT,

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_checkpoints_task_id ON checkpoints(task_id);
CREATE INDEX idx_checkpoints_status ON checkpoints(status);
CREATE INDEX idx_checkpoints_reviewer_id ON checkpoints(reviewer_id);
CREATE INDEX idx_checkpoints_created_at ON checkpoints(created_at DESC);
```

**Design Decisions:**
- Links to both `task_id` (overview) and `subtask_id` (specific work)
- `checkpoint_type` categorizes trigger reason
- JSONB `work_content` stores reviewed material
- ENUM `status` for checkpoint lifecycle
- `decision` tracks final outcome
- `feedback` provides correction guidance

**Alternatives Considered:**
- Separate `checkpoint_reviews` table: Single table simpler
- Store work reference only: Storing content enables historical review
- Multiple reviewers: Start simple, can extend later

### 7. Corrections Table

Tracks correction requests and revision cycles.

```sql
CREATE TYPE correction_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'cancelled'
);

CREATE TABLE corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checkpoint_id UUID NOT NULL REFERENCES checkpoints(id) ON DELETE CASCADE,
    subtask_id UUID NOT NULL REFERENCES subtasks(id) ON DELETE CASCADE,

    -- Correction Details
    correction_request TEXT NOT NULL,  -- What needs to be fixed
    original_result JSONB NOT NULL,  -- Original work
    corrected_result JSONB,  -- Fixed work

    -- Assignment
    assigned_worker_id UUID REFERENCES workers(id) ON DELETE SET NULL,
    assigned_tool VARCHAR(50),

    -- Status
    status correction_status DEFAULT 'pending',
    revision_count INTEGER DEFAULT 0,  -- Number of revision attempts

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_corrections_checkpoint_id ON corrections(checkpoint_id);
CREATE INDEX idx_corrections_subtask_id ON corrections(subtask_id);
CREATE INDEX idx_corrections_status ON corrections(status);
CREATE INDEX idx_corrections_assigned_worker_id ON corrections(assigned_worker_id);
```

**Design Decisions:**
- Links checkpoint to correction work
- Stores both `original_result` and `corrected_result`
- `revision_count` tracks correction attempts (max 3 per PRD)
- Re-assignment possible via `assigned_worker_id`
- Status tracks correction lifecycle

**Alternatives Considered:**
- Embed in checkpoints table: Separate table cleaner for 1:N relationship
- Multiple correction attempts in array: Separate records better for querying

### 8. Activity Logs Table

Comprehensive audit trail for all system activities.

```sql
CREATE TYPE activity_type AS ENUM (
    'task_created',
    'task_started',
    'task_completed',
    'subtask_allocated',
    'subtask_started',
    'subtask_completed',
    'checkpoint_created',
    'checkpoint_reviewed',
    'correction_requested',
    'worker_registered',
    'worker_offline',
    'evaluation_performed'
);

CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Activity Classification
    activity_type activity_type NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- task|subtask|worker|checkpoint
    entity_id UUID NOT NULL,

    -- Actor
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    worker_id UUID REFERENCES workers(id) ON DELETE SET NULL,

    -- Activity Details
    description TEXT NOT NULL,
    metadata JSONB,  -- Additional context

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_logs_entity ON activity_logs(entity_type, entity_id);
CREATE INDEX idx_activity_logs_type ON activity_logs(activity_type);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);
CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_worker_id ON activity_logs(worker_id);
```

**Design Decisions:**
- ENUM `activity_type` for well-defined events
- Generic `entity_type` + `entity_id` for flexible relationships
- Both `user_id` and `worker_id` to track actors
- JSONB `metadata` for event-specific details
- No foreign key on `entity_id` (polymorphic relationship)
- Append-only (no updates/deletes)

**Alternatives Considered:**
- Separate log tables per entity: Single table easier to query
- JSON log files: Database provides querying and indexing
- Time-series database: PostgreSQL sufficient for current scale

---

## JSONB Schema Definitions

### Task Requirements Schema

```json
{
  "language": "python",
  "framework": "fastapi",
  "include_tests": true,
  "include_docs": true,
  "style_guide": "PEP 8",
  "dependencies": ["sqlalchemy", "pydantic"],
  "features": [
    "user authentication",
    "JWT tokens",
    "password reset"
  ]
}
```

### Subtask Instructions Schema

```json
{
  "prompt": "Create a FastAPI endpoint for user login with JWT...",
  "context": {
    "related_files": ["src/models/user.py", "src/config.py"],
    "dependencies": ["subtask_abc123", "subtask_xyz789"]
  },
  "constraints": {
    "max_lines": 100,
    "timeout_seconds": 300
  }
}
```

### Worker System Info Schema

```json
{
  "os": "Linux",
  "os_version": "Ubuntu 22.04",
  "architecture": "x86_64",
  "cpu_count": 8,
  "memory_gb": 16,
  "disk_gb": 512,
  "gpu": {
    "available": true,
    "model": "NVIDIA RTX 3080",
    "memory_gb": 10
  }
}
```

### Evaluation Details Schema

```json
{
  "tools_used": ["pylint", "bandit", "radon"],
  "pylint": {
    "score": 8.5,
    "issues": ["C0301: Line too long", "W0612: Unused variable"]
  },
  "bandit": {
    "high_severity": 0,
    "medium_severity": 1,
    "low_severity": 3
  },
  "radon": {
    "cyclomatic_complexity": 4.2,
    "maintainability_index": 78
  }
}
```

---

## Query Patterns

### Get Active Tasks for User

```sql
SELECT t.*,
       u.username,
       COUNT(st.id) FILTER (WHERE st.status = 'completed') as completed_count,
       COUNT(st.id) as total_count
FROM tasks t
JOIN users u ON t.user_id = u.id
LEFT JOIN subtasks st ON t.id = st.task_id
WHERE t.user_id = $1 AND t.status != 'completed'
GROUP BY t.id, u.username
ORDER BY t.priority ASC, t.created_at DESC;
```

### Get Ready Subtasks (Dependencies Satisfied)

```sql
-- Subtasks where all dependencies are completed
SELECT st.*
FROM subtasks st
WHERE st.status = 'pending'
  AND st.task_id = $1
  AND NOT EXISTS (
    SELECT 1
    FROM unnest(st.depends_on) dep_id
    JOIN subtasks dep ON dep.id = dep_id
    WHERE dep.status != 'completed'
  );
```

### Get Worker Utilization

```sql
SELECT
    w.id,
    w.machine_name,
    w.status,
    COUNT(st.id) FILTER (WHERE st.status = 'in_progress') as active_subtasks,
    w.cpu_percent,
    w.memory_percent
FROM workers w
LEFT JOIN subtasks st ON w.id = st.assigned_worker_id
WHERE w.status = 'online'
GROUP BY w.id
ORDER BY active_subtasks ASC, w.cpu_percent ASC;
```

### Get Pending Checkpoints

```sql
SELECT
    c.*,
    t.description as task_description,
    st.description as subtask_description,
    e.overall_score
FROM checkpoints c
JOIN tasks t ON c.task_id = t.id
LEFT JOIN subtasks st ON c.subtask_id = st.id
LEFT JOIN evaluations e ON st.id = e.subtask_id
WHERE c.status = 'pending'
ORDER BY
    CASE WHEN e.overall_score < 7.0 THEN 0 ELSE 1 END,
    c.created_at ASC;
```

### Get Task Activity Timeline

```sql
SELECT
    al.activity_type,
    al.description,
    al.created_at,
    u.username as user_name,
    w.machine_name as worker_name
FROM activity_logs al
LEFT JOIN users u ON al.user_id = u.id
LEFT JOIN workers w ON al.worker_id = w.id
WHERE al.entity_type = 'task' AND al.entity_id = $1
ORDER BY al.created_at DESC;
```

---

## Data Integrity and Constraints

### Foreign Key Cascade Rules

| Relationship | On Delete | Rationale |
|--------------|-----------|-----------|
| tasks → users | CASCADE | Remove user's tasks when user deleted |
| subtasks → tasks | CASCADE | Remove subtasks when task deleted |
| subtasks → workers | SET NULL | Keep subtask history if worker removed |
| checkpoints → tasks | CASCADE | Remove checkpoints when task deleted |
| corrections → checkpoints | CASCADE | Remove corrections when checkpoint deleted |
| activity_logs → users | SET NULL | Preserve logs even if user deleted |

### Check Constraints

```sql
-- Score must be between 0.0 and 10.0
ALTER TABLE evaluations ADD CONSTRAINT check_score_range
    CHECK (
        overall_score BETWEEN 0.0 AND 10.0 AND
        code_quality_score BETWEEN 0.0 AND 10.0 AND
        completeness_score BETWEEN 0.0 AND 10.0 AND
        security_score BETWEEN 0.0 AND 10.0 AND
        architecture_score BETWEEN 0.0 AND 10.0 AND
        testability_score BETWEEN 0.0 AND 10.0
    );

-- Priority must be between 1 and 10
ALTER TABLE tasks ADD CONSTRAINT check_priority_range
    CHECK (priority BETWEEN 1 AND 10);

-- Resource percentages must be 0-100
ALTER TABLE workers ADD CONSTRAINT check_resource_range
    CHECK (
        cpu_percent BETWEEN 0 AND 100 AND
        memory_percent BETWEEN 0 AND 100 AND
        disk_percent BETWEEN 0 AND 100
    );

-- Revision count cannot be negative
ALTER TABLE corrections ADD CONSTRAINT check_revision_count
    CHECK (revision_count >= 0);
```

### Triggers

**Update `updated_at` timestamp:**

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workers_updated_at BEFORE UPDATE ON workers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subtasks_updated_at BEFORE UPDATE ON subtasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## Performance Optimization

### Indexing Strategy

1. **Primary Keys:** All tables use UUID primary keys (indexed by default)
2. **Foreign Keys:** All foreign keys are indexed
3. **Status Fields:** Status enums indexed for filtering
4. **Timestamps:** `created_at` indexed DESC for recent-first queries
5. **Composite Indexes:** `(task_id, order_index)` for subtask ordering

### Query Optimization

1. **Use prepared statements** to avoid SQL injection and improve performance
2. **Limit result sets** with pagination (LIMIT/OFFSET or cursor-based)
3. **Use covering indexes** where possible
4. **Avoid N+1 queries** with JOIN or eager loading
5. **Use connection pooling** (SQLAlchemy pool_size=20)

### Partitioning (Future)

Consider partitioning `activity_logs` by month if table grows > 10M rows:

```sql
CREATE TABLE activity_logs (
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ...
) PARTITION BY RANGE (created_at);

CREATE TABLE activity_logs_2025_12 PARTITION OF activity_logs
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

---

## Migration Strategy

### Alembic Migrations

All schema changes managed via Alembic:

```bash
# Create migration
alembic revision --autogenerate -m "Add subtask_type field"

# Review generated migration
cat alembic/versions/002_add_subtask_type.py

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Initial Migration (001_initial_schema.py)

Already created with all 8 tables, indexes, constraints, and triggers.

### Future Migrations

1. **Add fields:** Use `ALTER TABLE ADD COLUMN`
2. **Modify fields:** Create new column, migrate data, drop old column
3. **Add indexes:** Use `CREATE INDEX CONCURRENTLY` (no lock)
4. **Data migrations:** Write custom Python scripts in Alembic

---

## Consequences

### Positive

1. **Clear Structure:** Normalized schema reduces data redundancy
2. **Type Safety:** ENUMs and check constraints prevent invalid data
3. **Audit Trail:** Comprehensive activity logging for debugging
4. **Performance:** Well-indexed for common query patterns
5. **Flexibility:** JSONB fields allow schema evolution
6. **Referential Integrity:** Foreign keys enforce consistency

### Negative

1. **Complexity:** 8 tables with multiple relationships
2. **JOIN Overhead:** Some queries require multiple joins
3. **JSONB Queries:** Less efficient than normalized columns
4. **Migration Risk:** Schema changes require careful coordination

### Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema changes break app | High | Use Alembic, test migrations |
| Query performance degrades | High | Monitor slow queries, add indexes |
| JSONB schema inconsistency | Medium | Validate JSONB with Pydantic |
| Circular dependencies | Medium | Validate DAG on subtask creation |

---

## Review and Updates

This ADR should be reviewed:
- When performance issues are identified
- When new features require schema changes
- After every 10,000 tasks to analyze patterns
- Quarterly as part of technical debt review

**Next Review Date:** 2025-12-01

---

## References

1. [PostgreSQL Documentation](https://www.postgresql.org/docs/15/index.html)
2. [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
3. [Alembic Documentation](https://alembic.sqlalchemy.org/)
4. [Database Schema Diagram](../database-schema.md)

---

**Status:** This ADR is accepted and implemented.

**Last Updated:** 2025-12-09
