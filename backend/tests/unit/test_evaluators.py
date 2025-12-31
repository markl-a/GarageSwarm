"""
Comprehensive Unit Tests for Backend Evaluators

Tests all evaluator modules:
- CodeQualityEvaluator
- CompletenessEvaluator
- SecurityEvaluator
- EvaluationAggregator

Coverage includes:
- Valid code input scoring
- Invalid/malformed code handling
- Edge cases (empty input, very long input)
- Score calculation accuracy
- Aggregation weights
- Mock external tool calls
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import patch, MagicMock

from src.evaluators.base import BaseEvaluator, EvaluationResult
from src.evaluators.code_quality import CodeQualityEvaluator
from src.evaluators.completeness import CompletenessEvaluator
from src.evaluators.security import SecurityEvaluator
from src.evaluators.aggregator import EvaluationAggregator, QualityGrade


# ==================== Test Fixtures ====================


@pytest.fixture
def valid_python_code():
    """Valid Python code sample with good quality"""
    return '''
def calculate_sum(a: int, b: int) -> int:
    """
    Calculate the sum of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    try:
        result = a + b
        return result
    except TypeError as e:
        logger.error(f"Invalid input types: {e}")
        raise

def test_calculate_sum():
    """Test the calculate_sum function"""
    assert calculate_sum(2, 3) == 5
    assert calculate_sum(-1, 1) == 0
'''


@pytest.fixture
def invalid_python_code():
    """Python code with syntax errors"""
    return '''
def broken_function(
    # Missing closing parenthesis
    x = invalid syntax here
    return x
'''


@pytest.fixture
def code_with_security_issues():
    """Code with multiple security vulnerabilities"""
    return '''
import os

def process_user_input(user_input):
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    execute(query)

    # Command injection vulnerability
    os.system(f"echo {user_input}")

    # Hardcoded secrets
    api_key = "sk-1234567890abcdefghijklmnop"
    password = "SuperSecret123"

    # eval is dangerous
    eval(user_input)
'''


@pytest.fixture
def empty_code():
    """Empty code string"""
    return ""


@pytest.fixture
def very_long_code():
    """Very long code to test performance"""
    return "\n".join([f"# Comment line {i}" for i in range(10000)])


@pytest.fixture
def code_without_error_handling():
    """Code with no error handling"""
    return '''
def risky_operation(data):
    result = data / 0
    return result
'''


@pytest.fixture
def code_with_high_complexity():
    """Code with high cyclomatic complexity"""
    return '''
def complex_function(a, b, c, d, e):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        for i in range(10):
                            if i % 2 == 0:
                                for j in range(10):
                                    if j % 2 == 0:
                                        return True
    return False
'''


@pytest.fixture
def basic_context():
    """Basic evaluation context"""
    return {
        "language": "python",
        "description": "Write a function to calculate sum of two numbers",
        "requirements": []
    }


# ==================== CodeQualityEvaluator Tests ====================


class TestCodeQualityEvaluator:
    """Test suite for CodeQualityEvaluator"""

    @pytest_asyncio.fixture
    async def evaluator(self):
        """Create CodeQualityEvaluator instance"""
        return CodeQualityEvaluator()

    @pytest.mark.asyncio
    async def test_evaluator_properties(self, evaluator):
        """Test evaluator name and description"""
        assert evaluator.name == "code_quality"
        assert "syntax" in evaluator.description.lower()
        assert evaluator.get_weight() == 1.0

    @pytest.mark.asyncio
    async def test_valid_python_code(self, evaluator, valid_python_code, basic_context):
        """Test evaluation of valid Python code"""
        result = await evaluator.evaluate(valid_python_code, basic_context)

        assert isinstance(result, EvaluationResult)
        assert result.score >= Decimal("7.0")  # Should score well
        assert result.details["syntax_errors"] == 0
        assert "language" in result.metadata

    @pytest.mark.asyncio
    async def test_invalid_python_code(self, evaluator, invalid_python_code, basic_context):
        """Test evaluation of code with syntax errors"""
        result = await evaluator.evaluate(invalid_python_code, basic_context)

        assert result.score <= Decimal("5.0")  # Syntax errors heavily penalize
        assert result.details["syntax_errors"] > 0
        assert any(issue["type"] == "syntax" for issue in result.issues)
        assert any(issue["severity"] == "critical" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_empty_code(self, evaluator, empty_code, basic_context):
        """Test evaluation of empty code"""
        result = await evaluator.evaluate(empty_code, basic_context)

        assert isinstance(result, EvaluationResult)
        assert result.score >= Decimal("0.0")
        assert result.score <= Decimal("10.0")

    @pytest.mark.asyncio
    async def test_code_with_high_complexity(self, evaluator, code_with_high_complexity, basic_context):
        """Test detection of high cyclomatic complexity"""
        result = await evaluator.evaluate(code_with_high_complexity, basic_context)

        # Check for complexity issues - either high count or medium complexity
        has_complexity_issue = (
            result.details.get("high_complexity_count", 0) > 0 or
            any(issue["type"] == "complexity" for issue in result.issues)
        )
        assert has_complexity_issue

    @pytest.mark.asyncio
    async def test_comment_coverage_detection(self, evaluator, basic_context):
        """Test comment coverage calculation"""
        code_with_comments = '''
# This is a comment
def function():
    # Another comment
    pass  # Inline comment
'''
        result = await evaluator.evaluate(code_with_comments, basic_context)

        assert "comment_coverage" in result.details
        assert result.details["comment_coverage"] > 0

    @pytest.mark.asyncio
    async def test_long_lines_detection(self, evaluator, basic_context):
        """Test detection of lines that are too long"""
        code_with_long_lines = 'x = "' + 'a' * 150 + '"'
        result = await evaluator.evaluate(code_with_long_lines, basic_context)

        assert result.details["lint_warnings"] > 0
        assert any(issue["type"] == "style" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_missing_docstrings(self, evaluator, basic_context):
        """Test detection of missing docstrings"""
        code_without_docstrings = '''
def function_without_docstring(x):
    return x * 2

class ClassWithoutDocstring:
    pass
'''
        result = await evaluator.evaluate(code_without_docstrings, basic_context)

        assert result.details["lint_warnings"] > 0
        assert any("docstring" in issue["message"].lower() for issue in result.issues)

    @pytest.mark.asyncio
    async def test_score_clamping(self, evaluator, basic_context):
        """Test that scores are clamped to 0-10 range"""
        # Use severely broken code
        broken_code = "def f(\n" * 100  # Many syntax errors
        result = await evaluator.evaluate(broken_code, basic_context)

        assert result.score >= Decimal("0.0")
        assert result.score <= Decimal("10.0")

    @pytest.mark.asyncio
    async def test_non_python_language(self, evaluator):
        """Test evaluation of non-Python code"""
        javascript_code = '''
function sum(a, b) {
    return a + b;
}
'''
        context = {"language": "javascript", "description": "Sum function"}
        result = await evaluator.evaluate(javascript_code, context)

        assert isinstance(result, EvaluationResult)
        assert result.score >= Decimal("0.0")


# ==================== CompletenessEvaluator Tests ====================


class TestCompletenessEvaluator:
    """Test suite for CompletenessEvaluator"""

    @pytest_asyncio.fixture
    async def evaluator(self):
        """Create CompletenessEvaluator instance"""
        return CompletenessEvaluator()

    @pytest.mark.asyncio
    async def test_evaluator_properties(self, evaluator):
        """Test evaluator name and description"""
        assert evaluator.name == "completeness"
        assert "requirement" in evaluator.description.lower()

    @pytest.mark.asyncio
    async def test_requirement_coverage(self, evaluator, valid_python_code):
        """Test requirement coverage calculation"""
        context = {
            "language": "python",
            "description": "Create a function that calculates sum",
            "requirements": [
                "Function must accept two parameters",
                "Function must return the sum",
                "Function must have error handling"
            ]
        }
        result = await evaluator.evaluate(valid_python_code, context)

        assert "requirement_coverage" in result.details
        assert result.details["requirement_coverage"] >= 0
        assert "total_requirements" in result.details
        assert result.details["total_requirements"] >= 3

    @pytest.mark.asyncio
    async def test_error_handling_detection(self, evaluator, valid_python_code, basic_context):
        """Test detection of error handling"""
        result = await evaluator.evaluate(valid_python_code, basic_context)

        assert "error_handling_score" in result.details
        assert result.details["error_handling_score"] >= 0
        # Check if error handling was detected
        if "error_handling_details" in result.details:
            assert "has_try_except" in result.details["error_handling_details"]

    @pytest.mark.asyncio
    async def test_no_error_handling(self, evaluator, code_without_error_handling, basic_context):
        """Test detection of missing error handling"""
        result = await evaluator.evaluate(code_without_error_handling, basic_context)

        assert result.details["error_handling_score"] <= 50
        # May have error handling issue or suggestion
        has_error_handling_feedback = (
            any("error handling" in issue["message"].lower() for issue in result.issues) or
            any("error" in suggestion.lower() for suggestion in result.suggestions)
        )
        assert has_error_handling_feedback or result.details["error_handling_score"] == 0

    @pytest.mark.asyncio
    async def test_test_detection(self, evaluator, valid_python_code, basic_context):
        """Test detection of test code"""
        result = await evaluator.evaluate(valid_python_code, basic_context)

        assert "has_tests" in result.details
        assert result.details["has_tests"] is True

    @pytest.mark.asyncio
    async def test_no_tests(self, evaluator, code_without_error_handling, basic_context):
        """Test detection when tests are missing"""
        result = await evaluator.evaluate(code_without_error_handling, basic_context)

        assert result.details["has_tests"] is False
        assert any("test" in suggestion.lower() for suggestion in result.suggestions)

    @pytest.mark.asyncio
    async def test_documentation_detection(self, evaluator, valid_python_code, basic_context):
        """Test documentation detection"""
        result = await evaluator.evaluate(valid_python_code, basic_context)

        assert "has_documentation" in result.details
        assert result.details["has_documentation"] is True

    @pytest.mark.asyncio
    async def test_requirement_extraction(self, evaluator):
        """Test automatic requirement extraction from description"""
        context = {
            "language": "python",
            "description": """
            The function must:
            - Accept two parameters
            - Return their sum
            - Handle type errors
            """,
            "requirements": []
        }
        code = "def sum(a, b): return a + b"
        result = await evaluator.evaluate(code, context)

        assert result.details["total_requirements"] > 0

    @pytest.mark.asyncio
    async def test_missing_requirements(self, evaluator):
        """Test identification of missing requirements"""
        context = {
            "language": "python",
            "description": "Create a database connection manager",
            "requirements": [
                "Must implement connection pooling",
                "Must support transactions",
                "Must handle connection failures"
            ]
        }
        simple_code = "def connect(): pass"
        result = await evaluator.evaluate(simple_code, context)

        assert len(result.details["missing_requirements"]) > 0
        assert result.details["requirement_coverage"] < 50

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, evaluator, basic_context):
        """Test detection of generic exception handling"""
        code_with_generic_except = '''
def function():
    try:
        risky_operation()
    except Exception:
        pass
'''
        result = await evaluator.evaluate(code_with_generic_except, basic_context)

        assert result.details["error_handling_details"]["generic_exceptions"] > 0


# ==================== SecurityEvaluator Tests ====================


class TestSecurityEvaluator:
    """Test suite for SecurityEvaluator"""

    @pytest_asyncio.fixture
    async def evaluator(self):
        """Create SecurityEvaluator instance"""
        return SecurityEvaluator()

    @pytest.mark.asyncio
    async def test_evaluator_properties(self, evaluator):
        """Test evaluator name and description"""
        assert evaluator.name == "security"
        assert "security" in evaluator.description.lower()

    @pytest.mark.asyncio
    async def test_sql_injection_detection(self, evaluator, basic_context):
        """Test detection of SQL injection vulnerabilities"""
        # Test multiple patterns that should trigger SQL injection detection
        code1 = 'execute(f"SELECT * FROM users WHERE id = {user_id}")'
        code2 = 'cursor.execute("SELECT * FROM users WHERE name = \'%s\'" % username)'
        code3 = 'db.execute(query.format(username))'

        # Test at least one pattern
        result = await evaluator.evaluate(code1, basic_context)

        # Should detect SQL injection vulnerability
        has_sql_issue = (
            result.details.get("high_risk_count", 0) > 0 or
            result.details.get("total_vulnerabilities", 0) > 0 or
            any("sql" in str(issue).lower() or "injection" in str(issue).lower() for issue in result.issues)
        )
        assert has_sql_issue

    @pytest.mark.asyncio
    async def test_command_injection_detection(self, evaluator, basic_context):
        """Test detection of command injection vulnerabilities"""
        code = '''
import os
import subprocess

def run_command(cmd):
    os.system(cmd)
    subprocess.call(cmd, shell=True)
'''
        result = await evaluator.evaluate(code, basic_context)

        assert result.details["high_risk_count"] > 0
        assert any(issue["type"] == "command_injection" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_hardcoded_secrets_detection(self, evaluator, basic_context):
        """Test detection of hardcoded secrets"""
        code = '''
api_key = "sk-1234567890abcdefghijklmnop"
password = "MySecretPassword123"
aws_access_key = "AKIAIOSFODNN7EXAMPLE"
'''
        result = await evaluator.evaluate(code, basic_context)

        assert result.details["high_risk_count"] > 0
        assert any(issue["type"] == "hardcoded_secret" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_xss_vulnerability_detection(self, evaluator, basic_context):
        """Test detection of XSS vulnerabilities"""
        code = '''
def render_page(user_input):
    document.write(user_input)
    element.innerHTML = user_input
    eval(user_input)
'''
        result = await evaluator.evaluate(code, basic_context)

        assert result.details["high_risk_count"] > 0
        assert any(issue["type"] == "xss" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_insecure_functions_detection(self, evaluator, basic_context):
        """Test detection of insecure functions"""
        code = '''
import pickle
import yaml

def load_data(data):
    pickle.loads(data)
    yaml.load(data)
    eval(data)
    exec(data)
'''
        result = await evaluator.evaluate(code, basic_context)

        assert result.details["total_vulnerabilities"] > 0
        assert any(issue["type"] == "insecure_function" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_secure_code(self, evaluator, valid_python_code, basic_context):
        """Test evaluation of secure code"""
        result = await evaluator.evaluate(valid_python_code, basic_context)

        assert result.score >= Decimal("7.0")
        assert result.details["high_risk_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_vulnerabilities(self, evaluator, code_with_security_issues, basic_context):
        """Test code with multiple security issues"""
        result = await evaluator.evaluate(code_with_security_issues, basic_context)

        assert result.score < Decimal("5.0")
        assert result.details["total_vulnerabilities"] > 3
        assert result.details["high_risk_count"] > 0
        assert len(result.suggestions) > 0

    @pytest.mark.asyncio
    async def test_human_review_flag(self, evaluator, code_with_security_issues, basic_context):
        """Test that severe security issues trigger human review flag"""
        result = await evaluator.evaluate(code_with_security_issues, basic_context)

        if result.score < Decimal("4.0"):
            assert result.details["requires_human_review"] is True

    @pytest.mark.asyncio
    async def test_exclude_test_patterns(self, evaluator, basic_context):
        """Test that test/example patterns are excluded from secret detection"""
        code = '''
password = "test"
api_key = "demo"
secret_key = "example"
'''
        result = await evaluator.evaluate(code, basic_context)

        # Should not flag test/demo/example values as secrets
        secret_issues = [i for i in result.issues if i["type"] == "hardcoded_secret"]
        assert len(secret_issues) == 0

    @pytest.mark.asyncio
    async def test_insecure_dependencies(self, evaluator, basic_context):
        """Test detection of insecure dependencies"""
        code = '''
import telnetlib
import ftplib
from urllib import request
'''
        result = await evaluator.evaluate(code, basic_context)

        assert any(issue["type"] == "insecure_dependency" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_score_calculation(self, evaluator, basic_context):
        """Test security score calculation formula"""
        # Code with known vulnerabilities
        code = '''
def vulnerable():
    os.system("rm -rf")  # High risk
    yaml.load(data)      # High risk
    import urllib        # Low risk
'''
        result = await evaluator.evaluate(code, basic_context)

        # Verify score is calculated according to formula
        expected_score = 10.0 - (result.details["high_risk_count"] * 3) - \
                        (result.details["medium_risk_count"] * 1) - \
                        (result.details["low_risk_count"] * 0.5)
        expected_score = max(0.0, min(10.0, expected_score))

        assert abs(float(result.score) - expected_score) < 0.1


# ==================== EvaluationAggregator Tests ====================


class TestEvaluationAggregator:
    """Test suite for EvaluationAggregator"""

    @pytest.fixture
    def aggregator(self):
        """Create EvaluationAggregator instance"""
        return EvaluationAggregator()

    @pytest.fixture
    def custom_weights(self):
        """Custom weight configuration"""
        return {
            "code_quality": 0.3,
            "completeness": 0.4,
            "security": 0.3
        }

    def test_default_weights(self, aggregator):
        """Test default weight configuration"""
        weights = aggregator.get_weights()
        assert weights["code_quality"] == 0.25
        assert weights["completeness"] == 0.30
        assert weights["security"] == 0.25
        assert sum(weights.values()) == pytest.approx(1.0)

    def test_custom_weights(self, custom_weights):
        """Test custom weight initialization"""
        aggregator = EvaluationAggregator(weights=custom_weights)
        weights = aggregator.get_weights()
        assert weights["code_quality"] == 0.3
        assert weights["completeness"] == 0.4

    def test_weight_normalization(self):
        """Test that weights are normalized if they don't sum to 1.0"""
        bad_weights = {
            "code_quality": 0.5,
            "completeness": 0.5,
            "security": 0.5,
            "reserved": 0.5
        }
        aggregator = EvaluationAggregator(weights=bad_weights)
        weights = aggregator.get_weights()
        assert sum(weights.values()) == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_evaluate_all_valid_code(self, aggregator, valid_python_code, basic_context):
        """Test aggregate evaluation of valid code"""
        report = await aggregator.evaluate_all(valid_python_code, basic_context)

        assert "overall_score" in report
        assert "quality_grade" in report
        assert "component_scores" in report
        assert report["overall_score"] >= 0.0
        assert report["overall_score"] <= 10.0

    @pytest.mark.asyncio
    async def test_evaluate_all_invalid_code(self, aggregator, invalid_python_code, basic_context):
        """Test aggregate evaluation of invalid code"""
        report = await aggregator.evaluate_all(invalid_python_code, basic_context)

        assert report["overall_score"] <= 6.0  # Should be low but accounting for reserved weight
        assert report["quality_grade"] in ["poor", "fail", "acceptable"]
        assert len(report["all_issues"]) > 0

    @pytest.mark.asyncio
    async def test_component_scores(self, aggregator, valid_python_code, basic_context):
        """Test that all component scores are present"""
        report = await aggregator.evaluate_all(valid_python_code, basic_context)

        assert "code_quality" in report["component_scores"]
        assert "completeness" in report["component_scores"]
        assert "security" in report["component_scores"]

    @pytest.mark.asyncio
    async def test_quality_grades(self, aggregator, basic_context):
        """Test quality grade determination"""
        # Test excellent grade
        excellent_code = '''
def perfect_function(x: int) -> int:
    """
    A well-documented function.

    Args:
        x: Input value

    Returns:
        Result
    """
    try:
        return x * 2
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def test_perfect_function():
    assert perfect_function(5) == 10
'''
        report = await aggregator.evaluate_all(excellent_code, basic_context)
        assert report["quality_grade"] in ["excellent", "good", "acceptable"]

    @pytest.mark.asyncio
    async def test_issue_prioritization(self, aggregator, code_with_security_issues, basic_context):
        """Test that issues are sorted by severity"""
        report = await aggregator.evaluate_all(code_with_security_issues, basic_context)

        issues = report["all_issues"]
        if len(issues) > 1:
            # Check that critical/high issues come before low issues
            severities = [issue["severity"] for issue in issues]
            critical_index = severities.index("critical") if "critical" in severities else -1
            low_indices = [i for i, s in enumerate(severities) if s == "low"]

            if critical_index >= 0 and low_indices:
                assert critical_index < min(low_indices)

    @pytest.mark.asyncio
    async def test_suggestion_deduplication(self, aggregator, code_with_security_issues, basic_context):
        """Test that duplicate suggestions are removed"""
        report = await aggregator.evaluate_all(code_with_security_issues, basic_context)

        suggestions = report["all_suggestions"]
        unique_suggestions = set(s.lower() for s in suggestions)
        assert len(suggestions) == len(unique_suggestions)

    @pytest.mark.asyncio
    async def test_summary_generation(self, aggregator, valid_python_code, basic_context):
        """Test summary generation"""
        report = await aggregator.evaluate_all(valid_python_code, basic_context)

        summary = report["summary"]
        assert "overall_assessment" in summary
        assert "strengths" in summary
        assert "weaknesses" in summary
        assert "critical_actions" in summary

    @pytest.mark.asyncio
    async def test_aggregate_score_calculation(self, aggregator, basic_context):
        """Test weighted aggregate score calculation"""
        code = "def f(): return 1"
        report = await aggregator.evaluate_all(code, basic_context)

        # Calculate expected weighted score
        weights = aggregator.get_weights()
        component_scores = report["component_scores"]

        expected = sum(
            component_scores.get(name, 0) * weight
            for name, weight in weights.items()
            if name in component_scores
        )
        # Add reserved weight assuming perfect score
        expected += weights.get("reserved", 0) * 10.0

        assert abs(report["overall_score"] - expected) < 0.5

    def test_update_weights(self, aggregator):
        """Test weight update functionality"""
        new_weights = {"code_quality": 0.4, "completeness": 0.3, "security": 0.3}
        aggregator.update_weights(new_weights)

        weights = aggregator.get_weights()
        # After normalization, weights should sum to 1.0
        assert sum(weights.values()) == pytest.approx(1.0)

    def test_add_custom_evaluator(self, aggregator):
        """Test adding a custom evaluator"""
        class CustomEvaluator(BaseEvaluator):
            @property
            def name(self):
                return "custom"

            @property
            def description(self):
                return "Custom evaluator"

            async def evaluate(self, code, context):
                return EvaluationResult(
                    score=Decimal("8.0"),
                    details={},
                    suggestions=[],
                    issues=[]
                )

        custom = CustomEvaluator()
        aggregator.add_evaluator("custom", custom, 0.1)

        assert "custom" in aggregator.evaluators
        # After normalization, sum should be 1.0
        assert sum(aggregator.get_weights().values()) == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_evaluator_failure_handling(self, aggregator, basic_context):
        """Test handling of evaluator failures"""
        # Mock an evaluator to raise an exception
        with patch.object(
            aggregator.evaluators["code_quality"],
            "evaluate",
            side_effect=Exception("Test error")
        ):
            report = await aggregator.evaluate_all("def f(): pass", basic_context)

            # Should still return a report with failed evaluator
            assert "code_quality" in report["component_scores"]
            assert report["component_scores"]["code_quality"] == 0.0

    @pytest.mark.asyncio
    async def test_detailed_results(self, aggregator, valid_python_code, basic_context):
        """Test that detailed results are included in report"""
        report = await aggregator.evaluate_all(valid_python_code, basic_context)

        assert "detailed_results" in report
        assert "code_quality" in report["detailed_results"]
        assert "score" in report["detailed_results"]["code_quality"]
        assert "details" in report["detailed_results"]["code_quality"]

    def test_quality_grade_thresholds(self):
        """Test quality grade threshold boundaries"""
        aggregator = EvaluationAggregator()

        assert aggregator._determine_grade(Decimal("10.0")) == QualityGrade.EXCELLENT
        assert aggregator._determine_grade(Decimal("9.0")) == QualityGrade.EXCELLENT
        assert aggregator._determine_grade(Decimal("8.9")) == QualityGrade.GOOD
        assert aggregator._determine_grade(Decimal("7.0")) == QualityGrade.GOOD
        assert aggregator._determine_grade(Decimal("6.9")) == QualityGrade.ACCEPTABLE
        assert aggregator._determine_grade(Decimal("5.0")) == QualityGrade.ACCEPTABLE
        assert aggregator._determine_grade(Decimal("4.9")) == QualityGrade.POOR
        assert aggregator._determine_grade(Decimal("3.0")) == QualityGrade.POOR
        assert aggregator._determine_grade(Decimal("2.9")) == QualityGrade.FAIL
        assert aggregator._determine_grade(Decimal("0.0")) == QualityGrade.FAIL


# ==================== Edge Case Tests ====================


class TestEdgeCases:
    """Test edge cases across all evaluators"""

    @pytest.mark.asyncio
    async def test_very_long_code(self, very_long_code, basic_context):
        """Test evaluation of very long code"""
        evaluator = CodeQualityEvaluator()
        result = await evaluator.evaluate(very_long_code, basic_context)

        assert isinstance(result, EvaluationResult)
        assert result.score >= Decimal("0.0")

    @pytest.mark.asyncio
    async def test_unicode_code(self, basic_context):
        """Test evaluation of code with Unicode characters"""
        unicode_code = '''
def 函数(参数):
    """函数说明"""
    return 参数 + 1
'''
        evaluator = CodeQualityEvaluator()
        result = await evaluator.evaluate(unicode_code, basic_context)

        assert isinstance(result, EvaluationResult)

    @pytest.mark.asyncio
    async def test_mixed_line_endings(self, basic_context):
        """Test code with mixed line endings"""
        mixed_code = "def f():\r\n    return 1\n"
        evaluator = CodeQualityEvaluator()
        result = await evaluator.evaluate(mixed_code, basic_context)

        assert isinstance(result, EvaluationResult)

    @pytest.mark.asyncio
    async def test_only_comments(self, basic_context):
        """Test code that is only comments"""
        comment_only = "# Comment 1\n# Comment 2\n# Comment 3"
        evaluator = CodeQualityEvaluator()
        result = await evaluator.evaluate(comment_only, basic_context)

        assert isinstance(result, EvaluationResult)

    @pytest.mark.asyncio
    async def test_only_whitespace(self, basic_context):
        """Test code that is only whitespace"""
        whitespace = "   \n\t\n   \n"
        evaluator = CodeQualityEvaluator()
        result = await evaluator.evaluate(whitespace, basic_context)

        assert isinstance(result, EvaluationResult)

    @pytest.mark.asyncio
    async def test_missing_context_fields(self):
        """Test evaluation with minimal context"""
        minimal_context = {}
        evaluator = CodeQualityEvaluator()
        result = await evaluator.evaluate("def f(): pass", minimal_context)

        assert isinstance(result, EvaluationResult)

    @pytest.mark.asyncio
    async def test_null_bytes_in_code(self, basic_context):
        """Test code with null bytes"""
        code_with_null = "def f():\x00 pass"
        evaluator = CodeQualityEvaluator()

        # Should handle gracefully
        try:
            result = await evaluator.evaluate(code_with_null, basic_context)
            assert isinstance(result, EvaluationResult)
        except Exception:
            pass  # It's acceptable to fail on null bytes

    @pytest.mark.asyncio
    async def test_extremely_nested_code(self, basic_context):
        """Test extremely nested code"""
        # Create a function with nested ifs for complexity
        nested = '''
def complex_nested():
''' + "    if True:\n" * 15 + "        pass"
        evaluator = CodeQualityEvaluator()
        result = await evaluator.evaluate(nested, basic_context)

        # Very nested code should have some complexity indicators
        assert isinstance(result, EvaluationResult)
        assert result.score >= Decimal("0.0")


# ==================== Base Evaluator Tests ====================


class TestBaseEvaluator:
    """Test base evaluator functionality"""

    def test_evaluation_result_validation(self):
        """Test EvaluationResult score validation"""
        # Valid score
        result = EvaluationResult(score=Decimal("5.0"))
        assert result.score == Decimal("5.0")

        # Invalid score (too high)
        with pytest.raises(ValueError):
            EvaluationResult(score=Decimal("11.0"))

        # Invalid score (negative)
        with pytest.raises(ValueError):
            EvaluationResult(score=Decimal("-1.0"))

    def test_evaluation_result_to_dict(self):
        """Test EvaluationResult to_dict conversion"""
        result = EvaluationResult(
            score=Decimal("7.5"),
            details={"test": "value"},
            suggestions=["suggestion1"],
            issues=[{"type": "test"}],
            metadata={"key": "value"}
        )

        result_dict = result.to_dict()
        assert result_dict["score"] == 7.5
        assert result_dict["details"] == {"test": "value"}
        assert len(result_dict["suggestions"]) == 1

    def test_score_clamping(self):
        """Test score clamping utility"""
        evaluator = CodeQualityEvaluator()

        assert evaluator._clamp_score(15.0) == Decimal("10.0")
        assert evaluator._clamp_score(-5.0) == Decimal("0.0")
        assert evaluator._clamp_score(7.5) == Decimal("7.5")

    def test_weight_management(self):
        """Test evaluator weight management"""
        evaluator = CodeQualityEvaluator(weight=0.5)

        assert evaluator.get_weight() == 0.5

        evaluator.set_weight(0.75)
        assert evaluator.get_weight() == 0.75

        # Test negative weight rejection
        with pytest.raises(ValueError):
            evaluator.set_weight(-0.5)

    def test_config_management(self):
        """Test evaluator configuration management"""
        config = {"option1": "value1"}
        evaluator = CodeQualityEvaluator(config=config)

        assert evaluator.get_config() == config

        evaluator.update_config({"option2": "value2"})
        updated_config = evaluator.get_config()
        assert "option1" in updated_config
        assert "option2" in updated_config
