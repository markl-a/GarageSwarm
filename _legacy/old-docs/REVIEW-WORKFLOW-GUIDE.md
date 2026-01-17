# Code Review Workflow - Developer Guide

Quick reference for using the agent collaboration and review mechanism.

## Quick Start

### 1. Trigger a Code Review

```python
from src.services import ReviewService

review_service = ReviewService(db_session, redis_service)

# After code generation completes
review_subtask = await review_service.create_review_subtask(
    original_subtask_id=completed_subtask_id,
    review_cycle=1
)
```

### 2. Submit Review Results

```python
# Agent performs review and returns structured JSON
review_output = {
    "score": 7.5,  # 0-10 scale
    "issues": [
        {
            "dimension": "security",       # syntax|style|logic|security|readability
            "severity": "high",            # high|medium|low
            "description": "SQL injection risk in login function",
            "location": "auth/login.py:45",
            "example": "cursor.execute(f'SELECT * FROM users WHERE id={user_id}')"
        }
    ],
    "suggestions": [
        {
            "dimension": "style",
            "description": "Add type hints to function parameters",
            "example": "def login(username: str, password: str) -> bool:"
        }
    ],
    "summary": "Good implementation with one critical security issue"
}

score, needs_fix = await review_service.parse_and_store_review_result(
    review_subtask_id=review_subtask.subtask_id,
    review_output=review_output
)

if needs_fix:
    # Auto-fix will be triggered (score < 6.0)
    print(f"Score {score} below threshold, creating fix task")
```

### 3. Handle Auto-Fix Flow

```python
# System automatically creates fix subtask when score < 6.0
fix_subtask = await review_service.create_fix_subtask(
    original_subtask_id=original_subtask_id,
    review_subtask_id=review_subtask_id,
    review_cycle=1
)

# After fix completes, trigger re-review
rereview = await review_service.handle_fix_completion(
    fix_subtask_id=fix_subtask.subtask_id
)

# If rereview is None, max cycles reached → escalated to human
```

### 4. Track Review Chain

```python
# Get complete review history
chain = await review_service.get_review_chain(original_subtask_id)

for entry in chain:
    print(f"Cycle {entry['review_cycle']}: {entry['subtask_type']}")
    if entry['subtask_type'] == 'code_review':
        print(f"  Score: {entry['score']}")
        print(f"  Issues: {entry['issues_count']}")
```

## Parallel Execution

### Coordinate Parallel Tasks

```python
from src.services import TaskScheduler

scheduler = TaskScheduler(db_session, redis_service)

# View parallelizable levels
levels = await scheduler.identify_parallelizable_subtasks(task_id)
print(f"Task has {len(levels)} dependency levels")
for i, level in enumerate(levels):
    print(f"Level {i}: {len(level)} subtasks (can run in parallel)")

# Execute with coordination
results = await scheduler.coordinate_parallel_execution(task_id)
print(f"Completed: {results['total_subtasks_completed']}")
print(f"Failed: {results['total_subtasks_failed']}")
```

### Get Execution Statistics

```python
stats = await scheduler.get_parallel_execution_stats(task_id)
print(f"Max parallelism: {stats['max_parallelism']} simultaneous tasks")
print(f"Total levels: {stats['parallel_levels']}")
print(f"Status: {stats['status_counts']}")
```

## Review Score Guidelines

| Score | Meaning | Action |
|-------|---------|--------|
| 9-10  | Exceptional, production-ready | Accept immediately |
| 7-8   | Good quality, minor improvements | Accept with suggestions |
| 5-6   | Acceptable, moderate issues | Fix recommended |
| 3-4   | Poor quality, significant issues | **Auto-fix triggered** |
| 0-2   | Unacceptable, major rework | **Auto-fix triggered** |

**Threshold:** Score < 6.0 triggers automatic fix cycle

## Configuration

```python
# Get current configuration
config = review_service.get_review_config()

print(f"Score threshold: {config['score_threshold']}")  # 6.0
print(f"Max fix cycles: {config['max_fix_cycles']}")    # 2
print(f"Dimensions: {config['review_dimensions']}")
# ['syntax', 'style', 'logic', 'security', 'readability']
```

## Subtask Types

When creating subtasks, specify `subtask_type`:

- `code_generation`: Original code generation tasks
- `code_review`: Review tasks (auto-created)
- `code_fix`: Fix tasks (auto-created when score < 6.0)
- `test`: Test generation/execution
- `documentation`: Documentation tasks
- `analysis`: Analysis tasks
- `deployment`: Deployment tasks

```python
subtask = Subtask(
    task_id=task_id,
    name="Implement user authentication",
    description="Create JWT-based auth",
    subtask_type="code_generation",  # Specify type
    status="pending"
)
```

## Review Workflow States

```
┌─────────────────┐
│ Code Generation │
│  (Agent 1)      │
└────────┬────────┘
         │ completes
         ▼
┌─────────────────┐
│  Code Review    │
│  (Agent 2)      │
└────────┬────────┘
         │ score?
         ├─────────► score >= 6.0 → ✓ Accept
         │
         └─────────► score < 6.0
                     │
                     ▼
            ┌─────────────────┐
            │   Code Fix      │
            │  (Agent 1)      │
            └────────┬────────┘
                     │ completes
                     ▼
            ┌─────────────────┐
            │  Re-review      │
            │  (Agent 2)      │
            └────────┬────────┘
                     │ score?
                     ├─────────► score >= 6.0 → ✓ Accept
                     │
                     └─────────► score < 6.0 & cycle >= 2
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ Human Escalation │
                        │ (Manual Review)  │
                        └──────────────────┘
```

## Error Handling

### Review Creation Errors

```python
try:
    review = await review_service.create_review_subtask(subtask_id)
except ValueError as e:
    if "not completed" in str(e):
        print("Wait for subtask to complete first")
    elif "no output" in str(e):
        print("Subtask has no output to review")
    elif "not found" in str(e):
        print("Subtask doesn't exist")
```

### Review Parsing Errors

```python
try:
    score, needs_fix = await review_service.parse_and_store_review_result(
        review_subtask_id, review_output
    )
except ValueError as e:
    if "missing 'score'" in str(e):
        print("Review must include score field")
    elif "out of range" in str(e):
        print("Score must be between 0 and 10")
    elif "Invalid review output format" in str(e):
        print("Review must be valid JSON")
```

## Best Practices

### 1. Review Creation
- Only create reviews for completed subtasks
- Ensure subtask has output to review
- Use cycle parameter to track iterations

### 2. Review Scoring
- Be consistent with scoring criteria
- Document reasoning in summary
- Include specific locations for issues
- Provide actionable suggestions

### 3. Fix Implementation
- Address all high-severity issues
- Consider medium-severity issues
- Maintain original functionality
- Add tests for fixed issues

### 4. Parallel Execution
- Design subtasks with minimal dependencies
- Group independent work at same level
- Balance complexity across levels
- Monitor resource utilization

## Common Patterns

### Pattern 1: Review + Fix + Re-review

```python
# 1. Complete code generation
await complete_subtask(code_subtask_id)

# 2. Create review
review = await review_service.create_review_subtask(code_subtask_id)

# 3. Perform review (simulated)
review_output = perform_code_review(review)

# 4. Store results
score, needs_fix = await review_service.parse_and_store_review_result(
    review.subtask_id, review_output
)

# 5. If needs fix, create fix task
if needs_fix:
    fix = await review_service.create_fix_subtask(
        code_subtask_id, review.subtask_id, review_cycle=1
    )

    # 6. After fix, trigger re-review
    rereview = await review_service.handle_fix_completion(fix.subtask_id)
```

### Pattern 2: Bulk Parallel Review

```python
# Get all completed code generation subtasks
completed = await get_completed_code_subtasks(task_id)

# Create reviews for all in parallel
reviews = []
for subtask in completed:
    review = await review_service.create_review_subtask(subtask.subtask_id)
    reviews.append(review)

# Allocate to different workers for parallel execution
scheduler = TaskScheduler(db_session, redis_service)
results = await scheduler.coordinate_parallel_execution(task_id)
```

### Pattern 3: Progressive Enhancement

```python
# Cycle 1: Focus on critical issues
review_1 = {
    "score": 4.0,
    "issues": [{"severity": "high", "dimension": "security", ...}],
    "summary": "Fix security issues first"
}

# Cycle 2: Address style and optimization
review_2 = {
    "score": 7.5,
    "issues": [{"severity": "low", "dimension": "style", ...}],
    "summary": "Security fixed, style improvements suggested"
}
```

## Integration with Worker Agents

### Loading Prompts

```python
from jinja2 import Environment, FileSystemLoader

def load_review_prompt(subtask_data):
    env = Environment(loader=FileSystemLoader('worker-agent/src/prompts'))
    template = env.get_template('code_review.txt')

    return template.render(
        original_subtask_name=subtask_data['name'],
        original_description=subtask_data['description'],
        code_output=subtask_data['output'],
        review_cycle=subtask_data['metadata']['review_cycle'],
        review_dimensions=['syntax', 'style', 'logic', 'security', 'readability']
    )
```

## Troubleshooting

### Issue: Reviews not being created

**Check:**
1. Subtask status is "completed"
2. Subtask has output data
3. Database migration 002 applied
4. ReviewService properly initialized

### Issue: Auto-fix not triggering

**Check:**
1. Review score < 6.0
2. Review result properly stored
3. Cycle count < MAX_FIX_CYCLES
4. Original subtask accessible

### Issue: Parallel execution slow

**Check:**
1. Worker availability
2. Dependency structure (too linear?)
3. Resource limits (MAX_CONCURRENT_SUBTASKS)
4. Network latency between workers

## Performance Tips

1. **Batch Operations**: Create multiple reviews at once
2. **Async Execution**: Use async/await for all I/O
3. **Caching**: Cache review templates and configurations
4. **Monitoring**: Track review times and scores
5. **Load Balancing**: Distribute reviews across workers evenly

## Additional Resources

- Full implementation: `docs/EPIC-6-IMPLEMENTATION.md`
- Review service code: `backend/src/services/review_service.py`
- Test examples: `backend/tests/unit/test_review_service.py`
- Prompt templates: `worker-agent/src/prompts/`

## Support

For issues or questions:
1. Check test files for usage examples
2. Review implementation documentation
3. Check service method docstrings
4. Examine test fixtures for setup patterns
