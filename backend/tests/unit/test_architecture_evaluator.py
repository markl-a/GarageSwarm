"""Unit tests for ArchitectureEvaluator"""

import pytest
from decimal import Decimal

from src.evaluators.architecture import ArchitectureEvaluator
from src.evaluators.base import EvaluationResult


@pytest.fixture
def architecture_evaluator():
    """Create ArchitectureEvaluator instance"""
    return ArchitectureEvaluator()


@pytest.fixture
def good_code_sample():
    """Sample of well-architected Python code"""
    return """
import os
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class UserRepository:
    \"\"\"Repository for user data access\"\"\"

    def __init__(self, db_session):
        self.db_session = db_session

    def get_user(self, user_id: int):
        \"\"\"Get user by ID\"\"\"
        return self.db_session.query(User).filter(User.id == user_id).first()

    def create_user(self, username: str, email: str):
        \"\"\"Create new user\"\"\"
        user = User(username=username, email=email)
        self.db_session.add(user)
        return user
"""


@pytest.fixture
def bad_code_sample():
    """Sample of poorly architected Python code"""
    return """
from module import *
import sys, os, json, requests, datetime, collections

class GODClass:
    def __init__(self):
        global g_config
        self.config = g_config

    def DoEverything(self, param1, param2, param3, param4, param5, param6):
        if param1:
            if param2:
                if param3:
                    if param4:
                        if param5:
                            return self.process(param6)
        return None

    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
    def method13(self): pass
    def method14(self): pass
    def method15(self): pass
    def method16(self): pass
    def method17(self): pass
    def method18(self): pass
    def method19(self): pass
    def method20(self): pass
    def method21(self): pass
"""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluator_properties(architecture_evaluator):
    """Test evaluator properties"""
    assert architecture_evaluator.name == "architecture"
    assert "architecture" in architecture_evaluator.description.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_good_code(architecture_evaluator, good_code_sample):
    """Test evaluating well-architected code"""
    # Act
    result = await architecture_evaluator.evaluate(
        code=good_code_sample,
        context={"language": "python", "file_path": "src/repositories/user_repository.py"}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score >= Decimal("7.0")
    assert result.details["import_violations"] == 0
    assert result.details["naming_violations"] == 0
    assert len(result.issues) == 0 or all(issue["severity"] != "critical" for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_bad_code(architecture_evaluator, bad_code_sample):
    """Test evaluating poorly architected code"""
    # Act
    result = await architecture_evaluator.evaluate(
        code=bad_code_sample,
        context={"language": "python", "file_path": "src/god_class.py"}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score < Decimal("7.0")
    assert result.details["import_violations"] > 0  # Star import
    assert result.details["anti_patterns"] > 0  # God class, deep nesting, too many params
    assert len(result.issues) > 0
    assert any(issue["severity"] == "critical" for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detect_star_imports(architecture_evaluator):
    """Test detection of star imports"""
    code = """
from os import *
from sys import path
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert
    assert result.details["import_violations"] >= 1
    assert any("star import" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detect_naming_violations(architecture_evaluator):
    """Test detection of naming convention violations"""
    code = """
class snake_case_class:
    pass

def PascalCaseFunction():
    pass

MY_constant = 42
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert
    assert result.details["naming_violations"] > 0
    assert any("PascalCase" in issue["message"] or "snake_case" in issue["message"] for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detect_god_class(architecture_evaluator):
    """Test detection of god classes"""
    # Create a class with many methods
    methods = "\n    ".join([f"def method{i}(self): pass" for i in range(25)])
    code = f"""
class GodClass:
    {methods}
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert
    assert result.details["anti_patterns"] > 0
    assert len(result.details["god_classes"]) > 0
    assert "GodClass" in result.details["god_classes"]
    assert any("god class" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detect_long_method(architecture_evaluator):
    """Test detection of long methods"""
    # Create a function with many lines
    lines = "\n    ".join([f"var{i} = {i}" for i in range(60)])
    code = f"""
def very_long_function():
    {lines}
    return True
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert
    assert result.details["anti_patterns"] > 0
    assert any("long method" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detect_too_many_parameters(architecture_evaluator):
    """Test detection of functions with too many parameters"""
    code = """
def function_with_many_params(param1, param2, param3, param4, param5, param6, param7):
    return param1 + param2 + param3 + param4 + param5 + param6 + param7
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert
    assert result.details["anti_patterns"] > 0
    assert any("too many parameters" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detect_deep_nesting(architecture_evaluator):
    """Test detection of deep nesting"""
    code = """
def deeply_nested():
    if True:
        if True:
            if True:
                if True:
                    if True:
                        return "too deep"
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert
    assert result.details["anti_patterns"] > 0
    assert any("deep nesting" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_folder_structure_test_file(architecture_evaluator):
    """Test folder structure validation for test files"""
    code = "def test_something(): pass"

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={
            "language": "python",
            "file_path": "src/test_module.py"  # Test file not in tests directory
        }
    )

    # Assert
    assert result.details["structure_violations"] > 0
    assert any("test" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_separation_of_concerns(architecture_evaluator):
    """Test separation of concerns detection"""
    code = """
from fastapi import APIRouter

router = APIRouter()

@router.post("/users")
async def create_user(username: str):
    # Direct database access in route handler
    session = get_session()
    user = User(username=username)
    session.add(user)
    session.commit()
    return user
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert - this code mixes routing and database concerns
    # The evaluator should detect multiple concerns
    assert "separation_violations" in result.details


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_non_python_code(architecture_evaluator):
    """Test evaluation of non-Python code"""
    javascript_code = """
function hello() {
    console.log("Hello, world!");
}
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=javascript_code,
        context={"language": "javascript"}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score >= Decimal("0.0")
    assert result.score <= Decimal("10.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_large_file(architecture_evaluator):
    """Test evaluation of large file"""
    # Create a very large file (non-Python to trigger basic architecture check)
    large_code = "\n".join([f"function function_{i}() {{}}" for i in range(600)])

    # Act
    result = await architecture_evaluator.evaluate(
        code=large_code,
        context={"language": "javascript"}
    )

    # Assert
    assert any("large file" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_clamping(architecture_evaluator):
    """Test that scores are properly clamped to 0-10 range"""
    # Create code with many violations
    code = """
from module import *

class bad_class_name:
    def BadMethod(self, p1, p2, p3, p4, p5, p6, p7):
        global g_var
        if True:
            if True:
                if True:
                    if True:
                        if True:
                            return None
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert
    assert result.score >= Decimal("0.0")
    assert result.score <= Decimal("10.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_perfect_code_bonus(architecture_evaluator):
    """Test that perfect code gets bonus points"""
    code = """
from typing import Optional

class UserService:
    \"\"\"Service for user operations\"\"\"

    def __init__(self, repository):
        self.repository = repository

    def get_user(self, user_id: int) -> Optional[dict]:
        \"\"\"Get user by ID\"\"\"
        return self.repository.find_by_id(user_id)
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python", "file_path": "src/services/user_service.py"}
    )

    # Assert
    assert result.score >= Decimal("8.0")
    assert result.details["import_violations"] == 0
    assert result.details["naming_violations"] == 0
    assert result.details["anti_patterns"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_relative_imports_when_allowed(architecture_evaluator):
    """Test relative imports are allowed when configured"""
    code = """
from ..models import User
from .utils import helper_function
"""

    # Configure to allow relative imports
    architecture_evaluator.update_config({"allow_relative_imports": True})

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert - relative imports should not cause violations
    import_violations = sum(1 for issue in result.issues if "relative import" in issue["message"].lower())
    assert import_violations == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_relative_imports_when_disallowed(architecture_evaluator):
    """Test relative imports are flagged when configured"""
    code = """
from ..models import User
from .utils import helper_function
"""

    # Configure to disallow relative imports
    architecture_evaluator.update_config({"allow_relative_imports": False})

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert - relative imports should cause violations
    import_violations = sum(1 for issue in result.issues if "relative import" in issue["message"].lower())
    assert import_violations > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggestions_provided(architecture_evaluator, bad_code_sample):
    """Test that helpful suggestions are provided"""
    # Act
    result = await architecture_evaluator.evaluate(
        code=bad_code_sample,
        context={"language": "python"}
    )

    # Assert
    assert len(result.suggestions) > 0
    assert all(isinstance(s, str) for s in result.suggestions)
    assert any("refactor" in s.lower() or "split" in s.lower() or "reduce" in s.lower() for s in result.suggestions)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_code(architecture_evaluator):
    """Test evaluation of empty code"""
    # Act
    result = await architecture_evaluator.evaluate(
        code="",
        context={"language": "python"}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score >= Decimal("0.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_syntax_error_handling(architecture_evaluator):
    """Test handling of code with syntax errors"""
    code = """
def broken_function(
    # Missing closing parenthesis
"""

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python"}
    )

    # Assert - should not crash, even with syntax errors
    assert isinstance(result, EvaluationResult)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_metadata_in_result(architecture_evaluator):
    """Test that metadata is included in result"""
    code = "def test(): pass"

    # Act
    result = await architecture_evaluator.evaluate(
        code=code,
        context={"language": "python", "file_path": "test.py"}
    )

    # Assert
    assert "language" in result.metadata
    assert result.metadata["language"] == "python"
    assert result.metadata["evaluator"] == "architecture"
    assert "file_path" in result.metadata


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pascal_case_validation(architecture_evaluator):
    """Test PascalCase validation"""
    assert architecture_evaluator._is_pascal_case("UserService")
    assert architecture_evaluator._is_pascal_case("HTTPClient")
    assert not architecture_evaluator._is_pascal_case("user_service")
    assert not architecture_evaluator._is_pascal_case("User_Service")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_snake_case_validation(architecture_evaluator):
    """Test snake_case validation"""
    assert architecture_evaluator._is_snake_case("user_service")
    assert architecture_evaluator._is_snake_case("get_user_by_id")
    assert architecture_evaluator._is_snake_case("__init__")
    assert not architecture_evaluator._is_snake_case("UserService")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upper_case_validation(architecture_evaluator):
    """Test UPPER_CASE validation"""
    assert architecture_evaluator._is_upper_case("MAX_CONNECTIONS")
    assert architecture_evaluator._is_upper_case("API_KEY")
    assert not architecture_evaluator._is_upper_case("max_connections")
    assert not architecture_evaluator._is_upper_case("MaxConnections")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_module_name(architecture_evaluator):
    """Test module name extraction from file path"""
    assert "src.api.v1.tasks" in architecture_evaluator._extract_module_name("backend/src/api/v1/tasks.py")
    assert "src.models.user" in architecture_evaluator._extract_module_name("src/models/user.py")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_nesting_depth_calculation(architecture_evaluator):
    """Test nesting depth calculation"""
    code = """
def nested():
    if True:
        if True:
            if True:
                pass
"""
    tree = compile(code, "<string>", "exec", flags=__import__("ast").PyCF_ONLY_AST)
    func_node = tree.body[0]

    depth = architecture_evaluator._calculate_nesting_depth(func_node)
    assert depth >= 3
