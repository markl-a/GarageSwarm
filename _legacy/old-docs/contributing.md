# Contributing to Multi-Agent on the Web

Thank you for your interest in contributing to the Multi-Agent on the Web platform! This guide will help you understand our development process and how to contribute effectively.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)
- [Release Process](#release-process)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in your interactions.

### Our Standards

**Positive behaviors:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Project maintainers have the right and responsibility to remove, edit, or reject comments, commits, code, issues, and other contributions that don't align with this Code of Conduct.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check the existing issues to avoid duplicates.

**When reporting a bug, include:**

1. **Clear title**: Describe the issue concisely
2. **Environment details**:
   - OS: Windows 10, macOS 13, Ubuntu 22.04, etc.
   - Python version: `python --version`
   - Flutter version (if frontend): `flutter --version`
   - Installation method: Docker, manual, etc.

3. **Steps to reproduce**:
   ```
   1. Go to '...'
   2. Click on '....'
   3. Scroll down to '....'
   4. See error
   ```

4. **Expected behavior**: What you expected to happen
5. **Actual behavior**: What actually happened
6. **Screenshots**: If applicable
7. **Logs**: Relevant error logs
   ```
   # Backend logs
   docker-compose logs backend

   # Worker logs
   cat worker-agent/logs/worker-agent.log
   ```

**Bug Report Template:**

```markdown
## Bug Description
A clear and concise description of what the bug is.

## Environment
- OS: [e.g., Windows 10]
- Python: [e.g., 3.11.5]
- Backend version: [e.g., 1.0.0]

## Steps to Reproduce
1. ...
2. ...
3. ...

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Logs
```
Paste relevant logs here
```

## Screenshots
If applicable, add screenshots.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.

**When suggesting an enhancement, include:**

1. **Use case**: Why is this enhancement needed?
2. **Proposed solution**: How should it work?
3. **Alternatives considered**: Other approaches you've thought about
4. **Impact**: Who will benefit from this?

**Enhancement Template:**

```markdown
## Problem Statement
Describe the problem this enhancement solves.

## Proposed Solution
Describe your proposed solution.

## Alternatives Considered
Describe alternative solutions you've considered.

## Additional Context
Any other context, mockups, or examples.
```

### Contributing Code

We welcome code contributions! Here's how to get started:

1. **Find an issue**: Look for issues tagged `good first issue` or `help wanted`
2. **Claim the issue**: Comment that you'd like to work on it
3. **Fork the repo**: Create your own fork
4. **Create a branch**: Use descriptive branch names
5. **Make changes**: Follow our code standards
6. **Write tests**: Ensure your code is tested
7. **Submit PR**: Create a pull request

## Development Setup

Please refer to our detailed [Development Guide](./development.md) for complete setup instructions.

**Quick Start:**

```bash
# Clone repository
git clone <repository-url>
cd bmad-test

# Install dependencies
make install

# Start services
make up

# Run tests
make test
```

## Development Workflow

### 1. Create a Feature Branch

Use descriptive branch names following this convention:

```bash
# Feature branches
git checkout -b feature/add-task-priority

# Bug fix branches
git checkout -b fix/worker-heartbeat-timeout

# Documentation branches
git checkout -b docs/update-api-reference

# Refactoring branches
git checkout -b refactor/extract-allocation-service
```

### 2. Make Your Changes

**Before you start coding:**
- Review existing code to understand patterns
- Check if similar functionality exists
- Consider edge cases and error handling

**While coding:**
- Write clean, readable code
- Add comments for complex logic
- Follow the project's architecture patterns
- Keep changes focused and atomic

### 3. Write Tests

**Test Requirements:**
- New features must include tests
- Bug fixes should include regression tests
- Aim for >80% code coverage
- Test both success and failure cases

**Example Test:**

```python
# backend/tests/unit/test_task_service.py
import pytest
from uuid import uuid4
from src.services.task_service import TaskService

@pytest.mark.asyncio
async def test_create_task_success(mock_db, mock_redis):
    """Test successful task creation"""
    service = TaskService(mock_db, mock_redis)

    task_data = {
        "description": "Build user authentication",
        "checkpoint_frequency": "medium"
    }

    task = await service.create_task(task_data)

    assert task.task_id is not None
    assert task.description == task_data["description"]
    assert task.status == "pending"
    assert task.progress == 0

@pytest.mark.asyncio
async def test_create_task_invalid_description(mock_db, mock_redis):
    """Test task creation with invalid description"""
    service = TaskService(mock_db, mock_redis)

    with pytest.raises(ValueError, match="Description too short"):
        await service.create_task({"description": "Hi"})
```

### 4. Run Code Quality Checks

```bash
# Format code
make format

# Run linters
make lint

# Type check
mypy backend/src

# Run tests
make test

# Check coverage
pytest --cov=src --cov-report=term-missing
```

### 5. Commit Your Changes

See [Commit Guidelines](#commit-guidelines) below.

### 6. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create PR on GitHub
# Fill in the PR template
```

## Code Standards

### Python Code Standards

We follow **PEP 8** with some modifications.

#### Formatting

**Tool:** `black` with 100 character line length

```bash
# Format code
black backend/src backend/tests

# Check formatting
black --check backend/src
```

**Configuration (pyproject.toml):**

```toml
[tool.black]
line-length = 100
target-version = ['py311']
```

#### Import Sorting

**Tool:** `isort` with black profile

```bash
# Sort imports
isort backend/src backend/tests

# Check import order
isort --check-only backend/src
```

**Configuration (pyproject.toml):**

```toml
[tool.isort]
profile = "black"
line_length = 100
```

#### Linting

**Tool:** `pylint`

```bash
# Run pylint
pylint backend/src

# Disable specific warnings (sparingly)
# pylint: disable=line-too-long
```

**Common Rules:**
- Maximum line length: 100 characters
- Maximum function length: 50 lines (guideline)
- Maximum function arguments: 5
- Avoid wildcard imports (`from module import *`)
- Use explicit exception handling

#### Type Hints

Use type hints for all function signatures:

```python
from typing import List, Optional, Dict, Any
from uuid import UUID

async def get_task(
    task_id: UUID,
    include_subtasks: bool = False
) -> Optional[Dict[str, Any]]:
    """Get task by ID"""
    # Implementation
    pass
```

#### Docstrings

Use **Google-style docstrings**:

```python
def calculate_allocation_score(
    worker: Worker,
    subtask: Subtask,
    weights: Dict[str, float]
) -> float:
    """Calculate allocation score for worker-subtask pair.

    The score is a weighted sum of tool match, resource availability,
    and privacy compliance.

    Args:
        worker: Worker instance to evaluate
        subtask: Subtask to allocate
        weights: Dictionary of weight values for each factor
            - tool_match: Weight for tool compatibility (0.0-1.0)
            - resources: Weight for resource availability (0.0-1.0)
            - privacy: Weight for privacy compliance (0.0-1.0)

    Returns:
        Float score between 0.0 and 10.0, higher is better

    Raises:
        ValueError: If weights don't sum to 1.0

    Example:
        >>> worker = Worker(...)
        >>> subtask = Subtask(...)
        >>> score = calculate_allocation_score(
        ...     worker, subtask,
        ...     {"tool_match": 0.5, "resources": 0.3, "privacy": 0.2}
        ... )
        >>> print(f"Score: {score:.2f}")
        Score: 8.50
    """
    # Implementation
    pass
```

### Flutter/Dart Code Standards

#### Formatting

**Tool:** `dart format`

```bash
# Format code
dart format lib/

# Check formatting
dart format --output=none --set-exit-if-changed lib/
```

#### Linting

**Tool:** `flutter analyze`

```bash
# Run analyzer
flutter analyze

# Fix auto-fixable issues
dart fix --apply
```

**Configuration (analysis_options.yaml):**

```yaml
include: package:flutter_lints/flutter.yaml

linter:
  rules:
    - always_declare_return_types
    - avoid_print
    - prefer_const_constructors
    - use_key_in_widget_constructors
```

#### Naming Conventions

- **Classes**: PascalCase (`TaskListWidget`, `ApiService`)
- **Files**: snake_case (`task_list_widget.dart`, `api_service.dart`)
- **Variables**: camelCase (`taskId`, `isLoading`)
- **Constants**: camelCase with `const` (`const apiTimeout = 30`)
- **Private members**: prefix with `_` (`_handleTap`, `_apiClient`)

#### Widget Structure

```dart
class TaskCard extends ConsumerWidget {
  const TaskCard({
    super.key,
    required this.task,
    this.onTap,
  });

  final Task task;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      child: ListTile(
        title: Text(task.description),
        subtitle: Text('Status: ${task.status}'),
        onTap: onTap,
      ),
    );
  }
}
```

### SQL/Database Standards

#### Migration Files

```python
"""Add task priority field

Revision ID: 003
Revises: 002
Create Date: 2025-12-08 15:30:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002'

def upgrade():
    """Add priority column to tasks table"""
    op.add_column(
        'tasks',
        sa.Column('priority', sa.Integer(), nullable=False, server_default='50')
    )
    op.create_index('ix_tasks_priority', 'tasks', ['priority'])

def downgrade():
    """Remove priority column from tasks table"""
    op.drop_index('ix_tasks_priority', 'tasks')
    op.drop_column('tasks', 'priority')
```

#### Query Optimization

- Use indexes for frequently queried columns
- Avoid N+1 queries (use `joinedload` or `selectinload`)
- Use `EXPLAIN ANALYZE` for slow queries
- Limit result sets with pagination

## Commit Guidelines

We follow **Conventional Commits** specification.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **perf**: Performance improvement
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, build, etc.)
- **ci**: CI/CD changes

### Scope (Optional)

Indicates the area of change:
- `backend`: Backend changes
- `worker`: Worker agent changes
- `frontend`: Frontend changes
- `api`: API changes
- `db`: Database changes
- `docs`: Documentation changes

### Subject

- Use imperative mood ("add feature" not "added feature")
- Don't capitalize first letter
- No period at the end
- Maximum 50 characters

### Body (Optional)

- Explain the "what" and "why", not the "how"
- Wrap at 72 characters
- Separate from subject with blank line

### Footer (Optional)

- Reference issues: `Fixes #123`, `Closes #456`
- Breaking changes: `BREAKING CHANGE: description`

### Examples

**Simple feature:**
```
feat(backend): add task priority field

Add priority field to tasks table to support task ordering.
Priority is an integer from 1-100, default 50.
```

**Bug fix:**
```
fix(worker): resolve heartbeat timeout issue

Increase heartbeat timeout from 30s to 60s to prevent
premature disconnections on slow networks.

Fixes #234
```

**Breaking change:**
```
feat(api): change task status enum values

BREAKING CHANGE: Task status values changed from snake_case
to lowercase. Update clients accordingly.

Old: in_progress, completed
New: inprogress, completed

Closes #345
```

**Multiple changes:**
```
refactor(backend): extract allocation logic to service

- Create TaskAllocator service class
- Move scoring algorithm from scheduler
- Add unit tests for allocation service
- Update API to use new service

Part of #456
```

## Pull Request Process

### Before Submitting

**Checklist:**
- [ ] Code follows style guidelines
- [ ] All tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main branch
- [ ] PR description is clear and complete

### PR Title

Follow commit message convention:

```
feat(backend): add task priority field
fix(worker): resolve heartbeat timeout
docs: update API reference
```

### PR Description Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Fixes #123
Closes #456

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe how you tested your changes:
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing performed

## Screenshots (if applicable)
Add screenshots here.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests pass
```

### Review Process

**What reviewers look for:**

1. **Functionality**: Does it work as intended?
2. **Code quality**: Is the code clean and maintainable?
3. **Tests**: Are there adequate tests?
4. **Documentation**: Is documentation updated?
5. **Performance**: Any performance concerns?
6. **Security**: Any security implications?

**As a contributor:**
- Respond to feedback constructively
- Make requested changes promptly
- Ask questions if feedback is unclear
- Mark conversations as resolved when addressed

**As a reviewer:**
- Be respectful and constructive
- Explain the reasoning behind suggestions
- Distinguish between required changes and suggestions
- Approve when ready or request changes if needed

### Merging

**Requirements for merge:**
- At least 1 approval from maintainer
- All CI checks passing
- No merge conflicts
- All review comments addressed

**Merge strategy:**
- Use "Squash and merge" for feature branches
- Use "Rebase and merge" for hotfixes
- Never use "Merge commit" (creates messy history)

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                  # Unit tests (fast, isolated)
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/           # Integration tests (slower, with DB)
│   ├── test_api.py
│   ├── test_workflows.py
│   └── test_websocket.py
└── e2e/                   # End-to-end tests (slowest, full stack)
    └── test_task_flow.py
```

### Writing Good Tests

**Principles:**
- **Arrange-Act-Assert**: Clear test structure
- **One assertion focus**: Test one thing at a time
- **Descriptive names**: Test name describes what it tests
- **Independent**: Tests don't depend on each other
- **Fast**: Keep tests fast (mock external services)

**Example:**

```python
@pytest.mark.asyncio
async def test_allocator_selects_worker_with_matching_tool(mock_db, mock_redis):
    """
    Given: 2 workers, one with claude_code, one with gemini
    When: Allocating subtask requiring claude_code
    Then: Worker with claude_code is selected
    """
    # Arrange
    worker_claude = create_worker(tools=["claude_code"])
    worker_gemini = create_worker(tools=["gemini_cli"])
    subtask = create_subtask(recommended_tool="claude_code")

    allocator = TaskAllocator(mock_db, mock_redis)

    # Act
    selected = await allocator.allocate_subtask(subtask, [worker_claude, worker_gemini])

    # Assert
    assert selected.worker_id == worker_claude.worker_id
```

### Test Coverage

**Goals:**
- Overall coverage: >80%
- Critical paths: >95%
- New code: >90%

**Check coverage:**

```bash
# Backend
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Worker
cd worker-agent
pytest --cov=src --cov-report=html

# Frontend
cd frontend
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
```

## Documentation Guidelines

### Code Documentation

**Always document:**
- Public APIs and functions
- Complex algorithms
- Non-obvious code
- Configuration options

**Example:**

```python
def calculate_weighted_score(
    scores: Dict[str, float],
    weights: Dict[str, float]
) -> float:
    """Calculate weighted average of scores.

    Uses the formula: sum(score_i * weight_i) / sum(weight_i)

    Args:
        scores: Dictionary mapping dimension names to scores (0.0-10.0)
        weights: Dictionary mapping dimension names to weights (0.0-1.0)

    Returns:
        Weighted average score between 0.0 and 10.0

    Raises:
        ValueError: If scores and weights have different keys
        ZeroDivisionError: If total weight is zero

    Example:
        >>> scores = {"quality": 8.0, "security": 9.0}
        >>> weights = {"quality": 0.6, "security": 0.4}
        >>> calculate_weighted_score(scores, weights)
        8.4
    """
    if scores.keys() != weights.keys():
        raise ValueError("Scores and weights must have same keys")

    total_weight = sum(weights.values())
    if total_weight == 0:
        raise ZeroDivisionError("Total weight cannot be zero")

    weighted_sum = sum(scores[k] * weights[k] for k in scores)
    return weighted_sum / total_weight
```

### README Files

Each major component should have a README:

```
backend/README.md
worker-agent/README.md
frontend/README.md
```

**README structure:**
1. Brief description
2. Installation instructions
3. Usage examples
4. Configuration options
5. Development setup
6. Testing instructions

### Markdown Guidelines

- Use ATX-style headers (`#`, `##`, `###`)
- Include table of contents for long documents
- Use code fences with language identifiers
- Add alt text to images
- Keep lines under 100 characters (for readability)

## Release Process

### Versioning

We use **Semantic Versioning** (SemVer): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. **Update version numbers**:
   - `backend/src/__version__.py`
   - `worker-agent/src/__version__.py`
   - `frontend/pubspec.yaml`

2. **Update CHANGELOG.md**:
   ```markdown
   ## [1.2.0] - 2025-12-08

   ### Added
   - Task priority field (#123)
   - Worker pool visualization (#145)

   ### Fixed
   - Heartbeat timeout issue (#234)
   - WebSocket reconnection bug (#267)

   ### Changed
   - Improved allocation algorithm performance (#189)
   ```

3. **Create release tag**:
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

4. **Build and test**:
   ```bash
   make test
   make build
   ```

5. **Deploy** (if applicable)

6. **Create GitHub release** with release notes

## Getting Help

### Where to Ask Questions

- **GitHub Discussions**: General questions and discussions
- **GitHub Issues**: Bug reports and feature requests
- **Pull Request comments**: Questions about specific code

### Resources

- [Development Guide](./development.md)
- [Architecture Deep Dive](./architecture-deep-dive.md)
- [API Documentation](http://localhost:8000/docs)
- [Sprint Plans](./sprint-1-plan.md)

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing to Multi-Agent on the Web! 🎉
