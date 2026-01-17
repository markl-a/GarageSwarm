"""
Completeness Evaluator

Evaluates whether the code meets all requirements and includes proper
error handling, tests, and documentation.
"""

import re
import ast
from typing import Any, Dict, List, Set
from decimal import Decimal
import structlog

from .base import BaseEvaluator, EvaluationResult

logger = structlog.get_logger()


class CompletenessEvaluator(BaseEvaluator):
    """
    Evaluates code completeness:
    - Requirement coverage
    - Error handling
    - Test code presence
    - Documentation/comments
    """

    @property
    def name(self) -> str:
        return "completeness"

    @property
    def description(self) -> str:
        return "Evaluates requirement coverage, error handling, tests, and documentation"

    async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate code completeness

        Scoring formula:
        score = (requirement_coverage * 0.8) + (error_handling * 0.1) + (tests * 0.1)
        Then scale to 0-10

        Args:
            code: Source code to evaluate
            context: Context including description, requirements, language

        Returns:
            EvaluationResult with completeness score and details
        """
        language = context.get("language", "python").lower()
        description = context.get("description", "")
        explicit_requirements = context.get("requirements", [])

        issues = []
        suggestions = []
        details = {
            "requirement_coverage": 0.0,
            "requirements_met": 0,
            "total_requirements": 0,
            "error_handling_score": 0.0,
            "has_tests": False,
            "has_documentation": False,
            "missing_requirements": []
        }

        # Extract requirements from description
        requirements = self._extract_requirements(description, explicit_requirements)
        details["total_requirements"] = len(requirements)

        if len(requirements) > 0:
            # Check requirement coverage
            coverage_result = self._check_requirement_coverage(code, requirements, language)
            details["requirement_coverage"] = coverage_result["coverage"]
            details["requirements_met"] = coverage_result["met_count"]
            details["missing_requirements"] = coverage_result["missing"]
            issues.extend(coverage_result["issues"])
            suggestions.extend(coverage_result["suggestions"])
        else:
            # No explicit requirements, assume basic coverage
            details["requirement_coverage"] = 80.0  # Default reasonable coverage

        # Check error handling
        error_handling_result = self._check_error_handling(code, language)
        details["error_handling_score"] = error_handling_result["score"]
        details["error_handling_details"] = error_handling_result["details"]
        issues.extend(error_handling_result["issues"])
        suggestions.extend(error_handling_result["suggestions"])

        # Check for tests
        test_result = self._check_tests(code, language)
        details["has_tests"] = test_result["has_tests"]
        details["test_coverage"] = test_result["coverage"]
        issues.extend(test_result["issues"])
        suggestions.extend(test_result["suggestions"])

        # Check documentation
        doc_result = self._check_documentation(code, language)
        details["has_documentation"] = doc_result["has_documentation"]
        details["documentation_score"] = doc_result["score"]
        issues.extend(doc_result["issues"])
        suggestions.extend(doc_result["suggestions"])

        # Calculate overall score
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

    def _extract_requirements(self, description: str, explicit_requirements: List[str]) -> List[str]:
        """Extract requirements from description and explicit list"""
        requirements = list(explicit_requirements) if explicit_requirements else []

        # Extract from description using common patterns
        # Look for bullet points, numbered lists, "must", "should", etc.
        patterns = [
            r'[-*•]\s+(.+)',  # Bullet points
            r'\d+\.\s+(.+)',  # Numbered lists
            r'(?:must|should|need to|required to)\s+(.+?)(?:[.!]|$)',  # Modal verbs
            r'implement\s+(.+?)(?:[.!]|$)',  # Implementation requirements
            r'create\s+(.+?)(?:[.!]|$)',  # Creation requirements
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                req = match.group(1).strip()
                if len(req) > 10 and req not in requirements:  # Filter out too short matches
                    requirements.append(req)

        # If no requirements found, extract key nouns/verbs as basic requirements
        if not requirements:
            # Split into sentences and use first few as basic requirements
            sentences = [s.strip() for s in description.split('.') if s.strip()]
            requirements = sentences[:3] if sentences else []

        return requirements

    def _check_requirement_coverage(
        self, code: str, requirements: List[str], language: str
    ) -> Dict[str, Any]:
        """Check how many requirements are covered in the code"""
        issues = []
        suggestions = []
        met_requirements = []
        missing_requirements = []

        # Extract key terms from code
        code_lower = code.lower()
        code_terms = set(re.findall(r'\b\w+\b', code_lower))

        for req in requirements:
            # Extract key terms from requirement
            req_terms = set(re.findall(r'\b\w{3,}\b', req.lower()))  # Words with 3+ chars
            req_terms -= {'the', 'and', 'for', 'that', 'with', 'this', 'from', 'have', 'are'}

            # Check if significant portion of terms are in code
            if req_terms:
                matches = len(req_terms & code_terms)
                coverage = matches / len(req_terms)

                if coverage >= 0.5:  # At least 50% of terms present
                    met_requirements.append(req)
                else:
                    missing_requirements.append(req)
                    issues.append({
                        "type": "requirement",
                        "severity": "high",
                        "message": f"Requirement not fully implemented: {req[:80]}..."
                    })
            else:
                # If no terms extracted, assume not met
                missing_requirements.append(req)

        met_count = len(met_requirements)
        total_count = len(requirements)
        coverage = (met_count / total_count * 100) if total_count > 0 else 0

        if coverage < 50:
            suggestions.append("Implement missing requirements to improve completeness")
        elif coverage < 80:
            suggestions.append("Address remaining requirements for full coverage")

        return {
            "coverage": round(coverage, 1),
            "met_count": met_count,
            "missing": missing_requirements,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_error_handling(self, code: str, language: str) -> Dict[str, Any]:
        """Check error handling completeness"""
        issues = []
        suggestions = []
        score = 0.0
        details = {
            "has_try_except": False,
            "exception_count": 0,
            "generic_exceptions": 0,
            "has_logging": False
        }

        if language == "python":
            try:
                tree = ast.parse(code)

                # Count try-except blocks
                try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
                details["has_try_except"] = len(try_blocks) > 0
                details["exception_count"] = len(try_blocks)

                # Check for generic exceptions
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        if node.type is None:  # Bare except
                            details["generic_exceptions"] += 1
                            issues.append({
                                "type": "error_handling",
                                "severity": "medium",
                                "line": node.lineno,
                                "message": "Avoid bare except clauses"
                            })
                        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                            details["generic_exceptions"] += 1
                            issues.append({
                                "type": "error_handling",
                                "severity": "low",
                                "line": node.lineno,
                                "message": "Consider catching specific exceptions instead of generic Exception"
                            })

                # Check for logging
                details["has_logging"] = any(
                    re.search(r'\blogger\.|logging\.', code)
                )

                # Calculate score (0-100)
                if details["has_try_except"]:
                    score = 60  # Base score for having error handling

                    # Bonus for multiple handlers
                    score += min(details["exception_count"] * 10, 20)

                    # Penalty for too many generic exceptions
                    if details["generic_exceptions"] > 0:
                        score -= details["generic_exceptions"] * 5

                    # Bonus for logging
                    if details["has_logging"]:
                        score += 20

                    score = min(score, 100)
                else:
                    issues.append({
                        "type": "error_handling",
                        "severity": "high",
                        "message": "No error handling found"
                    })
                    suggestions.append("Add try-except blocks to handle potential errors")

            except:
                # Can't parse, assume no error handling
                score = 0

        else:
            # Basic check for other languages
            if re.search(r'\b(try|catch|except|rescue)\b', code, re.IGNORECASE):
                score = 60
                details["has_try_except"] = True
            else:
                issues.append({
                    "type": "error_handling",
                    "severity": "medium",
                    "message": "No error handling detected"
                })

        return {
            "score": round(score, 1),
            "details": details,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_tests(self, code: str, language: str) -> Dict[str, Any]:
        """Check for test code"""
        issues = []
        suggestions = []
        has_tests = False
        coverage = 0.0

        # Look for test patterns
        test_patterns = [
            r'\btest_\w+\s*\(',  # Python test functions
            r'\bdef test_',  # Python test methods
            r'\bclass Test\w+',  # Python test classes
            r'\b@pytest\.',  # Pytest decorators
            r'\bunittest\.',  # Unittest
            r'\bassert\s+',  # Assertions
            r'\bexpect\(',  # JS/TS expectations
            r'\bit\([\'"]',  # JS/TS test blocks
            r'\bdescribe\([\'"]',  # JS/TS describe blocks
        ]

        test_indicators = 0
        for pattern in test_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            test_indicators += len(matches)

        if test_indicators > 0:
            has_tests = True
            # Rough estimate of test coverage based on number of test indicators
            coverage = min(test_indicators * 10, 100)
        else:
            issues.append({
                "type": "testing",
                "severity": "medium",
                "message": "No test code found"
            })
            suggestions.append("Add unit tests to verify code functionality")

        return {
            "has_tests": has_tests,
            "coverage": coverage,
            "test_indicators": test_indicators,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_documentation(self, code: str, language: str) -> Dict[str, Any]:
        """Check documentation quality"""
        issues = []
        suggestions = []
        has_documentation = False
        score = 0.0

        if language == "python":
            try:
                tree = ast.parse(code)

                # Count docstrings
                module_docstring = ast.get_docstring(tree)
                has_module_doc = module_docstring is not None

                function_count = 0
                documented_functions = 0
                class_count = 0
                documented_classes = 0

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        function_count += 1
                        if ast.get_docstring(node):
                            documented_functions += 1
                    elif isinstance(node, ast.ClassDef):
                        class_count += 1
                        if ast.get_docstring(node):
                            documented_classes += 1

                # Calculate documentation score
                if has_module_doc:
                    score += 20

                if function_count > 0:
                    func_doc_ratio = documented_functions / function_count
                    score += func_doc_ratio * 40
                else:
                    score += 20  # No functions, give partial credit

                if class_count > 0:
                    class_doc_ratio = documented_classes / class_count
                    score += class_doc_ratio * 40
                else:
                    score += 20  # No classes, give partial credit

                has_documentation = score > 30

                if not has_module_doc:
                    issues.append({
                        "type": "documentation",
                        "severity": "low",
                        "message": "Missing module docstring"
                    })

                if function_count > documented_functions:
                    suggestions.append(
                        f"Add docstrings to {function_count - documented_functions} undocumented functions"
                    )

            except:
                # Basic comment check
                comment_lines = len([l for l in code.split('\n') if l.strip().startswith('#')])
                total_lines = len(code.split('\n'))
                if comment_lines / total_lines > 0.1:
                    has_documentation = True
                    score = 50

        else:
            # Basic check for comments
            comment_patterns = [
                r'//.*',  # C-style single line
                r'#.*',   # Python/Ruby style
                r'/\*.*?\*/',  # C-style multiline
            ]

            comment_count = 0
            for pattern in comment_patterns:
                matches = re.findall(pattern, code, re.DOTALL)
                comment_count += len(matches)

            total_lines = len(code.split('\n'))
            if comment_count > total_lines * 0.1:
                has_documentation = True
                score = 60

        if not has_documentation:
            suggestions.append("Add documentation to explain code functionality")

        return {
            "has_documentation": has_documentation,
            "score": round(score, 1),
            "issues": issues,
            "suggestions": suggestions
        }

    def _calculate_score(self, details: Dict[str, Any]) -> Decimal:
        """
        Calculate completeness score

        Formula:
        score = (requirement_coverage * 0.6) + (error_handling * 0.2) + (test_bonus) + (doc_bonus)
        Then scale to 0-10
        """
        # Requirement coverage (0-100) contributes 60%
        req_score = details.get("requirement_coverage", 0) * 0.006  # 0-6 points

        # Error handling (0-100) contributes 20%
        error_score = details.get("error_handling_score", 0) * 0.002  # 0-2 points

        # Test presence adds up to 1 point
        test_bonus = 1.0 if details.get("has_tests", False) else 0.0

        # Documentation adds up to 1 point
        doc_score = details.get("documentation_score", 0) * 0.01  # 0-1 points

        # Calculate total (0-10 scale)
        total_score = req_score + error_score + test_bonus + doc_score

        return self._clamp_score(total_score)
