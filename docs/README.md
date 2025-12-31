# Documentation Index

Welcome to the Multi-Agent on the Web documentation! This page provides an overview of all available documentation and helps you find what you need.

## Getting Started

New to the platform? Start here:

1. **[Installation Guide](installation.md)** - Set up the platform on your system
2. **[User Guide](user-guide.md)** - Learn how to use the platform
3. **[Quick Start Example](#quick-start-example)** - Run your first task in 5 minutes

## Documentation Categories

### For Users

Documentation for end users who want to use the platform:

| Document | Description |
|----------|-------------|
| [Installation Guide](installation.md) | Step-by-step installation for Backend, Worker Agents, and Frontend |
| [User Guide](user-guide.md) | Complete tutorial on using the platform |
| [API Reference](api-reference.md) | REST API documentation with examples |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |

### For Developers

Documentation for developers contributing to the platform:

| Document | Description |
|----------|-------------|
| [Architecture Design](architecture.md) | System architecture and design decisions |
| [Database Schema](database-schema.md) | PostgreSQL schema and relationships |
| [Redis Schema](redis-schema.md) | Redis data structures and caching strategy |
| [Error Handling Guide](ERROR-HANDLING-GUIDE.md) | Error handling patterns and best practices |
| [Review Workflow Guide](REVIEW-WORKFLOW-GUIDE.md) | Agent peer review workflow |
| [Contributing Guide](../CONTRIBUTING.md) | How to contribute to the project |

### For Project Managers

Documentation for understanding the project scope and planning:

| Document | Description |
|----------|-------------|
| [Product Requirements](PRD.md) | Complete product requirements document |
| [Epic Breakdown](epics.md) | 9 Epics broken down into 58 User Stories |
| [Sprint Plans](sprint-1-plan.md) | Detailed sprint planning |
| [UX Design Specification](ux-design-specification.md) | UI/UX design guidelines |
| [Product Brief](product-brief-Multi-Agent-on-the-web-2025-11-11.md) | Original product vision |

## Quick Start Example

Get up and running in 5 minutes:

### 1. Start the Backend

```bash
# Clone and start services
git clone <repository-url>
cd bmad-test
docker-compose up -d

# Verify services are healthy
curl http://localhost:8002/api/v1/health
```

### 2. Start a Worker

```bash
cd worker-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure worker
cp config/agent.yaml.example config/agent.yaml
export ANTHROPIC_API_KEY="your-key"

# Start worker
python src/main.py --config config/agent.yaml
```

### 3. Submit Your First Task

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a simple hello world REST API endpoint",
    "task_type": "develop_feature",
    "checkpoint_frequency": "low"
  }'
```

### 4. Monitor Progress

```bash
# List tasks
curl http://localhost:8002/api/v1/tasks

# Get task details
curl http://localhost:8002/api/v1/tasks/{task_id}

# Or view in browser
# http://localhost:8002/docs
```

## Common Use Cases

### Use Case 1: Feature Development

Develop a new feature with automated quality checks:

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "# User Profile Management\n\nImplement CRUD operations for user profiles:\n- GET /users/{id}\n- POST /users\n- PUT /users/{id}\n- DELETE /users/{id}\n\nRequirements:\n- JWT authentication\n- Input validation\n- Unit tests (>80% coverage)\n- API documentation",
    "task_type": "develop_feature",
    "checkpoint_frequency": "medium"
  }'
```

The system will:
1. Decompose into: Code Generation → Code Review → Test Generation → Documentation
2. Distribute subtasks to available workers
3. Execute with AI agents (Claude, Gemini, or Ollama)
4. Trigger checkpoints for human review
5. Provide quality evaluation scores

### Use Case 2: Bug Fix

Fix a bug with automated testing:

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Fix: API returns 500 error when email field is null in user registration. Add proper validation and error handling.",
    "task_type": "bug_fix",
    "checkpoint_frequency": "low"
  }'
```

The system will:
1. Decompose into: Bug Analysis → Fix Implementation → Regression Testing
2. Execute fix with appropriate AI agent
3. Run automated tests
4. Generate bug fix report

### Use Case 3: Code Review

Review code with automated security and quality checks:

```bash
curl -X POST http://localhost:8002/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Review PR #123: New authentication module using JWT tokens",
    "task_type": "code_review",
    "checkpoint_frequency": "high"
  }'
```

The system will:
1. Run static analysis (pylint, radon)
2. Perform security scan (bandit)
3. Generate detailed review report
4. Request human review at multiple checkpoints

## Documentation Structure

```
docs/
├── README.md                          # This file - Documentation index
│
├── User Documentation/
│   ├── installation.md                # Installation guide
│   ├── user-guide.md                  # User tutorial
│   ├── api-reference.md               # API documentation
│   └── troubleshooting.md             # Common issues
│
├── Technical Documentation/
│   ├── architecture.md                # Architecture design
│   ├── database-schema.md             # Database structure
│   ├── redis-schema.md                # Redis structure
│   ├── ERROR-HANDLING-GUIDE.md        # Error handling
│   └── REVIEW-WORKFLOW-GUIDE.md       # Review workflow
│
├── Project Documentation/
│   ├── PRD.md                         # Product requirements
│   ├── epics.md                       # Epic breakdown
│   ├── sprint-1-plan.md               # Sprint planning
│   ├── ux-design-specification.md     # UX design
│   └── product-brief-*.md             # Product vision
│
└── Blog Posts/ (Implementation Reports)
    ├── blog-sprint1-backend-foundation.md
    └── blog-sprint1-backend-foundation-zh-TW.md
```

## Key Concepts

Understanding these concepts will help you use the platform effectively:

### Workers
- Distributed agents running on different machines
- Execute subtasks using AI tools (Claude, Gemini, Ollama)
- Report health via heartbeat mechanism
- Automatically load-balanced by the system

### Tasks
- High-level work requests submitted by users
- Automatically decomposed into subtasks
- Six task types: develop_feature, bug_fix, refactor, code_review, documentation, testing
- Support Markdown for rich descriptions

### Subtasks
- Individual work units created from task decomposition
- Allocated to appropriate workers based on tool capabilities
- Executed in parallel when dependencies allow
- Evaluated on 5 quality dimensions

### Checkpoints
- Human review points in the execution flow
- Triggered by frequency setting or low quality scores
- Support accept/correct/reject decisions
- Enable human oversight of AI work

### Evaluation
- Automated quality assessment of completed work
- 5 dimensions: Code Quality, Completeness, Security, Architecture, Testability
- Scores range from 0-10
- Scores < 7.0 automatically trigger checkpoints

## API Overview

The platform provides a comprehensive REST API:

**Workers API** - Manage worker agents
- `POST /api/v1/workers/register` - Register worker
- `POST /api/v1/workers/{id}/heartbeat` - Send heartbeat
- `GET /api/v1/workers` - List workers
- `GET /api/v1/workers/{id}` - Get worker details

**Tasks API** - Manage tasks
- `POST /api/v1/tasks` - Create task
- `GET /api/v1/tasks` - List tasks
- `GET /api/v1/tasks/{id}` - Get task details
- `POST /api/v1/tasks/{id}/cancel` - Cancel task
- `POST /api/v1/tasks/{id}/decompose` - Decompose task

**Subtasks API** - Manage subtasks
- `GET /api/v1/subtasks/{id}` - Get subtask details
- `POST /api/v1/subtasks/{id}/result` - Submit result
- `GET /api/v1/subtasks/{id}/evaluation` - Get evaluation

**Checkpoints API** - Human review
- `GET /api/v1/tasks/{id}/checkpoints` - List checkpoints
- `POST /api/v1/tasks/{task_id}/checkpoint/{checkpoint_id}/decision` - Submit decision

**WebSocket API** - Real-time updates
- `WS /ws/task/{id}` - Subscribe to task updates

**Health API** - Monitor system health
- `GET /api/v1/health` - Overall health check

For complete API documentation, see [API Reference](api-reference.md).

## Technology Stack Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI 0.104+ | Async REST API server |
| Database | PostgreSQL 15+ | Persistent data storage |
| Cache | Redis 7+ | Real-time state and caching |
| Frontend | Flutter 3.16+ | Cross-platform UI |
| Worker SDK | Python 3.11+ | Worker agent implementation |
| AI Tools | Claude, Gemini, Ollama | Task execution |
| ORM | SQLAlchemy 2.0+ | Database abstraction |
| Migration | Alembic | Schema version control |
| State Mgmt | Riverpod 2.4+ | Frontend state |

## Development Workflow

### For Backend Development

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload

# Run tests
pytest

# Create migration
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### For Worker Development

```bash
cd worker-agent
source venv/bin/activate
python src/main.py --config config/agent.yaml

# Run tests
pytest
```

### For Frontend Development

```bash
cd frontend
flutter run -d chrome

# Build for production
flutter build web
```

## Performance Targets

The platform is designed to meet these performance goals:

- ⚡ Task submission response: < 2s
- 🔄 WebSocket latency: < 500ms
- 📊 Dashboard load time: < 3s
- 👥 Concurrent users: 100+
- 🖥️ Worker capacity: 10+ machines
- ⚙️ Parallel tasks: 20+

## Security Considerations

When deploying to production:

1. **API Keys**: Store in environment variables, never commit to git
2. **Database**: Use strong passwords, enable SSL
3. **Redis**: Enable authentication, restrict network access
4. **Backend**: Implement JWT authentication, enable HTTPS
5. **Workers**: Use secure channels, validate all inputs
6. **Network**: Use firewalls, VPNs for worker communication

See [Architecture Design](architecture.md) for detailed security architecture.

## Monitoring and Observability

Monitor your deployment:

1. **Health Endpoints**: `/api/v1/health` for uptime monitoring
2. **Worker Status**: Check heartbeat timestamps
3. **Task Metrics**: Track completion rates and execution times
4. **Logs**: Centralized logging with structlog
5. **Resource Usage**: Monitor CPU, memory, disk on all machines

## Support Resources

### Getting Help

1. **Documentation**: Start here! Most questions are answered in the docs
2. **Troubleshooting Guide**: [troubleshooting.md](troubleshooting.md) for common issues
3. **API Reference**: [api-reference.md](api-reference.md) for API details
4. **GitHub Issues**: Report bugs or request features
5. **GitHub Discussions**: Ask questions and share ideas

### Contributing

We welcome contributions! See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Code style guidelines
- Testing requirements
- Pull request process
- Development setup

### Reporting Issues

When reporting issues, please include:
- Error messages and stack traces
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Python version, etc.)
- Relevant log excerpts

## Learning Path

Recommended learning path for new users:

### Week 1: Basic Understanding
1. Read [Installation Guide](installation.md)
2. Install and start all services
3. Read [User Guide](user-guide.md)
4. Submit simple test tasks
5. Review [API Reference](api-reference.md)

### Week 2: Advanced Usage
1. Study [Architecture Design](architecture.md)
2. Deploy workers on multiple machines
3. Experiment with different task types
4. Use checkpoint review system
5. Integrate with your CI/CD pipeline

### Week 3: Customization
1. Read [Database Schema](database-schema.md)
2. Understand [Redis Schema](redis-schema.md)
3. Customize evaluation criteria
4. Implement custom AI tool adapters
5. Contribute improvements

## Frequently Asked Questions

**Q: Can I use my own AI models?**
A: Yes! Implement a custom tool adapter in the worker agent. See [Architecture Design](architecture.md) for details.

**Q: How many workers can I deploy?**
A: The system is designed to support 10+ workers, but can scale further with proper resource allocation.

**Q: What happens if a worker crashes?**
A: The backend detects worker failures via heartbeat timeout and automatically reassigns tasks to other workers.

**Q: Can I run this in production?**
A: Yes, but implement proper security (JWT auth, HTTPS, firewalls) and monitoring first.

**Q: How do I add a new task type?**
A: Modify the task decomposer service to add new decomposition templates. See [Review Workflow Guide](REVIEW-WORKFLOW-GUIDE.md).

**Q: Can I use without Docker?**
A: Yes! See manual installation in [Installation Guide](installation.md).

## Changelog

For project updates and changes, see:
- [CHANGES.md](../CHANGES.md) - Version history
- [Sprint Completion Reports](sprint-1-completion-report.md) - Sprint summaries

## Additional Resources

### Blog Posts
- [Sprint 1 Backend Foundation](blog-sprint1-backend-foundation.md) - English
- [Sprint 1 後端基礎建設](blog-sprint1-backend-foundation-zh-TW.md) - 繁體中文

### Implementation Summaries
- [Epic 6 Implementation](EPIC-6-IMPLEMENTATION.md)
- [WebSocket Implementation](../WEBSOCKET_IMPLEMENTATION_SUMMARY.md)
- [Error Handling Summary](../STORY-9.3-ERROR-HANDLING-SUMMARY.md)

## License

[To be determined]

---

**Documentation Version**: 1.0.0
**Last Updated**: 2025-12-08
**Platform Version**: 1.0.0-beta

For the latest documentation, visit the [GitHub repository](https://github.com/your-repo/multi-agent-web).
