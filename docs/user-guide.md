# User Guide

Welcome to the Multi-Agent on the Web User Guide! This comprehensive tutorial will help you get the most out of the distributed multi-agent orchestration platform.

## Table of Contents

- [System Overview](#system-overview)
- [Starting the System](#starting-the-system)
- [Dashboard Overview](#dashboard-overview)
- [Working with Workers](#working-with-workers)
- [Creating and Managing Tasks](#creating-and-managing-tasks)
- [Monitoring Task Execution](#monitoring-task-execution)
- [Checkpoint Review System](#checkpoint-review-system)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)

## System Overview

Multi-Agent on the Web is a distributed platform that coordinates multiple AI agents across different machines to execute complex tasks in parallel.

### Key Concepts

- **Backend**: Central coordinator that manages all workers and tasks
- **Worker Agent**: Runs on distributed machines and executes subtasks using AI tools
- **Task**: High-level work request submitted by users
- **Subtask**: Individual work units decomposed from tasks
- **Checkpoint**: Human review points for quality control
- **Evaluation**: Automated quality assessment of completed work

### Architecture Flow

```
User → Backend → Task Decomposition → Subtasks
                      ↓
              Task Allocation
                      ↓
        Workers (with AI Tools)
                      ↓
              Execution & Review
                      ↓
        Human Checkpoints (if needed)
                      ↓
              Task Completion
```

## Starting the System

### Quick Start with Docker

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### Start Individual Components

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Worker Agent:**
```bash
cd worker-agent
source venv/bin/activate
python src/main.py --config config/agent.yaml
```

**Frontend:**
```bash
cd frontend
flutter run -d chrome
```

### Verify System is Running

1. Check backend health: `http://localhost:8002/api/v1/health`
2. View API docs: `http://localhost:8002/docs`
3. Open frontend dashboard: `http://localhost:3000`

## Dashboard Overview

The Flutter-based dashboard provides a real-time view of your distributed system.

### Main Sections

#### 1. Workers View

**Location**: Main navigation → Workers

Displays all registered worker agents:

- **Worker Status**: Online, Offline, Busy, Idle
- **Machine Information**: Name, OS, CPU, Memory
- **Available Tools**: Claude Code, Gemini CLI, Ollama
- **Resource Usage**: Real-time CPU, Memory, Disk metrics
- **Current Task**: What the worker is currently executing

**Status Indicators:**
- 🟢 Green: Online and available
- 🟡 Yellow: Online but busy
- 🔴 Red: Offline or disconnected
- ⚪ Gray: Idle (no tasks assigned)

#### 2. Tasks View

**Location**: Main navigation → Tasks

Shows all tasks in the system:

- **Task List**: All submitted tasks with status
- **Filters**: By status (pending, in_progress, completed, failed, cancelled)
- **Search**: Find tasks by description
- **Quick Actions**: Cancel, View details, Re-submit

#### 3. Task Detail View

**Location**: Click on any task in Tasks View

Detailed information about a specific task:

- **Task Overview**: Description, status, progress
- **Subtasks**: List of all subtasks with individual status
- **Timeline**: Execution history and events
- **Checkpoints**: Human review points (if applicable)
- **Evaluations**: Quality scores for completed work
- **Logs**: Real-time execution logs

## Working with Workers

### Registering a New Worker

Workers automatically register when started:

```bash
cd worker-agent
python src/main.py --config config/agent.yaml
```

The worker will:
1. Connect to the backend
2. Send system information
3. Report available AI tools
4. Start sending heartbeats every 30 seconds

### Monitoring Worker Health

**Via Dashboard:**
- Navigate to Workers view
- Check status indicators
- View resource usage graphs

**Via API:**
```bash
# List all workers
curl http://localhost:8002/api/v1/workers

# Get specific worker details
curl http://localhost:8002/api/v1/workers/{worker_id}
```

### Worker Status Lifecycle

1. **Offline**: Worker not connected
2. **Online**: Connected and ready
3. **Busy**: Executing tasks
4. **Idle**: Online but no tasks
5. **Disconnected**: Lost connection (no heartbeat for 90+ seconds)

### Unregistering a Worker

For graceful shutdown:

```bash
# Stop the worker process (Ctrl+C)
# The worker will automatically notify the backend

# Or manually via API:
curl -X POST http://localhost:8002/api/v1/workers/{worker_id}/unregister
```

## Creating and Managing Tasks

### Task Types

The system supports six task types:

1. **develop_feature**: Develop new features (Code → Review → Tests → Docs)
2. **bug_fix**: Fix bugs (Analysis → Fix → Regression Tests)
3. **refactor**: Refactor code (Analysis → Refactoring → Test Verification)
4. **code_review**: Review code (Static Analysis → Security Review → Report)
5. **documentation**: Write docs (API Docs → User Guide → README)
6. **testing**: Create tests (Test Plan → Unit Tests → Integration Tests → Report)

### Creating a Task

#### Via Dashboard

1. Click "New Task" button
2. Fill in task details:
   - **Description**: Detailed task description (supports Markdown)
   - **Task Type**: Select from dropdown
   - **Checkpoint Frequency**: low, medium, or high
   - **Privacy Level**: normal or sensitive
   - **Tool Preferences**: Preferred AI tools (optional)
3. Click "Submit Task"

#### Via API

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "# Add User Authentication\n\nImplement JWT-based authentication with:\n- Login/Logout endpoints\n- Token refresh mechanism\n- Password hashing\n- Rate limiting",
    "task_type": "develop_feature",
    "checkpoint_frequency": "medium",
    "privacy_level": "normal",
    "tool_preferences": ["claude_code", "gemini_cli"]
  }'
```

### Task Description Format

Use Markdown for rich formatting:

```markdown
# Task Title

## Objectives
- Objective 1
- Objective 2

## Requirements
1. Requirement A
2. Requirement B

## Technical Details
- Tech stack: Python, FastAPI
- Database: PostgreSQL
- Authentication: JWT

## Acceptance Criteria
- [ ] All tests pass
- [ ] Code coverage > 80%
- [ ] Documentation updated
```

### Checkpoint Frequency

Controls how often human review points are created:

- **low**: Checkpoints only on critical issues or task completion
- **medium**: Checkpoints after major subtasks (recommended)
- **high**: Checkpoints after every subtask

### Privacy Levels

- **normal**: Can use any available AI tool (cloud-based OK)
- **sensitive**: Prefers local AI tools (Ollama) for privacy

### Viewing Task Status

#### Via Dashboard

1. Navigate to Tasks view
2. Click on a task to see details
3. Monitor real-time progress updates

#### Via API

```bash
# List all tasks
curl http://localhost:8002/api/v1/tasks

# Get specific task
curl http://localhost:8002/api/v1/tasks/{task_id}

# Get real-time progress
curl http://localhost:8002/api/v1/tasks/{task_id}/progress
```

### Cancelling a Task

#### Via Dashboard

1. Open task details
2. Click "Cancel Task" button
3. Confirm cancellation

#### Via API

```bash
curl -X POST http://localhost:8002/api/v1/tasks/{task_id}/cancel
```

Note: Only pending or in-progress tasks can be cancelled.

## Monitoring Task Execution

### Real-Time Updates

The system provides real-time updates via:

- **WebSocket**: Live status updates to dashboard
- **Progress Tracking**: Percentage completion
- **Logs**: Execution logs for each subtask

### Task Lifecycle

```
pending → decomposing → ready → in_progress → (checkpoints) → completed
                                      ↓
                                  cancelled / failed
```

### Subtask Status

Each subtask progresses through:

1. **pending**: Waiting for dependencies or allocation
2. **ready**: Dependencies satisfied, ready for execution
3. **allocated**: Assigned to a worker
4. **in_progress**: Being executed
5. **under_review**: Being reviewed by another agent
6. **needs_revision**: Review found issues, needs fixing
7. **completed**: Successfully completed
8. **failed**: Failed after retries

### Viewing Logs

**Via Dashboard:**
- Open task details
- Click on a subtask
- View real-time logs in the logs panel

**Via WebSocket:**
```javascript
const ws = new WebSocket('ws://localhost:8002/ws/task/{task_id}');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Status update:', data);
};
```

### Progress Tracking

Progress is calculated as:
```
Progress = (completed_subtasks / total_subtasks) * 100
```

View progress:
- Dashboard: Progress bar on task card
- API: `/api/v1/tasks/{task_id}/progress`

## Checkpoint Review System

Checkpoints allow you to review and guide the AI agents' work.

### When Checkpoints are Triggered

1. **Frequency-Based**: Based on checkpoint_frequency setting
2. **Evaluation-Based**: When quality scores fall below threshold (< 7.0/10)
3. **Manual**: Explicitly requested by the system

### Reviewing a Checkpoint

#### Via Dashboard

1. Navigate to Tasks view
2. Tasks with pending checkpoints show a "Review" badge
3. Click on the task
4. Review the completed work:
   - View code changes
   - Check evaluation scores
   - Read subtask outputs
5. Make a decision

#### Checkpoint Decisions

**Accept**: Work meets requirements
- Task continues to next phase
- No changes needed

**Correct**: Work needs minor adjustments
- Provide specific feedback
- System will make corrections
- Work continues after fixes

**Reject**: Work is unsatisfactory
- Provide detailed feedback
- Subtask will be reassigned
- May use different AI tool

### Providing Feedback

Be specific and actionable:

**Good Feedback:**
```markdown
The authentication implementation is good, but:

1. Add rate limiting to prevent brute force attacks
2. Use bcrypt instead of SHA256 for password hashing
3. Add unit tests for token refresh logic
4. Document the API endpoints in OpenAPI format
```

**Poor Feedback:**
```markdown
Needs improvement.
```

### API for Checkpoint Review

```bash
curl -X POST http://localhost:8002/api/v1/tasks/{task_id}/checkpoint/{checkpoint_id}/decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "correct",
    "notes": "Add rate limiting and improve tests",
    "specific_feedback": {
      "security": "Add rate limiting to login endpoint",
      "testing": "Need more edge case tests"
    }
  }'
```

## Advanced Features

### Task Dependencies

When creating subtasks manually (advanced use):

```bash
curl -X POST http://localhost:8002/api/v1/subtasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-uuid",
    "name": "Integration Tests",
    "description": "Write integration tests",
    "dependencies": ["unit-test-subtask-uuid"],
    "recommended_tool": "claude_code"
  }'
```

### Batch Operations

Process multiple tasks in parallel:

```bash
# Submit multiple tasks
for desc in "Fix bug #123" "Add feature X" "Refactor module Y"; do
  curl -X POST http://localhost:8002/api/v1/tasks \
    -H "Content-Type: application/json" \
    -d "{\"description\": \"$desc\", \"task_type\": \"bug_fix\"}"
done
```

### Worker Scaling

Add more workers for increased throughput:

```bash
# On each new machine:
cd worker-agent
# Edit config/agent.yaml with unique machine_name
python src/main.py --config config/agent.yaml
```

The system will automatically:
- Load balance tasks across workers
- Consider worker capabilities (tools)
- Monitor worker health
- Failover to other workers if one fails

### Quality Evaluation

Every subtask is evaluated on 5 dimensions:

1. **Code Quality** (0-10): Readability, maintainability, style
2. **Completeness** (0-10): All requirements met
3. **Security** (0-10): No vulnerabilities
4. **Architecture Alignment** (0-10): Follows design patterns
5. **Testability** (0-10): Unit test coverage

**Overall Score** = Average of all dimensions

Scores < 7.0 trigger automatic checkpoints.

View evaluations:
```bash
curl http://localhost:8002/api/v1/subtasks/{subtask_id}/evaluation
```

## Best Practices

### Task Description Guidelines

1. **Be Specific**: Clear objectives and requirements
2. **Use Markdown**: Structured formatting improves comprehension
3. **Include Context**: Technical stack, constraints, dependencies
4. **Define Success**: Acceptance criteria and test requirements
5. **Provide Examples**: Code snippets, API formats, etc.

### Checkpoint Strategy

- **Low Frequency**: For routine, low-risk tasks
- **Medium Frequency**: For most development work (recommended)
- **High Frequency**: For critical or complex tasks

### Worker Management

1. **Distribute Workload**: Deploy workers on multiple machines
2. **Match Tools to Tasks**: Ensure workers have required AI tools
3. **Monitor Resources**: Keep CPU/memory below 80%
4. **Graceful Shutdown**: Always use Ctrl+C, not kill -9

### Performance Optimization

1. **Parallel Execution**: Break tasks into independent subtasks
2. **Worker Capacity**: Don't overload workers (max 3 concurrent tasks per worker)
3. **Network Latency**: Place workers close to backend (same network)
4. **Resource Allocation**: More powerful machines = more concurrent tasks

### Security Best Practices

1. **API Keys**: Never commit API keys to version control
2. **Environment Variables**: Use `.env` files for secrets
3. **Network Security**: Use HTTPS in production
4. **Privacy Levels**: Mark sensitive tasks appropriately
5. **Access Control**: Implement authentication for production deployments

## Keyboard Shortcuts (Dashboard)

- `Ctrl+N`: New Task
- `Ctrl+F`: Search Tasks
- `Ctrl+R`: Refresh Dashboard
- `Esc`: Close Modal
- `↑/↓`: Navigate Lists
- `Enter`: Open Selected Item

## Troubleshooting

For common issues and solutions, see [troubleshooting.md](troubleshooting.md).

## Getting Help

- **API Documentation**: http://localhost:8002/docs
- **Architecture Guide**: [architecture.md](architecture.md)
- **Installation Guide**: [installation.md](installation.md)
- **API Reference**: [api-reference.md](api-reference.md)
- **GitHub Issues**: Report bugs or request features

## Example Workflows

### Example 1: Feature Development

```bash
# 1. Create feature development task
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Add REST API for user profile management",
    "task_type": "develop_feature",
    "checkpoint_frequency": "medium"
  }'

# 2. System automatically decomposes into subtasks:
#    - Code Generation
#    - Code Review
#    - Test Generation
#    - Documentation

# 3. Workers execute subtasks in parallel

# 4. Review checkpoint after major subtask completion

# 5. Task completes when all subtasks done
```

### Example 2: Bug Fix

```bash
# 1. Submit bug fix task
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Fix: API returns 500 error when user email is null",
    "task_type": "bug_fix",
    "checkpoint_frequency": "low"
  }'

# 2. System decomposes into:
#    - Bug Analysis
#    - Fix Implementation
#    - Regression Testing

# 3. Workers execute fix

# 4. Review checkpoint if quality score < 7.0

# 5. Deploy fix after completion
```

### Example 3: Code Review

```bash
# 1. Submit code review task
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Review PR #123: New authentication module",
    "task_type": "code_review",
    "checkpoint_frequency": "high"
  }'

# 2. System performs:
#    - Static Analysis (pylint, security scan)
#    - Security Review (vulnerability check)
#    - Review Report generation

# 3. Multiple checkpoints for thorough review

# 4. Final report generated
```

## Next Steps

After mastering the basics:

1. **Explore API**: See [api-reference.md](api-reference.md) for programmatic access
2. **Scale Up**: Deploy workers on multiple machines
3. **Customize**: Adjust worker configurations for your needs
4. **Integrate**: Connect with CI/CD pipelines
5. **Monitor**: Set up alerts and dashboards for production use

Happy orchestrating!
