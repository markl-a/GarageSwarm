# Contributing to Multi-Agent on the Web

Thank you for contributing to the BMAD-METHOD Multi-Agent Orchestration Platform! This guide will help you get started with development.

## Development Environment Setup

### Prerequisites

- **Python**: 3.11+
- **Node.js**: 18+ (for frontend tooling)
- **Flutter**: 3.16+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.30+
- **Make**: For running development commands

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bmad-test
   ```

2. **Install pre-commit hooks**
   ```bash
   make install-hooks
   ```

3. **Set up Python environments**

   Backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

   Worker Agent:
   ```bash
   cd worker-agent
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp backend/.env.example backend/.env
   cp worker-agent/config/agent.yaml.example worker-agent/config/agent.yaml
   ```

   Edit the files with your API keys and settings.

5. **Install Flutter dependencies**
   ```bash
   cd frontend
   flutter pub get
   ```

## Development Workflow

### Starting Services

**Using Docker (Recommended):**
```bash
make up          # Start all services
make logs        # View logs
make down        # Stop all services
```

**Local Development:**
```bash
# Terminal 1 - Backend
make dev-backend

# Terminal 2 - Frontend
make dev-frontend

# Terminal 3 - Worker Agent
make dev-worker
```

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following the style guide
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests**
   ```bash
   make test              # All tests
   make test-backend      # Backend only
   make test-worker       # Worker only
   ```

4. **Format and lint**
   ```bash
   make format            # Auto-format code
   make lint              # Check for issues
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Pre-commit hooks will automatically run and format your code.

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

### Python (Backend & Worker Agent)

- **Formatting**: Use `black` with 100 character line length
- **Imports**: Use `isort` with black profile
- **Linting**: Follow `pylint` recommendations
- **Type hints**: Use type annotations for function signatures
- **Docstrings**: Use Google-style docstrings

Example:
```python
from typing import List, Optional
from uuid import UUID

async def create_task(
    task_description: str,
    user_id: UUID,
    privacy_level: str = "public"
) -> Task:
    """Create a new task in the system.

    Args:
        task_description: Natural language description of the task
        user_id: UUID of the user creating the task
        privacy_level: Privacy level (public, private, team)

    Returns:
        Task: The created task object

    Raises:
        ValueError: If privacy_level is invalid
    """
    # Implementation
```

### Flutter (Frontend)

- **Formatting**: Use `flutter format` with 100 character line length
- **Linting**: Follow `flutter analyze` recommendations
- **State Management**: Use Riverpod providers
- **Widgets**: Prefer stateless widgets when possible
- **Naming**: Use camelCase for variables, PascalCase for classes

Example:
```dart
class TaskListProvider extends StateNotifier<AsyncValue<List<Task>>> {
  TaskListProvider(this._taskService) : super(const AsyncValue.loading()) {
    loadTasks();
  }

  final TaskService _taskService;

  Future<void> loadTasks() async {
    state = const AsyncValue.loading();
    try {
      final tasks = await _taskService.fetchTasks();
      state = AsyncValue.data(tasks);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}
```

## Project Structure

```
bmad-test/
├── backend/              # FastAPI Backend
│   ├── src/
│   │   ├── api/         # REST API endpoints
│   │   ├── services/    # Business logic
│   │   ├── models/      # SQLAlchemy models
│   │   ├── repositories/# Data access layer
│   │   └── evaluators/  # Evaluation framework
│   └── tests/
├── frontend/             # Flutter Frontend
│   ├── lib/
│   │   ├── screens/     # UI screens
│   │   ├── widgets/     # Reusable widgets
│   │   ├── providers/   # State management
│   │   └── services/    # API clients
│   └── test/
├── worker-agent/         # Worker Agent SDK
│   ├── src/
│   │   ├── agent/       # Agent core
│   │   └── tools/       # AI tool adapters
│   └── tests/
└── docs/                 # Documentation
```

## Testing Guidelines

### Writing Tests

- **Coverage**: Aim for >80% code coverage
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test interactions between components
- **E2E Tests**: Test complete user workflows (frontend)

### Backend Tests (pytest)

```python
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_create_task(task_service, mock_db):
    """Test task creation with valid input."""
    task_id = uuid4()
    description = "Build user authentication"

    task = await task_service.create_task(
        task_id=task_id,
        description=description
    )

    assert task.task_id == task_id
    assert task.description == description
    assert task.status == "pending"
```

### Frontend Tests (Flutter)

```dart
testWidgets('TaskCard displays task information', (tester) async {
  final task = Task(
    id: '123',
    title: 'Test Task',
    status: TaskStatus.inProgress,
  );

  await tester.pumpWidget(
    MaterialApp(home: TaskCard(task: task)),
  );

  expect(find.text('Test Task'), findsOneWidget);
  expect(find.byType(CircularProgressIndicator), findsOneWidget);
});
```

## Database Migrations

### Creating Migrations

```bash
make migrate-create
# Enter migration message when prompted
```

### Applying Migrations

```bash
make migrate
```

### Migration Best Practices

- One migration per logical change
- Always test migrations on development database first
- Include both `upgrade()` and `downgrade()` functions
- Never edit applied migrations

## API Documentation

- **Backend API**: http://localhost:8000/docs (Swagger UI)
- **Architecture**: See `docs/architecture.md`
- **Sprint Plan**: See `docs/sprint-1-plan.md`

## Debugging

### Backend Debugging

Add breakpoints and use debugpy:
```python
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

### Worker Agent Debugging

Check logs:
```bash
tail -f worker-agent/logs/worker-agent.log
```

### Docker Container Debugging

```bash
make shell-backend     # Access backend container
make shell-worker      # Access worker container
make logs              # View all logs
```

## Common Issues

### Pre-commit Hooks Fail

```bash
# Re-install hooks
pre-commit uninstall
make install-hooks

# Run manually to see errors
pre-commit run --all-files
```

### Database Connection Errors

- Check PostgreSQL is running: `docker-compose ps`
- Verify DATABASE_URL in `.env`
- Check migrations are applied: `make migrate`

### Worker Agent Not Connecting

- Verify backend_url in `config/agent.yaml`
- Check backend health: `curl http://localhost:8000/health`
- Verify API keys are set in environment

## Code Review Process

1. **Self-review**: Check your own PR before requesting review
2. **Tests**: Ensure all tests pass
3. **Coverage**: Maintain or improve code coverage
4. **Documentation**: Update docs for API changes
5. **PR Description**: Clearly describe what and why

## Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

Examples:
```
feat: add task evaluation service
fix: resolve worker heartbeat timeout issue
docs: update API documentation for task endpoints
refactor: extract task allocation logic to separate service
```

## Getting Help

- **Architecture Questions**: See `docs/architecture.md`
- **Sprint Planning**: See `docs/sprint-1-plan.md`
- **Issues**: Create a GitHub issue
- **Discussions**: Use GitHub Discussions

## Security

- Never commit API keys or secrets
- Use environment variables for sensitive data
- Report security issues privately to maintainers
- Follow OWASP top 10 guidelines

## License

This project is licensed under the MIT License. See LICENSE file for details.
