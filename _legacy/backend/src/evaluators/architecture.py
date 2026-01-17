"""
Architecture Alignment Evaluator

Evaluates code alignment with project architecture patterns:
- Import structure analysis
- Naming conventions
- Folder structure compliance
- Separation of concerns
- Anti-pattern detection
"""

import ast
import re
from typing import Any, Dict, List, Set, Tuple
from decimal import Decimal
from collections import defaultdict
import structlog

from .base import BaseEvaluator, EvaluationResult

logger = structlog.get_logger()


class ArchitectureEvaluator(BaseEvaluator):
    """
    Evaluates code architecture alignment:
    - Import structure and dependency analysis
    - Naming conventions (PEP 8 compliance)
    - Folder structure compliance
    - Separation of concerns
    - Anti-pattern detection (circular deps, god classes, etc.)
    """

    @property
    def name(self) -> str:
        return "architecture"

    @property
    def description(self) -> str:
        return "Evaluates code architecture alignment and design patterns"

    async def evaluate(self, code: str, context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate architecture alignment

        Scoring formula:
        base_score = 10.0
        score = base_score - (critical_violations * 2) - (major_violations * 1) - (minor_violations * 0.3)

        Args:
            code: Source code to evaluate
            context: Context including:
                - language: Programming language
                - file_path: File path (for folder structure analysis)
                - project_structure: Expected project structure
                - architecture_patterns: Expected patterns

        Returns:
            EvaluationResult with architecture score and details
        """
        language = context.get("language", "python").lower()
        file_path = context.get("file_path", "")

        # Initialize results
        issues = []
        suggestions = []
        details = {
            "import_violations": 0,
            "naming_violations": 0,
            "structure_violations": 0,
            "separation_violations": 0,
            "anti_patterns": 0,
            "total_imports": 0,
            "circular_dependencies": [],
            "god_classes": [],
            "complexity_score": 10.0
        }

        # Only evaluate Python code for now
        if language == "python":
            # Analyze imports
            import_result = self._analyze_imports(code, file_path, context)
            details["import_violations"] = import_result["violation_count"]
            details["total_imports"] = import_result["total_imports"]
            details["circular_dependencies"] = import_result["circular_dependencies"]
            issues.extend(import_result["issues"])
            suggestions.extend(import_result["suggestions"])

            # Check naming conventions
            naming_result = self._check_naming_conventions(code)
            details["naming_violations"] = naming_result["violation_count"]
            issues.extend(naming_result["issues"])
            suggestions.extend(naming_result["suggestions"])

            # Check folder structure compliance
            structure_result = self._check_folder_structure(file_path, context)
            details["structure_violations"] = structure_result["violation_count"]
            issues.extend(structure_result["issues"])
            suggestions.extend(structure_result["suggestions"])

            # Check separation of concerns
            separation_result = self._check_separation_of_concerns(code)
            details["separation_violations"] = separation_result["violation_count"]
            issues.extend(separation_result["issues"])
            suggestions.extend(separation_result["suggestions"])

            # Detect anti-patterns
            anti_pattern_result = self._detect_anti_patterns(code)
            details["anti_patterns"] = anti_pattern_result["pattern_count"]
            details["god_classes"] = anti_pattern_result["god_classes"]
            issues.extend(anti_pattern_result["issues"])
            suggestions.extend(anti_pattern_result["suggestions"])
        else:
            # For non-Python code, do basic architecture checks
            basic_result = self._basic_architecture_check(code, language, file_path)
            details.update(basic_result["details"])
            issues.extend(basic_result["issues"])
            suggestions.extend(basic_result["suggestions"])

        # Calculate score
        score = self._calculate_score(details, issues)

        return EvaluationResult(
            score=score,
            details=details,
            suggestions=suggestions,
            issues=issues,
            metadata={
                "language": language,
                "file_path": file_path,
                "evaluator": self.name
            }
        )

    def _analyze_imports(self, code: str, file_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze import structure

        Checks for:
        - Relative vs absolute imports
        - Unused imports
        - Star imports (from x import *)
        - Circular dependencies (basic detection)
        """
        issues = []
        suggestions = []
        violation_count = 0
        circular_dependencies = []
        total_imports = 0

        try:
            tree = ast.parse(code)
            imports = []
            star_imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    total_imports += len(node.names)
                    for alias in node.names:
                        imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    total_imports += 1
                    module = node.module or ""

                    # Check for star imports
                    for alias in node.names:
                        if alias.name == "*":
                            star_imports.append(module)
                            violation_count += 1
                            issues.append({
                                "type": "import",
                                "severity": "medium",
                                "line": node.lineno,
                                "message": f"Star import from '{module}' - avoid wildcard imports"
                            })

                    # Check for relative imports
                    if node.level > 0:
                        # Relative import - check if it's appropriate
                        if not self.config.get("allow_relative_imports", True):
                            violation_count += 1
                            issues.append({
                                "type": "import",
                                "severity": "low",
                                "line": node.lineno,
                                "message": f"Relative import detected - consider using absolute imports"
                            })

            # Suggest organizing imports
            if total_imports > 10:
                suggestions.append("Consider organizing imports into groups: stdlib, third-party, local")

            # Check for potential circular dependencies (basic check)
            if file_path:
                circular_deps = self._detect_circular_imports(imports, file_path, context)
                if circular_deps:
                    circular_dependencies.extend(circular_deps)
                    violation_count += len(circular_deps)
                    for dep in circular_deps:
                        issues.append({
                            "type": "import",
                            "severity": "critical",
                            "message": f"Potential circular dependency: {dep}"
                        })
                    suggestions.append("Refactor to eliminate circular dependencies")

        except Exception as e:
            logger.warning(f"Error analyzing imports: {e}")

        return {
            "violation_count": violation_count,
            "total_imports": total_imports,
            "circular_dependencies": circular_dependencies,
            "issues": issues,
            "suggestions": suggestions
        }

    def _detect_circular_imports(self, imports: List[str], file_path: str, context: Dict[str, Any]) -> List[str]:
        """
        Detect potential circular dependencies

        This is a basic check that looks for imports that might create cycles
        """
        circular = []

        # Get project structure from context
        project_structure = context.get("project_structure", {})
        if not project_structure:
            return circular

        # Extract module name from file path
        current_module = self._extract_module_name(file_path)
        if not current_module:
            return circular

        # Check if any imports might import back to this module
        for imp in imports:
            # Simple heuristic: if import starts with same root package
            if current_module and imp.startswith(current_module.split(".")[0]):
                # Could be a circular dependency
                circular.append(f"{current_module} <-> {imp}")

        return circular

    def _extract_module_name(self, file_path: str) -> str:
        """Extract module name from file path"""
        if not file_path:
            return ""

        # Convert file path to module name
        # e.g., "backend/src/api/v1/tasks.py" -> "src.api.v1.tasks"
        parts = file_path.replace("\\", "/").split("/")

        # Find 'src' or similar root
        try:
            if "src" in parts:
                idx = parts.index("src")
                module_parts = parts[idx:]
                # Remove .py extension
                if module_parts[-1].endswith(".py"):
                    module_parts[-1] = module_parts[-1][:-3]
                return ".".join(module_parts)
        except (ValueError, IndexError):
            pass

        return ""

    def _check_naming_conventions(self, code: str) -> Dict[str, Any]:
        """
        Check naming conventions (PEP 8 compliance)

        Checks:
        - Class names (PascalCase)
        - Function names (snake_case)
        - Constant names (UPPER_CASE)
        - Private members (_prefix)
        """
        issues = []
        suggestions = []
        violation_count = 0

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Check class names
                if isinstance(node, ast.ClassDef):
                    if not self._is_pascal_case(node.name):
                        violation_count += 1
                        issues.append({
                            "type": "naming",
                            "severity": "medium",
                            "line": node.lineno,
                            "message": f"Class '{node.name}' should use PascalCase"
                        })

                # Check function names
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not self._is_snake_case(node.name) and not node.name.startswith("_"):
                        violation_count += 1
                        issues.append({
                            "type": "naming",
                            "severity": "low",
                            "line": node.lineno,
                            "message": f"Function '{node.name}' should use snake_case"
                        })

                # Check constant names (module-level assignments)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            # If all uppercase with underscores, it's likely a constant
                            if target.id.isupper() or "_" in target.id:
                                if not self._is_upper_case(target.id):
                                    # This might be intended as a constant but not properly named
                                    if target.id[0].isupper():
                                        violation_count += 1
                                        issues.append({
                                            "type": "naming",
                                            "severity": "low",
                                            "line": node.lineno,
                                            "message": f"Constant '{target.id}' should be UPPER_CASE"
                                        })

            if violation_count > 0:
                suggestions.append("Follow PEP 8 naming conventions for better code readability")

        except Exception as e:
            logger.warning(f"Error checking naming conventions: {e}")

        return {
            "violation_count": violation_count,
            "issues": issues,
            "suggestions": suggestions
        }

    def _is_pascal_case(self, name: str) -> bool:
        """Check if name is PascalCase"""
        if not name:
            return False
        # PascalCase: starts with uppercase, no underscores (except for private)
        if name.startswith("_"):
            name = name[1:]
        return name[0].isupper() and "_" not in name

    def _is_snake_case(self, name: str) -> bool:
        """Check if name is snake_case"""
        if not name:
            return False
        # snake_case: all lowercase with underscores
        # Also allow dunder methods like __init__
        if name.startswith("__") and name.endswith("__"):
            return True
        return name.islower() or "_" in name

    def _is_upper_case(self, name: str) -> bool:
        """Check if name is UPPER_CASE"""
        if not name:
            return False
        # UPPER_CASE: all uppercase with underscores
        return name.isupper() or (name.upper() == name and "_" in name)

    def _check_folder_structure(self, file_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check folder structure compliance

        Validates:
        - File is in correct directory based on type
        - Follows project structure conventions
        """
        issues = []
        suggestions = []
        violation_count = 0

        if not file_path:
            return {
                "violation_count": 0,
                "issues": issues,
                "suggestions": suggestions
            }

        # Get expected structure from context
        expected_structure = context.get("project_structure", {})

        # Normalize path
        normalized_path = file_path.replace("\\", "/").lower()

        # Check common patterns
        if "test" in normalized_path:
            if not normalized_path.startswith("test") and "tests" not in normalized_path:
                violation_count += 1
                issues.append({
                    "type": "structure",
                    "severity": "medium",
                    "message": "Test files should be in 'tests' directory"
                })

        # Check for proper src structure
        if "/src/" in normalized_path:
            # Good - using src directory
            pass
        elif normalized_path.endswith(".py") and "test" not in normalized_path:
            # Check if it should be in src
            if expected_structure.get("use_src_directory", True):
                suggestions.append("Consider organizing source files under 'src' directory")

        return {
            "violation_count": violation_count,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_separation_of_concerns(self, code: str) -> Dict[str, Any]:
        """
        Check separation of concerns

        Looks for:
        - Mixed responsibilities in single module
        - Database logic in presentation layer
        - Business logic in controllers
        """
        issues = []
        suggestions = []
        violation_count = 0

        try:
            tree = ast.parse(code)

            # Track different concerns found
            concerns = {
                "database": False,
                "api": False,
                "business_logic": False,
                "presentation": False
            }

            for node in ast.walk(tree):
                # Check for database operations
                if isinstance(node, ast.Name):
                    if any(keyword in node.id.lower() for keyword in ["session", "query", "commit", "rollback"]):
                        concerns["database"] = True

                # Check for API/routing decorators
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ["get", "post", "put", "delete", "route"]:
                            concerns["api"] = True

                # Check for business logic indicators
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Complex functions with business logic
                    if len(list(ast.walk(node))) > 50:
                        concerns["business_logic"] = True

            # Check if multiple concerns are mixed
            concern_count = sum(concerns.values())
            if concern_count > 2:
                violation_count += 1
                issues.append({
                    "type": "separation",
                    "severity": "medium",
                    "message": "Multiple concerns detected in single module - consider separating responsibilities"
                })
                suggestions.append("Split code into separate layers (e.g., routes, services, repositories)")

        except Exception as e:
            logger.warning(f"Error checking separation of concerns: {e}")

        return {
            "violation_count": violation_count,
            "issues": issues,
            "suggestions": suggestions
        }

    def _detect_anti_patterns(self, code: str) -> Dict[str, Any]:
        """
        Detect common anti-patterns

        Detects:
        - God classes (too many methods/attributes)
        - Long methods (>50 lines)
        - Deep nesting (>4 levels)
        - Too many parameters (>5)
        """
        issues = []
        suggestions = []
        pattern_count = 0
        god_classes = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Check for god classes
                if isinstance(node, ast.ClassDef):
                    method_count = sum(1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
                    if method_count > 20:
                        pattern_count += 1
                        god_classes.append(node.name)
                        issues.append({
                            "type": "anti_pattern",
                            "severity": "critical",
                            "line": node.lineno,
                            "message": f"God class detected: '{node.name}' has {method_count} methods"
                        })
                        suggestions.append(f"Split '{node.name}' into smaller, focused classes")

                # Check for long methods
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Calculate function length
                    if hasattr(node, "end_lineno") and node.end_lineno:
                        func_length = node.end_lineno - node.lineno
                        if func_length > 50:
                            pattern_count += 1
                            issues.append({
                                "type": "anti_pattern",
                                "severity": "medium",
                                "line": node.lineno,
                                "message": f"Long method detected: '{node.name}' ({func_length} lines)"
                            })
                            suggestions.append(f"Refactor '{node.name}' into smaller functions")

                    # Check for too many parameters
                    param_count = len(node.args.args)
                    if param_count > 5:
                        pattern_count += 1
                        issues.append({
                            "type": "anti_pattern",
                            "severity": "medium",
                            "line": node.lineno,
                            "message": f"Too many parameters in '{node.name}': {param_count} (max recommended: 5)"
                        })
                        suggestions.append(f"Consider using a parameter object for '{node.name}'")

                    # Check for deep nesting
                    max_depth = self._calculate_nesting_depth(node)
                    if max_depth > 4:
                        pattern_count += 1
                        issues.append({
                            "type": "anti_pattern",
                            "severity": "medium",
                            "line": node.lineno,
                            "message": f"Deep nesting in '{node.name}': {max_depth} levels"
                        })
                        suggestions.append(f"Reduce nesting in '{node.name}' using early returns or guard clauses")

        except Exception as e:
            logger.warning(f"Error detecting anti-patterns: {e}")

        return {
            "pattern_count": pattern_count,
            "god_classes": god_classes,
            "issues": issues,
            "suggestions": suggestions
        }

    def _calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth in a function"""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _basic_architecture_check(self, code: str, language: str, file_path: str) -> Dict[str, Any]:
        """Basic architecture checks for non-Python code"""
        issues = []
        suggestions = []

        details = {
            "import_violations": 0,
            "naming_violations": 0,
            "structure_violations": 0,
            "separation_violations": 0,
            "anti_patterns": 0
        }

        # Basic checks for any language
        lines = code.split("\n")
        if len(lines) > 500:
            issues.append({
                "type": "anti_pattern",
                "severity": "medium",
                "message": "Large file detected (>500 lines) - consider splitting"
            })
            suggestions.append("Split large files into smaller, focused modules")

        return {
            "details": details,
            "issues": issues,
            "suggestions": suggestions
        }

    def _calculate_score(self, details: Dict[str, Any], issues: List[Dict[str, Any]]) -> Decimal:
        """
        Calculate final score based on violations

        score = 10 - (critical * 2) - (high * 1.5) - (medium * 1) - (low * 0.3)
        """
        base_score = 10.0

        # Count issues by severity
        critical_count = sum(1 for issue in issues if issue.get("severity") == "critical")
        high_count = sum(1 for issue in issues if issue.get("severity") == "high")
        medium_count = sum(1 for issue in issues if issue.get("severity") == "medium")
        low_count = sum(1 for issue in issues if issue.get("severity") == "low")

        # Apply penalties
        score = base_score
        score -= critical_count * 2.0
        score -= high_count * 1.5
        score -= medium_count * 1.0
        score -= low_count * 0.3

        # Bonus for good practices
        if details.get("total_imports", 0) > 0 and details.get("import_violations", 0) == 0:
            score += 0.5

        if details.get("anti_patterns", 0) == 0:
            score += 0.5

        return self._clamp_score(score)
