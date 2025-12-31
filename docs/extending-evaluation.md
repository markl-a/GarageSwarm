# Extending the Evaluation Framework

This guide explains how to add new evaluators to the Multi-Agent on the Web platform's code evaluation framework.

## Table of Contents

- [Overview](#overview)
- [Evaluation Framework Architecture](#evaluation-framework-architecture)
- [BaseEvaluator Interface](#baseevaluator-interface)
- [Creating a New Evaluator](#creating-a-new-evaluator)
- [Example: Performance Evaluator](#example-performance-evaluator)
- [Integrating with Aggregator](#integrating-with-aggregator)
- [Configuring Weights](#configuring-weights)
- [Testing Your Evaluator](#testing-your-evaluator)
- [Best Practices](#best-practices)
- [Common Evaluation Patterns](#common-evaluation-patterns)

## Overview

The evaluation framework provides **quantitative quality assessment** of AI-generated code. It uses a pluggable architecture that allows adding new evaluation dimensions.

### Current Evaluators

| Evaluator | Weight | Evaluates |
|-----------|--------|-----------|
| **CodeQualityEvaluator** | 25% | Syntax, linting, complexity, documentation |
| **CompletenessEvaluator** | 30% | Requirement coverage, implementation completeness |
| **SecurityEvaluator** | 25% | Security vulnerabilities, hardcoded secrets |
| **Reserved** | 20% | Available for custom evaluators |

### Why Add Evaluators?

Add new evaluators to assess:
- **Performance**: Runtime complexity, memory usage
- **Testing**: Test coverage, test quality
- **Architecture**: Design patterns, SOLID principles
- **Accessibility**: WCAG compliance (for frontend)
- **Documentation**: API docs completeness
- **Dependencies**: Security of third-party packages

## Evaluation Framework Architecture

```
┌───────────────────────────────────────────────────────────┐
│            EvaluationAggregator                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  • Runs all evaluators                              │ │
│  │  • Aggregates scores with weights                   │ │
│  │  • Generates overall report                         │ │
│  └─────────────────────────────────────────────────────┘ │
└────────┬────────────┬────────────┬────────────────────────┘
         │            │            │
         ▼            ▼            ▼
  ┌────────────┬────────────┬──────────────┬─────────────┐
  │   Code     │ Complete-  │  Security    │ Performance │
  │  Quality   │   ness     │              │   (NEW)     │
  │            │            │              │             │
  │ Score: 8.5 │ Score: 7.0 │ Score: 9.0   │ Score: 6.5  │
  └────────────┴────────────┴──────────────┴─────────────┘
         │            │            │            │
         └────────────┴────────────┴────────────┘
                      │
                      ▼
              ┌──────────────────┐
              │  Overall Score   │
              │      7.8/10      │
              │   Grade: GOOD    │
              └──────────────────┘
```

## BaseEvaluator Interface

All evaluators must extend `BaseEvaluator`:

```python
# backend/src/evaluators/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from decimal import Decimal

@dataclass
class EvaluationResult:
    """Result of an evaluation"""
    score: Decimal                           # Score 0.0-10.0
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseEvaluator(ABC):
    """Abstract base class for all evaluators"""

    def __init__(self, weight: float = 1.0, config: Optional[Dict[str, Any]] = None):
        """Initialize evaluator

        Args:
            weight: Weight for this evaluator in aggregation (default: 1.0)
            config: Optional configuration dictionary
        """
        self.weight = weight
        self.config = config or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Return evaluator name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return evaluator description"""
        pass

    @abstractmethod
    async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
        """Evaluate code and return result

        Args:
            code: The code to evaluate
            context: Context information including:
                - description: Task/subtask description
                - requirements: List of requirements
                - language: Programming language
                - task_type: Type of task
                - additional context as needed

        Returns:
            EvaluationResult with score, details, and suggestions
        """
        pass
```

### Required Properties

- **name**: Unique identifier for the evaluator (e.g., "performance")
- **description**: Human-readable description

### Required Method

- **evaluate(code, context)**: Performs evaluation and returns `EvaluationResult`

### EvaluationResult Structure

```python
EvaluationResult(
    score=Decimal("7.5"),  # 0.0-10.0
    details={
        "metric1": value1,
        "metric2": value2,
        # ... more metrics
    },
    suggestions=[
        "Consider optimizing loop at line 42",
        "Add caching for expensive computation",
    ],
    issues=[
        {
            "type": "performance",
            "severity": "medium",  # critical, high, medium, low
            "line": 42,
            "message": "O(n²) complexity detected"
        }
    ],
    metadata={
        "execution_time": 1.23,
        "tools_used": ["radon"]
    }
)
```

## Creating a New Evaluator

### Step 1: Create Evaluator File

Create a new file in `backend/src/evaluators/`:

```bash
cd backend/src/evaluators
touch performance.py
```

### Step 2: Implement BaseEvaluator

```python
# backend/src/evaluators/performance.py

"""
Performance Evaluator

Evaluates code performance characteristics including:
- Time complexity analysis
- Space complexity analysis
- Potential bottlenecks
- Optimization opportunities
"""

import ast
import re
from typing import Any, Dict, List, Optional
from decimal import Decimal
import structlog

from .base import BaseEvaluator, EvaluationResult

logger = structlog.get_logger()


class PerformanceEvaluator(BaseEvaluator):
    """
    Evaluates code performance aspects:
    - Time complexity (Big-O)
    - Space complexity
    - Nested loops detection
    - Recursive calls analysis
    - List comprehension vs loops
    """

    @property
    def name(self) -> str:
        return "performance"

    @property
    def description(self) -> str:
        return "Evaluates code performance and computational complexity"

    async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate code performance

        Scoring formula:
        base_score = 10.0
        score = base_score - (nested_loops * 2) - (inefficient_patterns * 1.5) - (complexity_issues * 1)

        Args:
            code: Source code to evaluate
            context: Context including language, description, etc.

        Returns:
            EvaluationResult with performance score and recommendations
        """
        language = context.get("language", "python").lower()

        # Initialize results
        issues = []
        suggestions = []
        details = {
            "time_complexity": "O(n)",  # Estimated
            "space_complexity": "O(1)",  # Estimated
            "nested_loops": 0,
            "recursive_calls": 0,
            "inefficient_patterns": 0,
            "optimization_opportunities": []
        }

        # Only evaluate Python code for now
        if language == "python":
            try:
                tree = ast.parse(code)

                # Analyze nested loops
                nested_result = self._analyze_nested_loops(tree)
                details["nested_loops"] = nested_result["count"]
                issues.extend(nested_result["issues"])
                suggestions.extend(nested_result["suggestions"])

                # Analyze recursive calls
                recursive_result = self._analyze_recursion(tree)
                details["recursive_calls"] = recursive_result["count"]
                issues.extend(recursive_result["issues"])
                suggestions.extend(recursive_result["suggestions"])

                # Detect inefficient patterns
                pattern_result = self._detect_inefficient_patterns(tree, code)
                details["inefficient_patterns"] = pattern_result["count"]
                issues.extend(pattern_result["issues"])
                suggestions.extend(pattern_result["suggestions"])

                # Estimate complexity
                complexity = self._estimate_complexity(details)
                details["time_complexity"] = complexity["time"]
                details["space_complexity"] = complexity["space"]

            except SyntaxError as e:
                logger.warning("Failed to parse code for performance analysis", error=str(e))
                issues.append({
                    "type": "parse_error",
                    "severity": "low",
                    "message": "Could not parse code for performance analysis"
                })

        # Calculate score
        score = self._calculate_score(details)

        return EvaluationResult(
            score=score,
            details=details,
            suggestions=suggestions,
            issues=issues,
            metadata={
                "language": language,
                "evaluator": self.name
            }
        )

    def _analyze_nested_loops(self, tree: ast.AST) -> Dict[str, Any]:
        """Detect nested loops (performance concern)"""
        issues = []
        suggestions = []
        nested_count = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check if there's another loop inside
                for child in ast.walk(node):
                    if child != node and isinstance(child, (ast.For, ast.While)):
                        nested_count += 1
                        issues.append({
                            "type": "nested_loop",
                            "severity": "medium",
                            "line": node.lineno,
                            "message": f"Nested loop detected (potential O(n²) or worse)"
                        })
                        suggestions.append(
                            f"Consider optimizing nested loop at line {node.lineno} "
                            "using hash maps, set operations, or vectorization"
                        )
                        break  # Count each outer loop only once

        return {
            "count": nested_count,
            "issues": issues,
            "suggestions": suggestions
        }

    def _analyze_recursion(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze recursive function calls"""
        issues = []
        suggestions = []
        recursive_count = 0

        # Build list of function names
        function_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_names.add(node.name)

        # Check for recursive calls
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == node.name:
                            recursive_count += 1
                            issues.append({
                                "type": "recursion",
                                "severity": "low",
                                "line": node.lineno,
                                "message": f"Recursive function '{node.name}' (ensure base case exists)"
                            })
                            suggestions.append(
                                f"Consider iterative alternative for '{node.name}' if recursion depth is large"
                            )
                            break  # Count each function only once

        return {
            "count": recursive_count,
            "issues": issues,
            "suggestions": suggestions
        }

    def _detect_inefficient_patterns(self, tree: ast.AST, code: str) -> Dict[str, Any]:
        """Detect inefficient coding patterns"""
        issues = []
        suggestions = []
        pattern_count = 0

        # Pattern 1: list.append() in a loop (use list comprehension)
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if (isinstance(child.func, ast.Attribute) and
                            child.func.attr == "append"):
                            pattern_count += 1
                            issues.append({
                                "type": "inefficient_pattern",
                                "severity": "low",
                                "line": node.lineno,
                                "message": "Using append in loop (consider list comprehension)"
                            })
                            suggestions.append(
                                f"Replace loop with list comprehension at line {node.lineno} for better performance"
                            )
                            break

        # Pattern 2: Multiple string concatenations (use join)
        if "+=" in code and "str" in code.lower():
            lines = code.split("\n")
            for i, line in enumerate(lines, 1):
                if "+=" in line and ("str" in line or "'" in line or '"' in line):
                    pattern_count += 1
                    issues.append({
                        "type": "inefficient_pattern",
                        "severity": "low",
                        "line": i,
                        "message": "String concatenation in loop (use str.join())"
                    })
                    suggestions.append(
                        f"Replace string concatenation with str.join() at line {i}"
                    )

        # Pattern 3: Checking membership in list (use set)
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # Check for "x in list" pattern
                if any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.List):
                            pattern_count += 1
                            issues.append({
                                "type": "inefficient_pattern",
                                "severity": "low",
                                "line": node.lineno,
                                "message": "Membership test on list (use set for O(1) lookup)"
                            })
                            suggestions.append(
                                f"Convert list to set for membership tests at line {node.lineno}"
                            )

        return {
            "count": pattern_count,
            "issues": issues,
            "suggestions": suggestions
        }

    def _estimate_complexity(self, details: Dict[str, Any]) -> Dict[str, str]:
        """Estimate time and space complexity"""
        # Simple heuristics for complexity estimation
        nested_loops = details["nested_loops"]
        recursive_calls = details["recursive_calls"]

        if nested_loops >= 3:
            time_complexity = "O(n³)"
        elif nested_loops >= 2:
            time_complexity = "O(n²)"
        elif nested_loops >= 1:
            time_complexity = "O(n log n)"
        elif recursive_calls > 0:
            time_complexity = "O(2^n)"  # Worst case for recursion
        else:
            time_complexity = "O(n)"

        # Space complexity estimation
        if recursive_calls > 0:
            space_complexity = "O(n)"  # Stack space
        else:
            space_complexity = "O(1)"  # Constant space

        return {
            "time": time_complexity,
            "space": space_complexity
        }

    def _calculate_score(self, details: Dict[str, Any]) -> Decimal:
        """
        Calculate performance score

        Formula:
        score = 10.0 - (nested_loops * 2) - (inefficient_patterns * 1.5) - (recursive_calls * 0.5)
        """
        base_score = 10.0

        score = base_score
        score -= details["nested_loops"] * 2
        score -= details["inefficient_patterns"] * 1.5
        score -= details["recursive_calls"] * 0.5

        # Bonus for good complexity
        if details["time_complexity"] == "O(n)" or details["time_complexity"] == "O(1)":
            score += 0.5

        return self._clamp_score(score)
```

### Step 3: Add to Evaluators Module

Update `backend/src/evaluators/__init__.py`:

```python
# backend/src/evaluators/__init__.py

from .base import BaseEvaluator, EvaluationResult
from .code_quality import CodeQualityEvaluator
from .completeness import CompletenessEvaluator
from .security import SecurityEvaluator
from .performance import PerformanceEvaluator  # Add new evaluator
from .aggregator import EvaluationAggregator, QualityGrade

__all__ = [
    "BaseEvaluator",
    "EvaluationResult",
    "CodeQualityEvaluator",
    "CompletenessEvaluator",
    "SecurityEvaluator",
    "PerformanceEvaluator",  # Add new evaluator
    "EvaluationAggregator",
    "QualityGrade",
]
```

## Integrating with Aggregator

### Step 4: Register in Aggregator

Update `backend/src/evaluators/aggregator.py`:

```python
# backend/src/evaluators/aggregator.py

from .base import BaseEvaluator, EvaluationResult
from .code_quality import CodeQualityEvaluator
from .completeness import CompletenessEvaluator
from .security import SecurityEvaluator
from .performance import PerformanceEvaluator  # Import new evaluator


class EvaluationAggregator:
    """Aggregates results from multiple evaluators"""

    DEFAULT_WEIGHTS = {
        "code_quality": 0.20,      # Reduced from 0.25
        "completeness": 0.25,      # Reduced from 0.30
        "security": 0.25,          # Same
        "performance": 0.15,       # NEW: 15%
        "reserved": 0.15           # Reduced from 0.20
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """Initialize aggregator with custom weights"""
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()

        # Initialize evaluators
        self.evaluators = {
            "code_quality": CodeQualityEvaluator(weight=self.weights["code_quality"]),
            "completeness": CompletenessEvaluator(weight=self.weights["completeness"]),
            "security": SecurityEvaluator(weight=self.weights["security"]),
            "performance": PerformanceEvaluator(weight=self.weights["performance"]),  # Add new evaluator
        }

    # ... rest of the class remains the same
```

### Weight Distribution Guidelines

**Total must equal 1.0 (100%)**

Recommended weight ranges:
- Critical evaluators (security, completeness): 20-30%
- Important evaluators (code quality, performance): 15-25%
- Secondary evaluators (testing, docs): 10-15%
- Reserved for future: 10-20%

Example configurations:

**Configuration 1: Security-focused**
```python
weights = {
    "code_quality": 0.20,
    "completeness": 0.20,
    "security": 0.35,      # Higher weight
    "performance": 0.10,
    "reserved": 0.15
}
```

**Configuration 2: Balanced**
```python
weights = {
    "code_quality": 0.20,
    "completeness": 0.25,
    "security": 0.25,
    "performance": 0.15,
    "testing": 0.10,       # New evaluator
    "reserved": 0.05
}
```

## Configuring Weights

### Dynamic Weight Configuration

You can adjust weights at runtime:

```python
# In API endpoint or service
aggregator = EvaluationAggregator()

# Get current weights
current_weights = aggregator.get_weights()
print(current_weights)
# {'code_quality': 0.25, 'completeness': 0.30, ...}

# Update weights
aggregator.update_weights({
    "performance": 0.20,  # Increase performance weight
    "reserved": 0.05      # Decrease reserved
})

# Run evaluation with new weights
result = await aggregator.evaluate_all(code, context)
```

### Add Custom Evaluator at Runtime

```python
# Create custom evaluator
custom_evaluator = MyCustomEvaluator(weight=0.10)

# Add to aggregator
aggregator.add_evaluator(
    name="custom",
    evaluator=custom_evaluator,
    weight=0.10
)

# Weights will be automatically normalized
```

## Testing Your Evaluator

### Step 5: Write Unit Tests

Create `backend/tests/unit/test_performance_evaluator.py`:

```python
# backend/tests/unit/test_performance_evaluator.py

import pytest
from decimal import Decimal
from src.evaluators.performance import PerformanceEvaluator


@pytest.fixture
def evaluator():
    """Create evaluator instance"""
    return PerformanceEvaluator(weight=1.0)


@pytest.mark.asyncio
async def test_evaluate_good_performance(evaluator):
    """Test code with good performance characteristics"""
    code = """
def search(arr, target):
    # O(n) linear search
    for i, item in enumerate(arr):
        if item == target:
            return i
    return -1
"""
    context = {"language": "python"}

    result = await evaluator.evaluate(code, context)

    assert result.score >= Decimal("7.0")
    assert result.details["time_complexity"] in ["O(n)", "O(log n)"]
    assert result.details["nested_loops"] == 0


@pytest.mark.asyncio
async def test_evaluate_nested_loops(evaluator):
    """Test code with nested loops"""
    code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
"""
    context = {"language": "python"}

    result = await evaluator.evaluate(code, context)

    assert result.details["nested_loops"] >= 1
    assert result.details["time_complexity"] in ["O(n²)", "O(n³)"]
    assert any(issue["type"] == "nested_loop" for issue in result.issues)


@pytest.mark.asyncio
async def test_evaluate_inefficient_patterns(evaluator):
    """Test detection of inefficient patterns"""
    code = """
def process_items(items):
    result = ""
    for item in items:
        result += str(item)  # Inefficient string concatenation
    return result
"""
    context = {"language": "python"}

    result = await evaluator.evaluate(code, context)

    assert result.details["inefficient_patterns"] >= 1
    assert any("join" in suggestion.lower() for suggestion in result.suggestions)


@pytest.mark.asyncio
async def test_evaluate_recursion(evaluator):
    """Test recursive function detection"""
    code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
    context = {"language": "python"}

    result = await evaluator.evaluate(code, context)

    assert result.details["recursive_calls"] >= 1
    assert result.details["time_complexity"] in ["O(2^n)", "O(n)"]


@pytest.mark.asyncio
async def test_evaluate_non_python(evaluator):
    """Test non-Python code handling"""
    code = "const x = 10;"
    context = {"language": "javascript"}

    result = await evaluator.evaluate(code, context)

    # Should return a default score
    assert result.score >= Decimal("0.0")
    assert result.score <= Decimal("10.0")


def test_evaluator_properties(evaluator):
    """Test evaluator properties"""
    assert evaluator.name == "performance"
    assert len(evaluator.description) > 0
    assert evaluator.weight == 1.0
```

### Step 6: Run Tests

```bash
cd backend

# Run specific test file
pytest tests/unit/test_performance_evaluator.py -v

# Run with coverage
pytest tests/unit/test_performance_evaluator.py --cov=src/evaluators/performance --cov-report=html

# Run all evaluator tests
pytest tests/unit/test_*evaluator*.py
```

### Step 7: Integration Testing

Create `backend/tests/integration/test_evaluation_api.py`:

```python
@pytest.mark.asyncio
async def test_evaluate_with_performance_evaluator(client, sample_code):
    """Test evaluation API with performance evaluator"""
    response = await client.post(
        "/api/v1/evaluate",
        json={
            "code": sample_code,
            "context": {
                "language": "python",
                "description": "Sort function"
            },
            "evaluators": ["code_quality", "performance", "security"]
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "overall_score" in data
    assert "component_scores" in data
    assert "performance" in data["component_scores"]
    assert 0 <= data["component_scores"]["performance"] <= 10
```

## Best Practices

### 1. Clear Scoring Formula

Document your scoring formula clearly:

```python
"""
Scoring formula:
base_score = 10.0
score = base_score
        - (critical_issues * 3.0)
        - (high_issues * 1.5)
        - (medium_issues * 0.5)
        + (good_practices * 0.5)

Score range: 0.0 - 10.0
"""
```

### 2. Meaningful Suggestions

Provide actionable suggestions:

```python
# Bad
suggestions.append("Improve performance")

# Good
suggestions.append(
    f"Replace nested loop at line {lineno} with hash map lookup "
    "to reduce complexity from O(n²) to O(n)"
)
```

### 3. Structured Issues

Use consistent issue structure:

```python
issue = {
    "type": "performance",                    # Category
    "severity": "medium",                     # critical, high, medium, low
    "line": 42,                               # Line number (if applicable)
    "message": "O(n²) complexity detected",   # Description
    "suggestion": "Use hash map for O(1) lookup"  # Optional fix
}
```

### 4. Handle Parsing Errors

Gracefully handle code that can't be parsed:

```python
try:
    tree = ast.parse(code)
    # ... analysis
except SyntaxError as e:
    logger.warning("Parse error", error=str(e))
    # Return partial result or default score
    return EvaluationResult(
        score=Decimal("5.0"),  # Neutral score
        details={"parse_error": str(e)},
        suggestions=["Fix syntax errors before evaluation"],
        issues=[{
            "type": "syntax_error",
            "severity": "critical",
            "message": f"Parse error: {str(e)}"
        }]
    )
```

### 5. Language Support

Support multiple languages or clearly indicate limitations:

```python
async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
    language = context.get("language", "python").lower()

    if language not in ["python", "javascript"]:
        logger.warning("Unsupported language", language=language)
        return EvaluationResult(
            score=Decimal("5.0"),  # Neutral score
            details={"supported": False},
            suggestions=[f"Performance evaluation not supported for {language}"],
            issues=[]
        )

    # ... language-specific evaluation
```

### 6. Configurable Thresholds

Use configuration for thresholds:

```python
class PerformanceEvaluator(BaseEvaluator):
    def __init__(self, weight=1.0, config=None):
        super().__init__(weight, config)

        # Configurable thresholds
        self.max_nested_loops = config.get("max_nested_loops", 2)
        self.max_complexity = config.get("max_complexity", "O(n²)")
        self.strict_mode = config.get("strict_mode", False)
```

### 7. Metadata for Debugging

Include useful metadata:

```python
return EvaluationResult(
    score=score,
    details=details,
    suggestions=suggestions,
    issues=issues,
    metadata={
        "language": language,
        "evaluator": self.name,
        "execution_time": execution_time,
        "lines_analyzed": len(code.split("\n")),
        "tools_used": ["ast", "radon"],
        "timestamp": datetime.utcnow().isoformat()
    }
)
```

## Common Evaluation Patterns

### Pattern 1: AST-Based Analysis

Use Python's `ast` module for code analysis:

```python
import ast

def analyze_code_structure(code: str) -> Dict[str, Any]:
    """Analyze code structure using AST"""
    tree = ast.parse(code)

    stats = {
        "functions": 0,
        "classes": 0,
        "loops": 0,
        "conditionals": 0
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            stats["functions"] += 1
        elif isinstance(node, ast.ClassDef):
            stats["classes"] += 1
        elif isinstance(node, (ast.For, ast.While)):
            stats["loops"] += 1
        elif isinstance(node, ast.If):
            stats["conditionals"] += 1

    return stats
```

### Pattern 2: Regex-Based Detection

Use regex for pattern matching:

```python
import re

def detect_patterns(code: str) -> List[Dict[str, Any]]:
    """Detect code patterns using regex"""
    patterns = []

    # Pattern: Hardcoded passwords
    password_pattern = re.compile(r'password\s*=\s*["\'](.+?)["\']', re.IGNORECASE)
    for match in password_pattern.finditer(code):
        patterns.append({
            "type": "hardcoded_password",
            "severity": "critical",
            "line": code[:match.start()].count("\n") + 1,
            "value": match.group(1)
        })

    return patterns
```

### Pattern 3: External Tool Integration

Integrate external tools:

```python
import subprocess
import json

async def run_external_tool(code: str, tool: str) -> Dict[str, Any]:
    """Run external code analysis tool"""
    # Write code to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name

    try:
        # Run tool
        result = subprocess.run(
            [tool, temp_file, '--json'],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Parse output
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            logger.error("Tool failed", tool=tool, error=result.stderr)
            return {}

    finally:
        os.unlink(temp_file)
```

### Pattern 4: Keyword-Based Scoring

Score based on keyword presence:

```python
def score_documentation(code: str, docstrings: List[str]) -> float:
    """Score documentation quality based on keywords"""
    keywords = {
        "args": 1.0,
        "returns": 1.0,
        "raises": 0.5,
        "example": 1.5,
        "note": 0.5,
        "warning": 0.5
    }

    score = 0.0
    for docstring in docstrings:
        docstring_lower = docstring.lower()
        for keyword, value in keywords.items():
            if keyword in docstring_lower:
                score += value

    # Normalize to 0-10 scale
    max_score = len(docstrings) * sum(keywords.values())
    normalized = (score / max_score * 10) if max_score > 0 else 5.0

    return min(normalized, 10.0)
```

## Troubleshooting

### Issue: Evaluator Not Running

**Problem:** New evaluator doesn't execute

**Solutions:**
1. Check evaluator is imported in `__init__.py`
2. Verify evaluator is registered in `EvaluationAggregator`
3. Ensure evaluator weight is > 0
4. Check for exceptions in evaluator code

### Issue: Inconsistent Scores

**Problem:** Scores vary wildly between runs

**Solutions:**
1. Remove randomness from scoring logic
2. Use deterministic algorithms
3. Document scoring formula clearly
4. Add unit tests for edge cases

### Issue: Performance Problems

**Problem:** Evaluation takes too long

**Solutions:**
1. Optimize AST traversal (use `ast.walk` once)
2. Add timeouts to external tool calls
3. Cache analysis results
4. Limit code size for analysis
5. Profile code to find bottlenecks

```python
import cProfile

def profile_evaluator():
    """Profile evaluator performance"""
    profiler = cProfile.Profile()
    profiler.enable()

    # Run evaluation
    result = await evaluator.evaluate(code, context)

    profiler.disable()
    profiler.print_stats(sort='cumulative')
```

## Next Steps

After creating your evaluator:

1. **Document thoroughly**: Add detailed docstrings and comments
2. **Test extensively**: Unit tests, integration tests, edge cases
3. **Monitor in production**: Track scores, execution time, error rates
4. **Iterate**: Refine scoring based on real-world usage
5. **Share**: Contribute back to the project

## Additional Resources

- [BaseEvaluator Interface](../backend/src/evaluators/base.py)
- [CodeQualityEvaluator Example](../backend/src/evaluators/code_quality.py)
- [CompletenessEvaluator Example](../backend/src/evaluators/completeness.py)
- [SecurityEvaluator Example](../backend/src/evaluators/security.py)
- [EvaluationAggregator](../backend/src/evaluators/aggregator.py)
- [Testing Guide](./contributing.md#testing-guidelines)
- [Architecture Deep Dive](./architecture-deep-dive.md#evaluation-framework-architecture)
