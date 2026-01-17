# End-to-End Test Suite

This directory contains comprehensive end-to-end (E2E) tests for the BMAD (Backend for Multi-Agent Development) system.

## Overview

The E2E test suite validates the complete system workflow from worker registration through task completion, including all major features:

- Worker lifecycle management
- Task submission and decomposition
- Parallel task execution
- Agent review workflow
- Automated evaluation
- Checkpoint and user decision system

## Test Structure

### Test Files

1. **test_worker_lifecycle.py** (10 tests)
   - Worker registration and idempotency
   - Heartbeat mechanism
   - Resource monitoring
   - Graceful shutdown
   - Worker filtering and listing

2. **test_task_execution.py** (14 tests)
   - Task creation and submission
   - Task decomposition into subtasks
   - Task progress tracking
   - Task cancellation
   - Status querying and filtering
   - Validation and error handling

3. **test_parallel_execution.py** (10 tests)
   - Parallel subtask execution
   - DAG dependency resolution
   - Dependency blocking
   - Multi-worker parallel execution
   - Concurrent allocation
   - Sequential chains and mixed execution

4. **test_review_workflow.py** (10 tests)
   - Review subtask auto-creation
   - Review result processing
   - Auto-fix workflow for low scores
   - Review cycle limits
   - Worker assignment (different reviewers)
   - Correction records

5. **test_evaluation.py** (12 tests)
   - Evaluation creation and scoring
   - Weighted score calculation
   - Passing/failing thresholds
   - Critical security issue detection
   - Partial scores
   - Multiple evaluations per subtask
   - Score aggregation
   - API integration

6. **test_checkpoint.py** (14 tests)
   - Checkpoint creation based on frequency
   - User decisions (accept/correct/reject)
   - Correction record creation
   - Checkpoint history and statistics
   - Different checkpoint frequencies
   - Evaluation summaries in checkpoints

**Total: 69 E2E tests**

## Fixtures and Helpers

### conftest.py

The `conftest.py` file provides comprehensive fixtures for E2E testing:

#### Factory Fixtures

- **WorkerFactory**: Create and manage test workers
  - `create_worker()`: Register workers via API
  - Automatic cleanup on teardown

- **TaskFactory**: Create and manage test tasks
  - `create_task()`: Submit tasks via API
  - `decompose_task()`: Decompose into subtasks
  - `get_task_details()`: Retrieve task information
  - Automatic cleanup on teardown

- **SubtaskFactory**: Manage subtasks
  - `submit_result()`: Submit subtask results
  - `get_subtask_details()`: Retrieve subtask information

- **EvaluationFactory**: Create evaluations
  - `create_evaluation()`: Create evaluation records directly

#### Sample Data Fixtures

- `sample_code_output`: Mock code generation output
- `sample_review_output`: Mock code review output
- `sample_test_output`: Mock test generation output

#### Helper Functions

- `wait_for_task_status()`: Poll task until reaching expected status
- `wait_for_subtask_status()`: Poll subtask until reaching expected status

## Running E2E Tests

### Prerequisites

1. **Database**: PostgreSQL must be running and accessible
   ```bash
   # Default connection:
   postgresql+asyncpg://postgres:postgres@postgres:5432/multi_agent_test
   ```

2. **Environment**: Set `DATABASE_URL` if using different connection

### Run All E2E Tests

```bash
# From backend directory
pytest tests/e2e/ -v -m e2e
```

### Run Specific Test File

```bash
pytest tests/e2e/test_worker_lifecycle.py -v
pytest tests/e2e/test_task_execution.py -v
pytest tests/e2e/test_parallel_execution.py -v
pytest tests/e2e/test_review_workflow.py -v
pytest tests/e2e/test_evaluation.py -v
pytest tests/e2e/test_checkpoint.py -v
```

### Run Specific Test

```bash
pytest tests/e2e/test_worker_lifecycle.py::test_worker_registration_flow -v
```

### Run with Coverage

```bash
pytest tests/e2e/ -v -m e2e --cov=src --cov-report=html
```

### Run in Docker

```bash
# From project root
docker-compose run --rm backend pytest tests/e2e/ -v -m e2e
```

## Test Scenarios

### 1. Worker Lifecycle Scenarios

- **Basic Registration**: Worker registers with system info and tools
- **Idempotent Registration**: Same worker can re-register without duplication
- **Heartbeat Updates**: Worker sends periodic heartbeats with resource usage
- **Status Transitions**: Worker transitions between idle/busy/online/offline
- **Graceful Shutdown**: Worker unregisters cleanly

### 2. Task Execution Scenarios

- **Task Submission**: User submits task with description and requirements
- **Decomposition**: Task is broken down into subtasks based on type
- **Progress Tracking**: Task progress updates as subtasks complete
- **Cancellation**: User can cancel pending or in-progress tasks
- **Status Queries**: Real-time status available via API

### 3. Parallel Execution Scenarios

- **Independent Parallel**: Multiple subtasks without dependencies execute simultaneously
- **DAG Dependencies**: Subtasks execute in correct order based on dependencies
- **Dependency Blocking**: Dependent subtasks wait for prerequisites
- **Multi-Worker**: Multiple workers execute different subtasks in parallel
- **Mixed Execution**: Some subtasks run in parallel, others sequentially

### 4. Review Workflow Scenarios

- **Auto-Review**: Review subtask created after code generation
- **High Score Pass**: Good code passes review without fixes
- **Low Score Fix**: Poor code triggers auto-fix workflow
- **Review Cycles**: Multiple review-fix cycles with limits
- **Different Reviewer**: Review assigned to different agent

### 5. Evaluation Scenarios

- **Multi-Dimensional**: Code quality, completeness, security, architecture, testability
- **Weighted Scoring**: Security weighted 2x, code quality/completeness 1.5x
- **Threshold Detection**: Scores below 7.0 trigger actions
- **Critical Issues**: Security issues below 7.0 flagged as critical
- **Aggregation**: Task-level aggregation of subtask evaluations

### 6. Checkpoint Scenarios

- **Frequency-Based**: Checkpoints created based on configured frequency
- **User Decisions**: Accept (continue), Correct (request fixes), Reject (cancel)
- **Correction Workflow**: Corrections create new fix subtasks
- **History Tracking**: Complete checkpoint history with statistics
- **Evaluation Context**: Checkpoints include evaluation data for informed decisions

## Test Design Principles

### 1. Isolation

- Each test is independent
- Factories handle cleanup automatically
- Database reset between tests via fixtures

### 2. Realism

- Tests use actual API endpoints
- Real database transactions
- Authentic data flows through system

### 3. Coverage

- Happy paths and error cases
- Edge cases and boundary conditions
- Concurrent and sequential scenarios

### 4. Maintainability

- Factories reduce test code duplication
- Clear test names describe scenarios
- Comprehensive assertions verify behavior

### 5. Documentation

- Tests serve as executable documentation
- Each test demonstrates a user scenario
- Comments explain complex setups

## Expected Behavior

### Database Connection

E2E tests require a running PostgreSQL database. If tests fail with connection errors:

1. **Check database is running**:
   ```bash
   docker-compose ps postgres
   ```

2. **Verify connection string**:
   ```bash
   echo $DATABASE_URL
   ```

3. **Run in Docker environment**:
   ```bash
   docker-compose run --rm backend pytest tests/e2e/
   ```

### Test Markers

All E2E tests are marked with `@pytest.mark.e2e`:

```bash
# Run only E2E tests
pytest -m e2e

# Run all except E2E tests
pytest -m "not e2e"

# Run E2E tests for specific component
pytest -m e2e tests/e2e/test_worker_lifecycle.py
```

## Coverage Goals

The E2E test suite aims for:

- **Breadth**: Cover all major system features
- **Depth**: Test both happy paths and error cases
- **Integration**: Verify components work together correctly
- **Regression**: Catch breaking changes across system

**Current Coverage**: 69 comprehensive E2E tests covering 6 major areas

## Continuous Integration

E2E tests should be run:

- **On every PR**: Verify changes don't break system workflows
- **Before deployment**: Final validation before production
- **Nightly**: Full system integration verification

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL environment variable
   - Verify network connectivity in Docker

2. **Tests Timeout**
   - Increase timeout in pytest.ini
   - Check for deadlocks in database
   - Verify Redis is accessible

3. **Intermittent Failures**
   - May indicate race conditions
   - Use wait_for_* helpers for async operations
   - Check transaction isolation levels

4. **Import Errors**
   - Verify all models are imported in `__init__.py`
   - Check PYTHONPATH includes src directory
   - Ensure dependencies are installed

## Future Enhancements

Potential additions to E2E test suite:

1. **WebSocket Tests**: Real-time update streaming
2. **Performance Tests**: Load testing with many workers/tasks
3. **Failure Recovery**: Test system recovery from failures
4. **Multi-Tenancy**: Test user isolation and permissions
5. **API Rate Limiting**: Test rate limit enforcement
6. **Long-Running Tasks**: Test checkpoint behavior in extended workflows

## Contributing

When adding new E2E tests:

1. **Use Factories**: Leverage existing factories for setup
2. **Mark Tests**: Add `@pytest.mark.e2e` decorator
3. **Document Scenarios**: Add docstring explaining test scenario
4. **Clean Up**: Ensure proper cleanup via factories
5. **Assertions**: Verify all important state changes
6. **Coverage**: Aim to increase overall coverage

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [SQLAlchemy AsyncIO](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
