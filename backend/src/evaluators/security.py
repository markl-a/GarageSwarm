"""
Security Evaluator

Evaluates code security by checking for common vulnerabilities and security issues.
"""

import re
from typing import Any, Dict, List, Tuple
from decimal import Decimal
import structlog

from .base import BaseEvaluator, EvaluationResult

logger = structlog.get_logger()


class SecurityEvaluator(BaseEvaluator):
    """
    Evaluates code security:
    - Injection vulnerabilities (SQL, XSS, Command)
    - Hardcoded secrets
    - Insecure functions
    - Dependency vulnerabilities (simulated)
    """

    @property
    def name(self) -> str:
        return "security"

    @property
    def description(self) -> str:
        return "Evaluates code security and identifies vulnerabilities"

    async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate code security

        Scoring formula:
        score = 10 - (high_risk * 3) - (medium_risk * 1) - (low_risk * 0.5)

        Args:
            code: Source code to evaluate
            context: Context including language, description, etc.

        Returns:
            EvaluationResult with security score and details
        """
        language = context.get("language", "python").lower()

        issues = []
        suggestions = []
        vulnerabilities = {
            "high_risk": [],
            "medium_risk": [],
            "low_risk": []
        }

        # Check for SQL injection
        sql_result = self._check_sql_injection(code, language)
        self._categorize_vulnerabilities(sql_result, vulnerabilities)
        issues.extend(sql_result["issues"])
        suggestions.extend(sql_result["suggestions"])

        # Check for XSS vulnerabilities
        xss_result = self._check_xss_vulnerabilities(code, language)
        self._categorize_vulnerabilities(xss_result, vulnerabilities)
        issues.extend(xss_result["issues"])
        suggestions.extend(xss_result["suggestions"])

        # Check for command injection
        cmd_result = self._check_command_injection(code, language)
        self._categorize_vulnerabilities(cmd_result, vulnerabilities)
        issues.extend(cmd_result["issues"])
        suggestions.extend(cmd_result["suggestions"])

        # Check for hardcoded secrets
        secrets_result = self._check_hardcoded_secrets(code)
        self._categorize_vulnerabilities(secrets_result, vulnerabilities)
        issues.extend(secrets_result["issues"])
        suggestions.extend(secrets_result["suggestions"])

        # Check for insecure functions
        insecure_result = self._check_insecure_functions(code, language)
        self._categorize_vulnerabilities(insecure_result, vulnerabilities)
        issues.extend(insecure_result["issues"])
        suggestions.extend(insecure_result["suggestions"])

        # Simulate dependency vulnerability scan
        deps_result = self._simulate_dependency_scan(code, language)
        self._categorize_vulnerabilities(deps_result, vulnerabilities)
        issues.extend(deps_result["issues"])
        suggestions.extend(deps_result["suggestions"])

        # Count vulnerabilities by severity
        high_count = len(vulnerabilities["high_risk"])
        medium_count = len(vulnerabilities["medium_risk"])
        low_count = len(vulnerabilities["low_risk"])

        details = {
            "high_risk_count": high_count,
            "medium_risk_count": medium_count,
            "low_risk_count": low_count,
            "total_vulnerabilities": high_count + medium_count + low_count,
            "vulnerabilities": vulnerabilities,
            "requires_human_review": False
        }

        # Calculate score
        score = self._calculate_score(high_count, medium_count, low_count)

        # Flag for human review if score is too low
        if score < Decimal("4.0"):
            details["requires_human_review"] = True
            issues.append({
                "type": "security",
                "severity": "critical",
                "message": "Security score below threshold - requires human review"
            })

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

    def _check_sql_injection(self, code: str, language: str) -> Dict[str, Any]:
        """Check for SQL injection vulnerabilities"""
        issues = []
        suggestions = []
        vulnerabilities = []

        # Patterns that suggest SQL injection risk
        sql_patterns = [
            (r'execute\s*\(\s*["\'].*%s.*["\']', "high", "SQL query with string formatting - use parameterized queries"),
            (r'execute\s*\(\s*f["\'].*\{.*\}.*["\']', "high", "SQL query with f-string - use parameterized queries"),
            (r'execute\s*\(\s*.*\+.*["\']', "high", "SQL query with string concatenation - use parameterized queries"),
            (r'raw\s*\(', "medium", "Raw SQL query detected - ensure proper sanitization"),
            (r'\.format\s*\(.*SELECT|INSERT|UPDATE|DELETE', "high", "SQL query with .format() - use parameterized queries"),
        ]

        for pattern, severity, message in sql_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                vulnerabilities.append({
                    "severity": severity,
                    "type": "sql_injection",
                    "line": line_num,
                    "message": message
                })
                issues.append({
                    "type": "sql_injection",
                    "severity": severity,
                    "line": line_num,
                    "message": message
                })

        if vulnerabilities:
            suggestions.append("Use parameterized queries or ORM to prevent SQL injection")

        return {
            "vulnerabilities": vulnerabilities,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_xss_vulnerabilities(self, code: str, language: str) -> Dict[str, Any]:
        """Check for XSS vulnerabilities"""
        issues = []
        suggestions = []
        vulnerabilities = []

        # Patterns that suggest XSS risk
        xss_patterns = [
            (r'\.innerHTML\s*=', "high", "Direct innerHTML assignment - potential XSS risk"),
            (r'document\.write\s*\(', "high", "document.write() - potential XSS risk"),
            (r'eval\s*\(', "high", "eval() usage - potential XSS and code injection risk"),
            (r'dangerouslySetInnerHTML', "medium", "dangerouslySetInnerHTML - ensure content is sanitized"),
            (r'<script>.*</script>', "high", "Inline script tag in template - potential XSS risk"),
        ]

        for pattern, severity, message in xss_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                vulnerabilities.append({
                    "severity": severity,
                    "type": "xss",
                    "line": line_num,
                    "message": message
                })
                issues.append({
                    "type": "xss",
                    "severity": severity,
                    "line": line_num,
                    "message": message
                })

        if vulnerabilities:
            suggestions.append("Sanitize user input and use safe DOM manipulation methods")

        return {
            "vulnerabilities": vulnerabilities,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_command_injection(self, code: str, language: str) -> Dict[str, Any]:
        """Check for command injection vulnerabilities"""
        issues = []
        suggestions = []
        vulnerabilities = []

        # Patterns that suggest command injection risk
        cmd_patterns = [
            (r'os\.system\s*\(', "high", "os.system() with potential user input - use subprocess with list args"),
            (r'subprocess\.call\s*\(.*shell\s*=\s*True', "high", "subprocess with shell=True - avoid or sanitize input"),
            (r'eval\s*\(', "high", "eval() usage - potential code injection"),
            (r'exec\s*\(', "high", "exec() usage - potential code injection"),
            (r'__import__\s*\(', "medium", "Dynamic import - ensure input is validated"),
            (r'compile\s*\(', "medium", "compile() usage - ensure input is trusted"),
        ]

        for pattern, severity, message in cmd_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                vulnerabilities.append({
                    "severity": severity,
                    "type": "command_injection",
                    "line": line_num,
                    "message": message
                })
                issues.append({
                    "type": "command_injection",
                    "severity": severity,
                    "line": line_num,
                    "message": message
                })

        if vulnerabilities:
            suggestions.append("Use subprocess with list arguments instead of shell=True")

        return {
            "vulnerabilities": vulnerabilities,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_hardcoded_secrets(self, code: str) -> Dict[str, Any]:
        """Check for hardcoded secrets"""
        issues = []
        suggestions = []
        vulnerabilities = []

        # Patterns for common secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']{3,}["\']', "high", "Hardcoded password detected"),
            (r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']', "high", "Hardcoded API key detected"),
            (r'secret[_-]?key\s*=\s*["\'][^"\']{10,}["\']', "high", "Hardcoded secret key detected"),
            (r'token\s*=\s*["\'][^"\']{10,}["\']', "high", "Hardcoded token detected"),
            (r'aws[_-]?access[_-]?key', "high", "Hardcoded AWS access key detected"),
            (r'private[_-]?key\s*=\s*["\']', "high", "Hardcoded private key detected"),
            (r'bearer\s+[a-zA-Z0-9\-._~+/]+=*', "medium", "Bearer token in code"),
        ]

        # Exclude common test/example patterns
        exclude_patterns = [
            r'password\s*=\s*["\'](?:password|test|demo|example|your_password_here)["\']',
            r'api[_-]?key\s*=\s*["\'](?:test|demo|example|your_api_key_here)["\']',
        ]

        for pattern, severity, message in secret_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                # Check if it's an excluded pattern
                is_excluded = False
                for exclude_pattern in exclude_patterns:
                    if re.search(exclude_pattern, match.group(0), re.IGNORECASE):
                        is_excluded = True
                        break

                if not is_excluded:
                    line_num = code[:match.start()].count('\n') + 1
                    vulnerabilities.append({
                        "severity": severity,
                        "type": "hardcoded_secret",
                        "line": line_num,
                        "message": message
                    })
                    issues.append({
                        "type": "hardcoded_secret",
                        "severity": severity,
                        "line": line_num,
                        "message": message
                    })

        if vulnerabilities:
            suggestions.append("Move secrets to environment variables or secure secret management")

        return {
            "vulnerabilities": vulnerabilities,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_insecure_functions(self, code: str, language: str) -> Dict[str, Any]:
        """Check for use of insecure functions"""
        issues = []
        suggestions = []
        vulnerabilities = []

        if language == "python":
            insecure_patterns = [
                (r'pickle\.loads?\s*\(', "high", "pickle.load() on untrusted data - use json instead"),
                (r'yaml\.load\s*\([^,)]*\)', "high", "yaml.load() without Loader - use yaml.safe_load()"),
                (r'input\s*\(', "low", "input() used - ensure validation if used in production"),
                (r'random\.random\s*\(', "low", "random.random() - use secrets module for cryptographic randomness"),
                (r'assert\s+', "low", "assert statement - can be disabled with -O flag"),
            ]

            for pattern, severity, message in insecure_patterns:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    vulnerabilities.append({
                        "severity": severity,
                        "type": "insecure_function",
                        "line": line_num,
                        "message": message
                    })
                    issues.append({
                        "type": "insecure_function",
                        "severity": severity,
                        "line": line_num,
                        "message": message
                    })

        return {
            "vulnerabilities": vulnerabilities,
            "issues": issues,
            "suggestions": suggestions
        }

    def _simulate_dependency_scan(self, code: str, language: str) -> Dict[str, Any]:
        """Simulate dependency vulnerability scanning"""
        issues = []
        suggestions = []
        vulnerabilities = []

        # Look for import statements and simulate finding vulnerabilities
        # In reality, this would check against a vulnerability database

        if language == "python":
            # Check for imports of packages with known issues
            risky_packages = {
                "urllib": ("low", "Consider using requests library for better security"),
                "telnetlib": ("medium", "Telnet is insecure - use SSH instead"),
                "ftplib": ("low", "FTP is insecure - use SFTP instead"),
            }

            for package, (severity, message) in risky_packages.items():
                pattern = rf'import\s+{package}|from\s+{package}\s+import'
                if re.search(pattern, code):
                    vulnerabilities.append({
                        "severity": severity,
                        "type": "insecure_dependency",
                        "message": f"{package}: {message}"
                    })
                    issues.append({
                        "type": "insecure_dependency",
                        "severity": severity,
                        "message": f"{package}: {message}"
                    })

        if vulnerabilities:
            suggestions.append("Review and update dependencies to secure alternatives")

        return {
            "vulnerabilities": vulnerabilities,
            "issues": issues,
            "suggestions": suggestions
        }

    def _categorize_vulnerabilities(self, result: Dict[str, Any], vulnerabilities: Dict[str, List]) -> None:
        """Categorize vulnerabilities by severity"""
        for vuln in result.get("vulnerabilities", []):
            severity = vuln.get("severity", "low")
            if severity == "high":
                vulnerabilities["high_risk"].append(vuln)
            elif severity == "medium":
                vulnerabilities["medium_risk"].append(vuln)
            else:
                vulnerabilities["low_risk"].append(vuln)

    def _calculate_score(self, high_risk: int, medium_risk: int, low_risk: int) -> Decimal:
        """
        Calculate security score

        Formula: score = 10 - (high_risk * 3) - (medium_risk * 1) - (low_risk * 0.5)
        """
        base_score = 10.0

        score = base_score
        score -= high_risk * 3
        score -= medium_risk * 1
        score -= low_risk * 0.5

        return self._clamp_score(score)
