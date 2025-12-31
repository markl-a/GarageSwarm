"""
Code Quality Evaluator

Evaluates code quality based on syntax, linting, complexity, and documentation.
Uses real tools (pylint, flake8) when available, falls back to simulated analysis.
"""

import ast
import json
import subprocess
import tempfile
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
from pathlib import Path
import structlog

from .base import BaseEvaluator, EvaluationResult

logger = structlog.get_logger()


class CodeQualityEvaluator(BaseEvaluator):
    """
    Evaluates code quality aspects:
    - Syntax errors
    - Linting issues (real pylint/flake8 when available)
    - Cyclomatic complexity
    - Comment coverage
    """

    def __init__(self, weight: float = 1.0, config: Optional[Dict[str, Any]] = None):
        """
        Initialize evaluator

        Args:
            weight: Weight for this evaluator in aggregation
            config: Configuration options:
                - timeout: Subprocess timeout in seconds (default: 30)
                - use_real_tools: Whether to use real linters (default: True)
                - pylint_enabled: Enable pylint (default: True)
                - flake8_enabled: Enable flake8 (default: True)
        """
        super().__init__(weight, config)
        self._timeout = self.config.get("timeout", 30)
        self._use_real_tools = self.config.get("use_real_tools", True)
        self._pylint_enabled = self.config.get("pylint_enabled", True)
        self._flake8_enabled = self.config.get("flake8_enabled", True)

        # Check tool availability
        self._tools_available = self._check_tools_available()

    @property
    def name(self) -> str:
        return "code_quality"

    @property
    def description(self) -> str:
        return "Evaluates code syntax, linting, complexity, and documentation using real tools"

    def _check_tools_available(self) -> Dict[str, bool]:
        """Check which linting tools are available"""
        available = {
            "pylint": False,
            "flake8": False
        }

        if not self._use_real_tools:
            return available

        # Check pylint
        if self._pylint_enabled:
            try:
                result = subprocess.run(
                    ["pylint", "--version"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                available["pylint"] = result.returncode == 0
                if available["pylint"]:
                    logger.info("pylint is available")
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                logger.warning(f"pylint not available: {e}")

        # Check flake8
        if self._flake8_enabled:
            try:
                result = subprocess.run(
                    ["flake8", "--version"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                available["flake8"] = result.returncode == 0
                if available["flake8"]:
                    logger.info("flake8 is available")
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                logger.warning(f"flake8 not available: {e}")

        return available

    async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate code quality

        Scoring formula:
        base_score = 10.0
        score = base_score - (syntax_errors * 5) - (lint_warnings * 0.1) - (high_complexity * 1)

        Args:
            code: Source code to evaluate
            context: Context including language, description, etc.

        Returns:
            EvaluationResult with quality score and details
        """
        language = context.get("language", "python").lower()

        # Initialize results
        issues = []
        suggestions = []
        details = {
            "syntax_errors": 0,
            "lint_warnings": 0,
            "lint_errors": 0,
            "high_complexity_count": 0,
            "comment_coverage": 0.0,
            "total_lines": 0,
            "comment_lines": 0,
            "code_lines": 0,
            "tools_used": []
        }

        # Only evaluate Python code for now
        if language == "python":
            # Check syntax
            syntax_result = self._check_syntax(code)
            details["syntax_errors"] = syntax_result["error_count"]
            issues.extend(syntax_result["issues"])

            # Only continue if syntax is valid
            if details["syntax_errors"] == 0:
                # Run real linting if available
                if self._use_real_tools and any(self._tools_available.values()):
                    lint_result = await self._run_real_linting(code)
                    details["lint_warnings"] = lint_result["warning_count"]
                    details["lint_errors"] = lint_result["error_count"]
                    details["tools_used"] = lint_result["tools_used"]
                    issues.extend(lint_result["issues"])
                    suggestions.extend(lint_result["suggestions"])
                else:
                    # Fall back to simulated linting
                    lint_result = self._simulate_linting(code)
                    details["lint_warnings"] = lint_result["warning_count"]
                    details["tools_used"] = ["simulated"]
                    issues.extend(lint_result["issues"])
                    suggestions.extend(lint_result["suggestions"])

                # Calculate complexity
                complexity_result = self._calculate_complexity(code)
                details["high_complexity_count"] = complexity_result["high_complexity_count"]
                details["complexity_details"] = complexity_result["details"]
                issues.extend(complexity_result["issues"])
                suggestions.extend(complexity_result["suggestions"])

                # Calculate comment coverage
                comment_result = self._calculate_comment_coverage(code)
                details.update(comment_result)

                if comment_result["comment_coverage"] < 10.0:
                    suggestions.append("Add more comments to improve code readability")
                    issues.append({
                        "type": "documentation",
                        "severity": "low",
                        "message": f"Low comment coverage: {comment_result['comment_coverage']:.1f}%"
                    })
        else:
            # For non-Python code, do basic checks
            basic_result = self._basic_code_check(code, language)
            details.update(basic_result["details"])
            issues.extend(basic_result["issues"])
            suggestions.extend(basic_result["suggestions"])

        # Calculate score
        score = self._calculate_score(details)

        return EvaluationResult(
            score=score,
            details=details,
            suggestions=suggestions,
            issues=issues,
            metadata={
                "language": language,
                "evaluator": self.name,
                "tools_available": self._tools_available
            }
        )

    def _check_syntax(self, code: str) -> Dict[str, Any]:
        """Check Python syntax errors"""
        try:
            ast.parse(code)
            return {
                "error_count": 0,
                "issues": []
            }
        except SyntaxError as e:
            return {
                "error_count": 1,
                "issues": [{
                    "type": "syntax",
                    "severity": "critical",
                    "line": e.lineno,
                    "message": f"Syntax error: {e.msg}"
                }]
            }
        except Exception as e:
            return {
                "error_count": 1,
                "issues": [{
                    "type": "syntax",
                    "severity": "critical",
                    "message": f"Parse error: {str(e)}"
                }]
            }

    async def _run_real_linting(self, code: str) -> Dict[str, Any]:
        """
        Run real linting tools (pylint and flake8)

        Args:
            code: Python code to lint

        Returns:
            Dictionary with warning_count, error_count, issues, suggestions, tools_used
        """
        issues = []
        suggestions = []
        warning_count = 0
        error_count = 0
        tools_used = []

        # Create temporary file for linting
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            # Run pylint
            if self._tools_available.get("pylint", False):
                pylint_result = await self._run_pylint(tmp_path)
                issues.extend(pylint_result["issues"])
                suggestions.extend(pylint_result["suggestions"])
                warning_count += pylint_result["warning_count"]
                error_count += pylint_result["error_count"]
                tools_used.append("pylint")

            # Run flake8
            if self._tools_available.get("flake8", False):
                flake8_result = await self._run_flake8(tmp_path)
                issues.extend(flake8_result["issues"])
                suggestions.extend(flake8_result["suggestions"])
                warning_count += flake8_result["warning_count"]
                error_count += flake8_result["error_count"]
                tools_used.append("flake8")

        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_path}: {e}")

        # Deduplicate issues (same line and similar message)
        issues = self._deduplicate_issues(issues)

        # Add general suggestions based on issue count
        if warning_count > 20:
            suggestions.append("Consider running an autoformatter like black to fix many style issues automatically")
        elif warning_count > 10:
            suggestions.append("Review and fix linting warnings to improve code quality")

        return {
            "warning_count": warning_count,
            "error_count": error_count,
            "issues": issues,
            "suggestions": suggestions,
            "tools_used": tools_used
        }

    async def _run_pylint(self, file_path: str) -> Dict[str, Any]:
        """
        Run pylint on a file

        Args:
            file_path: Path to Python file

        Returns:
            Dictionary with issues, suggestions, warning_count, error_count
        """
        issues = []
        suggestions = []
        warning_count = 0
        error_count = 0

        try:
            # Run pylint with JSON output
            result = subprocess.run(
                [
                    "pylint",
                    "--output-format=json",
                    "--score=no",
                    "--reports=no",
                    file_path
                ],
                capture_output=True,
                timeout=self._timeout,
                text=True
            )

            # Parse JSON output
            if result.stdout:
                try:
                    pylint_messages = json.loads(result.stdout)

                    for msg in pylint_messages:
                        severity = self._map_pylint_severity(msg.get("type", ""))
                        issue_type = msg.get("symbol", "style")

                        issue = {
                            "type": issue_type,
                            "severity": severity,
                            "line": msg.get("line", 0),
                            "column": msg.get("column", 0),
                            "message": msg.get("message", ""),
                            "source": "pylint"
                        }
                        issues.append(issue)

                        # Count by severity
                        if severity in ["critical", "high"]:
                            error_count += 1
                        else:
                            warning_count += 1

                    # Add specific suggestions based on common issues
                    issue_types = [msg.get("symbol", "") for msg in pylint_messages]
                    if "missing-docstring" in issue_types:
                        suggestions.append("Add docstrings to functions and classes")
                    if "line-too-long" in issue_types:
                        suggestions.append("Format code to keep lines under 120 characters")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse pylint JSON output: {e}")

        except subprocess.TimeoutExpired:
            logger.warning(f"pylint timed out after {self._timeout} seconds")
            error_count += 1
            issues.append({
                "type": "timeout",
                "severity": "high",
                "message": "pylint analysis timed out",
                "source": "pylint"
            })
        except Exception as e:
            logger.error(f"Error running pylint: {e}")

        return {
            "issues": issues,
            "suggestions": suggestions,
            "warning_count": warning_count,
            "error_count": error_count
        }

    async def _run_flake8(self, file_path: str) -> Dict[str, Any]:
        """
        Run flake8 on a file

        Args:
            file_path: Path to Python file

        Returns:
            Dictionary with issues, suggestions, warning_count, error_count
        """
        issues = []
        suggestions = []
        warning_count = 0
        error_count = 0

        try:
            # Run flake8
            result = subprocess.run(
                [
                    "flake8",
                    "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
                    "--max-line-length=120",
                    file_path
                ],
                capture_output=True,
                timeout=self._timeout,
                text=True
            )

            # Parse output
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue

                    # Parse flake8 output format: file:line:col: code message
                    match = re.match(r"^[^:]+:(\d+):(\d+):\s+([A-Z]\d+)\s+(.+)$", line)
                    if match:
                        line_num = int(match.group(1))
                        col_num = int(match.group(2))
                        error_code = match.group(3)
                        message = match.group(4)

                        severity = self._map_flake8_severity(error_code)

                        issue = {
                            "type": error_code,
                            "severity": severity,
                            "line": line_num,
                            "column": col_num,
                            "message": f"{error_code}: {message}",
                            "source": "flake8"
                        }
                        issues.append(issue)

                        # Count by severity
                        if severity in ["critical", "high"]:
                            error_count += 1
                        else:
                            warning_count += 1

                # Add suggestions based on common error codes
                error_codes = [i["type"] for i in issues]
                if any(code.startswith("E") for code in error_codes):
                    suggestions.append("Fix PEP 8 style errors")
                if any(code.startswith("W") for code in error_codes):
                    suggestions.append("Address PEP 8 style warnings")
                if any(code.startswith("F") for code in error_codes):
                    suggestions.append("Fix undefined names and import issues")

        except subprocess.TimeoutExpired:
            logger.warning(f"flake8 timed out after {self._timeout} seconds")
            error_count += 1
            issues.append({
                "type": "timeout",
                "severity": "high",
                "message": "flake8 analysis timed out",
                "source": "flake8"
            })
        except Exception as e:
            logger.error(f"Error running flake8: {e}")

        return {
            "issues": issues,
            "suggestions": suggestions,
            "warning_count": warning_count,
            "error_count": error_count
        }

    def _map_pylint_severity(self, msg_type: str) -> str:
        """Map pylint message type to severity level"""
        severity_map = {
            "error": "critical",
            "fatal": "critical",
            "warning": "medium",
            "convention": "low",
            "refactor": "low",
            "info": "low"
        }
        return severity_map.get(msg_type.lower(), "medium")

    def _map_flake8_severity(self, error_code: str) -> str:
        """Map flake8 error code to severity level"""
        # E9xx and F8xx are critical errors
        if error_code.startswith("E9") or error_code.startswith("F8"):
            return "critical"
        # F-series are usually errors (undefined names, etc.)
        elif error_code.startswith("F"):
            return "high"
        # E-series are style errors
        elif error_code.startswith("E"):
            return "medium"
        # W-series are warnings
        elif error_code.startswith("W"):
            return "low"
        # C-series are complexity warnings
        elif error_code.startswith("C"):
            return "medium"
        else:
            return "medium"

    def _deduplicate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate issues (same line and similar message)

        Args:
            issues: List of issue dictionaries

        Returns:
            Deduplicated list of issues
        """
        seen = set()
        deduplicated = []

        for issue in issues:
            # Create a key from line and message type
            key = (issue.get("line", 0), issue.get("type", ""))

            if key not in seen:
                seen.add(key)
                deduplicated.append(issue)

        return deduplicated

    def _simulate_linting(self, code: str) -> Dict[str, Any]:
        """
        Simulate linting checks (fallback when real tools unavailable)

        Checks for common issues:
        - Long lines (>120 characters)
        - Missing docstrings
        - Unused imports
        - Too many blank lines
        """
        issues = []
        suggestions = []
        warning_count = 0

        lines = code.split("\n")

        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                warning_count += 1
                issues.append({
                    "type": "style",
                    "severity": "low",
                    "line": i,
                    "message": f"Line too long ({len(line)} > 120 characters)",
                    "source": "simulated"
                })

        # Check for docstrings in classes and functions
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        warning_count += 1
                        issues.append({
                            "type": "documentation",
                            "severity": "medium",
                            "line": node.lineno,
                            "message": f"Missing docstring for {node.__class__.__name__} '{node.name}'",
                            "source": "simulated"
                        })
        except:
            pass  # Already handled in syntax check

        # Check for multiple consecutive blank lines
        blank_count = 0
        for i, line in enumerate(lines, 1):
            if not line.strip():
                blank_count += 1
                if blank_count > 2:
                    warning_count += 1
                    issues.append({
                        "type": "style",
                        "severity": "low",
                        "line": i,
                        "message": "More than 2 consecutive blank lines",
                        "source": "simulated"
                    })
            else:
                blank_count = 0

        if warning_count > 10:
            suggestions.append("Consider installing pylint and flake8 for more comprehensive analysis")
        elif warning_count > 5:
            suggestions.append("Fix remaining style and documentation issues")

        return {
            "warning_count": warning_count,
            "issues": issues,
            "suggestions": suggestions
        }

    def _calculate_complexity(self, code: str) -> Dict[str, Any]:
        """
        Calculate cyclomatic complexity

        High complexity: > 10
        """
        issues = []
        suggestions = []
        high_complexity_count = 0
        complexity_details = []

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = self._calc_function_complexity(node)
                    complexity_details.append({
                        "function": node.name,
                        "line": node.lineno,
                        "complexity": complexity
                    })

                    if complexity > 10:
                        high_complexity_count += 1
                        issues.append({
                            "type": "complexity",
                            "severity": "high",
                            "line": node.lineno,
                            "message": f"Function '{node.name}' has high complexity: {complexity}"
                        })
                        suggestions.append(f"Refactor function '{node.name}' to reduce complexity")
                    elif complexity > 7:
                        issues.append({
                            "type": "complexity",
                            "severity": "medium",
                            "line": node.lineno,
                            "message": f"Function '{node.name}' has moderate complexity: {complexity}"
                        })
        except:
            pass  # Already handled in syntax check

        return {
            "high_complexity_count": high_complexity_count,
            "details": complexity_details,
            "issues": issues,
            "suggestions": suggestions
        }

    def _calc_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a function"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points add to complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each boolean operation adds complexity
                complexity += len(child.values) - 1

        return complexity

    def _calculate_comment_coverage(self, code: str) -> Dict[str, Any]:
        """Calculate comment coverage percentage"""
        lines = code.split("\n")
        total_lines = len(lines)
        comment_lines = 0
        code_lines = 0

        in_multiline_string = False
        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Check for multiline strings/comments
            if '"""' in stripped or "'''" in stripped:
                in_multiline_string = not in_multiline_string
                comment_lines += 1
                continue

            if in_multiline_string:
                comment_lines += 1
                continue

            # Check for single-line comments
            if stripped.startswith("#"):
                comment_lines += 1
            else:
                code_lines += 1
                # Inline comments
                if "#" in stripped:
                    comment_lines += 0.5

        comment_coverage = (comment_lines / total_lines * 100) if total_lines > 0 else 0

        return {
            "total_lines": total_lines,
            "comment_lines": int(comment_lines),
            "code_lines": code_lines,
            "comment_coverage": round(comment_coverage, 1)
        }

    def _basic_code_check(self, code: str, language: str) -> Dict[str, Any]:
        """Basic checks for non-Python code"""
        issues = []
        suggestions = []

        lines = code.split("\n")
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip()])

        details = {
            "total_lines": total_lines,
            "code_lines": code_lines,
            "syntax_errors": 0,
            "lint_warnings": 0,
            "tools_used": ["basic"]
        }

        # Basic sanity checks
        if total_lines == 0 or code_lines == 0:
            issues.append({
                "type": "content",
                "severity": "critical",
                "message": "Code is empty"
            })
            details["syntax_errors"] = 1

        if code_lines < 5:
            suggestions.append("Code seems very short, ensure all requirements are met")

        return {
            "details": details,
            "issues": issues,
            "suggestions": suggestions
        }

    def _calculate_score(self, details: Dict[str, Any]) -> Decimal:
        """
        Calculate final score based on formula:
        score = 10 - (syntax_errors * 5) - (lint_errors * 1) - (lint_warnings * 0.1) - (high_complexity * 1)
        """
        base_score = 10.0

        # Apply penalties
        score = base_score
        score -= details.get("syntax_errors", 0) * 5
        score -= details.get("lint_errors", 0) * 1
        score -= details.get("lint_warnings", 0) * 0.1
        score -= details.get("high_complexity_count", 0) * 1

        # Small bonus for good comment coverage
        comment_coverage = details.get("comment_coverage", 0)
        if comment_coverage > 20:
            score += 0.5
        if comment_coverage > 30:
            score += 0.5

        return self._clamp_score(score)
