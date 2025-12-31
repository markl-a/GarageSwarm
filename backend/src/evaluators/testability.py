"""
Testability Evaluator

Evaluates code testability and test coverage quality:
- Test coverage percentage
- Test quality metrics
- Testable code structure
- Mock/stub usage
- Test organization
"""

import ast
import re
from typing import Any, Dict, List, Set
from decimal import Decimal
import structlog

from .base import BaseEvaluator, EvaluationResult

logger = structlog.get_logger()


class TestabilityEvaluator(BaseEvaluator):
    """
    Evaluates code testability and test quality:
    - Test coverage analysis
    - Test quality metrics (assertions, mocking, organization)
    - Code structure for testability
    - Dependency injection usage
    - Test completeness
    """

    @property
    def name(self) -> str:
        return "testability"

    @property
    def description(self) -> str:
        return "Evaluates code testability and test coverage quality"

    async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate testability

        Scoring formula:
        base_score = test_coverage_score + test_quality_score + code_testability_score
        Each component contributes 0-3.33 points for a total of 0-10

        Args:
            code: Source code to evaluate
            context: Context including:
                - language: Programming language
                - test_coverage: Coverage percentage (if available)
                - is_test_file: Whether this is a test file
                - coverage_data: Detailed coverage data

        Returns:
            EvaluationResult with testability score and details
        """
        language = context.get("language", "python").lower()
        is_test_file = context.get("is_test_file", False)
        test_coverage = context.get("test_coverage", None)

        # Initialize results
        issues = []
        suggestions = []
        details = {
            "test_coverage": test_coverage if test_coverage is not None else 0.0,
            "test_count": 0,
            "assertion_count": 0,
            "mock_usage": False,
            "test_quality_score": 0.0,
            "code_testability_score": 0.0,
            "coverage_score": 0.0,
            "has_fixtures": False,
            "has_parametrized_tests": False,
            "testable_structure": True
        }

        # Only evaluate Python code for now
        if language == "python":
            if is_test_file:
                # Evaluate test file quality
                test_result = self._evaluate_test_file(code)
                details.update(test_result["details"])
                issues.extend(test_result["issues"])
                suggestions.extend(test_result["suggestions"])
            else:
                # Evaluate code testability
                testability_result = self._evaluate_code_testability(code)
                details.update(testability_result["details"])
                issues.extend(testability_result["issues"])
                suggestions.extend(testability_result["suggestions"])

            # Calculate coverage score if coverage data available
            if test_coverage is not None:
                coverage_result = self._evaluate_coverage(test_coverage)
                details["coverage_score"] = coverage_result["score"]
                issues.extend(coverage_result["issues"])
                suggestions.extend(coverage_result["suggestions"])
        else:
            # For non-Python code, do basic checks
            basic_result = self._basic_testability_check(code, language, is_test_file)
            details.update(basic_result["details"])
            issues.extend(basic_result["issues"])
            suggestions.extend(basic_result["suggestions"])

        # Calculate final score
        score = self._calculate_score(details, is_test_file)

        return EvaluationResult(
            score=score,
            details=details,
            suggestions=suggestions,
            issues=issues,
            metadata={
                "language": language,
                "is_test_file": is_test_file,
                "evaluator": self.name
            }
        )

    def _evaluate_test_file(self, code: str) -> Dict[str, Any]:
        """
        Evaluate test file quality

        Checks:
        - Number of test cases
        - Assertion usage
        - Mock/stub usage
        - Test organization (fixtures, parametrization)
        - Test coverage of edge cases
        """
        issues = []
        suggestions = []
        details = {
            "test_count": 0,
            "assertion_count": 0,
            "mock_usage": False,
            "has_fixtures": False,
            "has_parametrized_tests": False,
            "test_quality_score": 0.0,
            "setup_teardown": False,
            "edge_case_tests": 0
        }

        try:
            tree = ast.parse(code)

            # Find test functions
            test_functions = []
            fixtures = []
            parametrized_tests = []

            for node in ast.walk(tree):
                # Find test functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_"):
                        test_functions.append(node)
                        details["test_count"] += 1

                        # Count assertions in test
                        assertion_count = self._count_assertions(node)
                        details["assertion_count"] += assertion_count

                        if assertion_count == 0:
                            issues.append({
                                "type": "test_quality",
                                "severity": "high",
                                "line": node.lineno,
                                "message": f"Test '{node.name}' has no assertions"
                            })

                    # Check for fixtures
                    if node.decorator_list:
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Name):
                                if decorator.id == "fixture":
                                    fixtures.append(node.name)
                                    details["has_fixtures"] = True
                            elif isinstance(decorator, ast.Attribute):
                                # Handle @pytest.fixture
                                if decorator.attr == "fixture":
                                    fixtures.append(node.name)
                                    details["has_fixtures"] = True
                                elif decorator.attr == "parametrize":
                                    parametrized_tests.append(node.name)
                                    details["has_parametrized_tests"] = True
                            elif isinstance(decorator, ast.Call):
                                if isinstance(decorator.func, ast.Attribute):
                                    if decorator.func.attr == "fixture":
                                        fixtures.append(node.name)
                                        details["has_fixtures"] = True
                                    elif decorator.func.attr == "parametrize":
                                        parametrized_tests.append(node.name)
                                        details["has_parametrized_tests"] = True
                                elif isinstance(decorator.func, ast.Name):
                                    if decorator.func.id == "fixture":
                                        fixtures.append(node.name)
                                        details["has_fixtures"] = True

                    # Check for setup/teardown
                    if node.name in ["setUp", "tearDown", "setup", "teardown", "setup_method", "teardown_method"]:
                        details["setup_teardown"] = True

                # Check for mock usage
                if isinstance(node, ast.Name):
                    if "mock" in node.id.lower() or "patch" in node.id.lower():
                        details["mock_usage"] = True

                # Check for edge case tests
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if any(keyword in node.name.lower() for keyword in ["edge", "boundary", "error", "exception", "invalid"]):
                        details["edge_case_tests"] += 1

            # Provide feedback
            if details["test_count"] == 0:
                issues.append({
                    "type": "test_quality",
                    "severity": "critical",
                    "message": "No test functions found in test file"
                })

            if details["test_count"] < 3:
                suggestions.append("Add more test cases to improve coverage")

            if not details["mock_usage"] and details["test_count"] > 0:
                suggestions.append("Consider using mocks/stubs for external dependencies")

            if not details["has_fixtures"] and details["test_count"] > 3:
                suggestions.append("Use fixtures to reduce test code duplication")

            if not details["has_parametrized_tests"] and details["test_count"] > 5:
                suggestions.append("Consider parametrized tests for testing multiple scenarios")

            if details["edge_case_tests"] == 0 and details["test_count"] > 0:
                issues.append({
                    "type": "test_quality",
                    "severity": "medium",
                    "message": "No edge case tests detected"
                })
                suggestions.append("Add tests for edge cases and error conditions")

            # Calculate test quality score (0-3.33)
            quality_score = 0.0

            # Base score from having tests
            if details["test_count"] > 0:
                quality_score += 1.0

            # Bonus for good practices
            if details["assertion_count"] > 0:
                avg_assertions = details["assertion_count"] / max(details["test_count"], 1)
                if avg_assertions >= 2:
                    quality_score += 0.5

            if details["mock_usage"]:
                quality_score += 0.3

            if details["has_fixtures"]:
                quality_score += 0.3

            if details["has_parametrized_tests"]:
                quality_score += 0.3

            if details["edge_case_tests"] > 0:
                quality_score += 0.5

            # Cap at 3.33
            details["test_quality_score"] = min(quality_score, 3.33)

        except Exception as e:
            logger.warning(f"Error evaluating test file: {e}")
            issues.append({
                "type": "test_quality",
                "severity": "critical",
                "message": f"Failed to parse test file: {str(e)}"
            })

        return {
            "details": details,
            "issues": issues,
            "suggestions": suggestions
        }

    def _count_assertions(self, node: ast.AST) -> int:
        """Count assertion statements in a test function"""
        assertion_count = 0

        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                assertion_count += 1
            elif isinstance(child, ast.Call):
                # Check for assertion methods (assert_equal, etc.)
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr.startswith("assert"):
                        assertion_count += 1

        return assertion_count

    def _evaluate_code_testability(self, code: str) -> Dict[str, Any]:
        """
        Evaluate how testable the code is

        Checks:
        - Use of dependency injection
        - Function complexity (simpler = more testable)
        - Tight coupling indicators
        - Global state usage
        - Hard-coded dependencies
        """
        issues = []
        suggestions = []
        details = {
            "dependency_injection": False,
            "global_state_usage": 0,
            "hard_coded_deps": 0,
            "code_testability_score": 0.0,
            "tight_coupling": 0,
            "testable_structure": True
        }

        try:
            tree = ast.parse(code)

            has_di_pattern = False
            global_vars = set()
            hard_coded_deps = []

            for node in ast.walk(tree):
                # Check for dependency injection patterns
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check if function accepts dependencies as parameters
                    if len(node.args.args) > 0:
                        # Look for common DI parameter names
                        param_names = [arg.arg for arg in node.args.args]
                        di_keywords = ["service", "repository", "client", "session", "db", "cache"]
                        if any(keyword in " ".join(param_names).lower() for keyword in di_keywords):
                            has_di_pattern = True
                            details["dependency_injection"] = True

                # Check for global state
                if isinstance(node, ast.Global):
                    details["global_state_usage"] += len(node.names)
                    global_vars.update(node.names)
                    issues.append({
                        "type": "testability",
                        "severity": "medium",
                        "line": node.lineno,
                        "message": f"Global state usage detected: {', '.join(node.names)}"
                    })

                # Check for hard-coded dependencies (direct instantiation)
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        # Direct class instantiation could indicate tight coupling
                        if node.func.id[0].isupper():  # Class names start with uppercase
                            hard_coded_deps.append(node.func.id)

            details["hard_coded_deps"] = len(hard_coded_deps)

            # Provide feedback
            if details["global_state_usage"] > 0:
                suggestions.append("Reduce global state usage for better testability")
                details["testable_structure"] = False

            if not has_di_pattern:
                suggestions.append("Consider using dependency injection for better testability")

            if len(hard_coded_deps) > 5:
                issues.append({
                    "type": "testability",
                    "severity": "medium",
                    "message": "Multiple hard-coded dependencies detected"
                })
                suggestions.append("Use dependency injection instead of direct instantiation")
                details["tight_coupling"] = len(hard_coded_deps)

            # Calculate code testability score (0-3.33)
            testability_score = 3.33  # Start with perfect score

            # Deduct for bad practices
            testability_score -= details["global_state_usage"] * 0.5
            testability_score -= min(details["hard_coded_deps"] * 0.1, 1.0)

            # Bonus for good practices
            if has_di_pattern:
                testability_score += 0.5

            # Clamp to range
            details["code_testability_score"] = max(0.0, min(testability_score, 3.33))

        except Exception as e:
            logger.warning(f"Error evaluating code testability: {e}")

        return {
            "details": details,
            "issues": issues,
            "suggestions": suggestions
        }

    def _evaluate_coverage(self, coverage_percentage: float) -> Dict[str, Any]:
        """
        Evaluate test coverage

        Coverage scoring (0-3.33):
        - 90-100%: 3.33
        - 80-89%: 2.5
        - 70-79%: 2.0
        - 60-69%: 1.5
        - 50-59%: 1.0
        - <50%: 0.5
        """
        issues = []
        suggestions = []

        if coverage_percentage >= 90:
            score = 3.33
        elif coverage_percentage >= 80:
            score = 2.5
            suggestions.append("Increase test coverage to 90%+ for excellent coverage")
        elif coverage_percentage >= 70:
            score = 2.0
            issues.append({
                "type": "coverage",
                "severity": "low",
                "message": f"Test coverage is {coverage_percentage}% - aim for 80%+"
            })
            suggestions.append("Add more tests to improve coverage")
        elif coverage_percentage >= 60:
            score = 1.5
            issues.append({
                "type": "coverage",
                "severity": "medium",
                "message": f"Test coverage is {coverage_percentage}% - should be at least 70%"
            })
            suggestions.append("Significantly increase test coverage")
        elif coverage_percentage >= 50:
            score = 1.0
            issues.append({
                "type": "coverage",
                "severity": "high",
                "message": f"Test coverage is {coverage_percentage}% - critically low"
            })
            suggestions.append("Add comprehensive test suite")
        else:
            score = 0.5
            issues.append({
                "type": "coverage",
                "severity": "critical",
                "message": f"Test coverage is {coverage_percentage}% - insufficient"
            })
            suggestions.append("Implement comprehensive testing strategy")

        return {
            "score": score,
            "issues": issues,
            "suggestions": suggestions
        }

    def _basic_testability_check(self, code: str, language: str, is_test_file: bool) -> Dict[str, Any]:
        """Basic testability checks for non-Python code"""
        issues = []
        suggestions = []

        details = {
            "test_coverage": 0.0,
            "test_count": 0,
            "test_quality_score": 0.0,
            "code_testability_score": 0.0,
            "coverage_score": 0.0
        }

        if is_test_file:
            # Very basic check for test patterns
            if re.search(r'\btest\w*\s*\(', code, re.IGNORECASE):
                details["test_count"] = len(re.findall(r'\btest\w*\s*\(', code, re.IGNORECASE))
                details["test_quality_score"] = 1.0
            else:
                issues.append({
                    "type": "test_quality",
                    "severity": "critical",
                    "message": "No test functions detected in test file"
                })
        else:
            suggestions.append("Add unit tests for this code")

        return {
            "details": details,
            "issues": issues,
            "suggestions": suggestions
        }

    def _calculate_score(self, details: Dict[str, Any], is_test_file: bool) -> Decimal:
        """
        Calculate final testability score

        Score components (each 0-3.33, total 0-10):
        1. Coverage score (if available)
        2. Test quality score (for test files) OR code testability score (for source files)
        3. Overall testability indicators

        For test files: test_quality_score + edge_coverage + organization
        For source files: code_testability_score + coverage_score + structure
        """
        base_score = 0.0

        if is_test_file:
            # For test files, focus on test quality
            base_score += details.get("test_quality_score", 0.0)

            # Add points for good test organization
            if details.get("has_fixtures", False):
                base_score += 0.5
            if details.get("has_parametrized_tests", False):
                base_score += 0.5
            if details.get("edge_case_tests", 0) > 0:
                base_score += 1.0

            # Quality bonus
            if details.get("assertion_count", 0) > 0:
                avg_assertions = details["assertion_count"] / max(details.get("test_count", 1), 1)
                if avg_assertions >= 3:
                    base_score += 0.5
        else:
            # For source files, focus on testability and coverage
            base_score += details.get("code_testability_score", 0.0)
            base_score += details.get("coverage_score", 0.0)

            # Bonus for testable structure
            if details.get("dependency_injection", False):
                base_score += 1.0

            if details.get("testable_structure", True):
                base_score += 1.0

        # Ensure we're in valid range
        return self._clamp_score(base_score)
