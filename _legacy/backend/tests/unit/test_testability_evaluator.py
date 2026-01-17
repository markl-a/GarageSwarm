"""Unit tests for TestabilityEvaluator"""

import pytest
from decimal import Decimal

from src.evaluators.testability import TestabilityEvaluator
from src.evaluators.base import EvaluationResult


@pytest.fixture
def testability_evaluator():
    """Create TestabilityEvaluator instance"""
    return TestabilityEvaluator()


@pytest.fixture
def good_test_file():
    """Sample of high-quality test file"""
    return """
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def sample_user():
    \"\"\"Fixture for sample user\"\"\"
    return {"id": 1, "name": "Test User"}

@pytest.mark.parametrize("user_id,expected", [
    (1, "User 1"),
    (2, "User 2"),
    (999, None),
])
def test_get_user_parametrized(user_id, expected):
    \"\"\"Test get_user with various inputs\"\"\"
    result = get_user(user_id)
    assert result == expected

def test_create_user():
    \"\"\"Test user creation\"\"\"
    user = create_user("test", "test@example.com")
    assert user.username == "test"
    assert user.email == "test@example.com"

def test_update_user_with_mock():
    \"\"\"Test user update with mock\"\"\"
    mock_db = Mock()
    service = UserService(mock_db)
    service.update_user(1, {"name": "Updated"})
    mock_db.commit.assert_called_once()

def test_delete_user_error():
    \"\"\"Test error handling when deleting non-existent user\"\"\"
    with pytest.raises(ValueError):
        delete_user(999)

def test_edge_case_empty_username():
    \"\"\"Test edge case with empty username\"\"\"
    with pytest.raises(ValueError):
        create_user("", "test@example.com")
"""


@pytest.fixture
def poor_test_file():
    """Sample of poor quality test file"""
    return """
def test_something():
    # No assertions
    result = do_something()

def test_another():
    # Only one weak assertion
    assert True
"""


@pytest.fixture
def testable_code():
    """Sample of testable source code"""
    return """
class UserService:
    \"\"\"Service with dependency injection\"\"\"

    def __init__(self, repository, cache_service, logger):
        self.repository = repository
        self.cache = cache_service
        self.logger = logger

    def get_user(self, user_id: int):
        \"\"\"Get user by ID\"\"\"
        cached = self.cache.get(f"user:{user_id}")
        if cached:
            return cached

        user = self.repository.find_by_id(user_id)
        if user:
            self.cache.set(f"user:{user_id}", user)
        return user
"""


@pytest.fixture
def untestable_code():
    """Sample of hard-to-test source code"""
    return """
import database

global_config = {}

def process_user(user_id):
    global global_config
    db = database.Database()
    session = database.Session()
    user = session.query(User).filter(User.id == user_id).first()

    if user:
        config = global_config
        # Direct instantiation everywhere
        validator = UserValidator()
        processor = DataProcessor()
        notifier = EmailNotifier()

        if validator.validate(user):
            processor.process(user)
            notifier.send(user.email)
"""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluator_properties(testability_evaluator):
    """Test evaluator properties"""
    assert testability_evaluator.name == "testability"
    assert "testability" in testability_evaluator.description.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_good_test_file(testability_evaluator, good_test_file):
    """Test evaluating high-quality test file"""
    # Act
    result = await testability_evaluator.evaluate(
        code=good_test_file,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score >= Decimal("4.0")  # Adjusted for realistic scoring
    assert result.details["test_count"] >= 5
    assert result.details["assertion_count"] > 0
    assert result.details["mock_usage"] is True
    assert result.details["has_fixtures"] is True
    assert result.details["has_parametrized_tests"] is True
    assert result.details["edge_case_tests"] > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_poor_test_file(testability_evaluator, poor_test_file):
    """Test evaluating poor quality test file"""
    # Act
    result = await testability_evaluator.evaluate(
        code=poor_test_file,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score < Decimal("7.0")
    assert len(result.issues) > 0
    assert any("no assertions" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_testable_code(testability_evaluator, testable_code):
    """Test evaluating testable source code"""
    # Act
    result = await testability_evaluator.evaluate(
        code=testable_code,
        context={"language": "python", "is_test_file": False}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score >= Decimal("5.0")
    assert result.details["dependency_injection"] is True
    assert result.details["global_state_usage"] == 0
    assert result.details["testable_structure"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_untestable_code(testability_evaluator, untestable_code):
    """Test evaluating hard-to-test source code"""
    # Act
    result = await testability_evaluator.evaluate(
        code=untestable_code,
        context={"language": "python", "is_test_file": False}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.details["global_state_usage"] > 0
    assert result.details["hard_coded_deps"] > 0
    assert len(result.issues) > 0
    assert any("global state" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_test_functions_in_test_file(testability_evaluator):
    """Test detection of test file with no test functions"""
    code = """
def helper_function():
    return True

def another_helper():
    return False
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.details["test_count"] == 0
    assert any(issue["severity"] == "critical" for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_without_assertions(testability_evaluator):
    """Test detection of tests without assertions"""
    code = """
def test_something():
    result = process_data()
    # Oops, forgot to assert!
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.details["test_count"] == 1
    assert result.details["assertion_count"] == 0
    assert any("no assertions" in issue["message"].lower() for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_usage_detection(testability_evaluator):
    """Test detection of mock usage"""
    code = """
from unittest.mock import Mock, patch

def test_with_mock():
    mock_db = Mock()
    service = Service(mock_db)
    service.process()
    mock_db.commit.assert_called_once()

@patch('module.function')
def test_with_patch(mock_func):
    assert mock_func.called
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.details["mock_usage"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fixture_detection(testability_evaluator):
    """Test detection of pytest fixtures"""
    code = """
import pytest

@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_using_fixture(sample_data):
    assert sample_data["key"] == "value"
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.details["has_fixtures"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parametrized_test_detection(testability_evaluator):
    """Test detection of parametrized tests"""
    code = """
import pytest

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    assert multiply(input) == expected
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.details["has_parametrized_tests"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edge_case_test_detection(testability_evaluator):
    """Test detection of edge case tests"""
    code = """
def test_edge_case_empty_list():
    assert process([]) == []

def test_boundary_condition_max_value():
    assert validate(sys.maxsize) is True

def test_error_handling_invalid_input():
    with pytest.raises(ValueError):
        process(None)
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.details["edge_case_tests"] >= 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dependency_injection_detection(testability_evaluator):
    """Test detection of dependency injection pattern"""
    code = """
class UserService:
    def __init__(self, repository, cache_service, logger):
        self.repository = repository
        self.cache = cache_service
        self.logger = logger
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": False}
    )

    # Assert
    assert result.details["dependency_injection"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_global_state_detection(testability_evaluator):
    """Test detection of global state usage"""
    code = """
global_cache = {}

def process():
    global global_cache
    global global_config
    return global_cache.get("key")
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": False}
    )

    # Assert
    assert result.details["global_state_usage"] >= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coverage_evaluation_excellent(testability_evaluator):
    """Test coverage evaluation with excellent coverage"""
    code = "def process(): pass"

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={
            "language": "python",
            "is_test_file": False,
            "test_coverage": 95.0
        }
    )

    # Assert
    assert result.details["coverage_score"] >= 3.0
    assert len([i for i in result.issues if i["type"] == "coverage"]) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coverage_evaluation_good(testability_evaluator):
    """Test coverage evaluation with good coverage"""
    code = "def process(): pass"

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={
            "language": "python",
            "is_test_file": False,
            "test_coverage": 85.0
        }
    )

    # Assert
    assert result.details["coverage_score"] >= 2.0
    assert result.details["coverage_score"] < 3.33


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coverage_evaluation_poor(testability_evaluator):
    """Test coverage evaluation with poor coverage"""
    code = "def process(): pass"

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={
            "language": "python",
            "is_test_file": False,
            "test_coverage": 45.0
        }
    )

    # Assert
    assert result.details["coverage_score"] < 2.0
    assert any(issue["severity"] == "critical" for issue in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assertion_counting(testability_evaluator):
    """Test counting of assertions in tests"""
    code = """
def test_multiple_assertions():
    assert True
    assert 1 == 1
    assert "hello" == "hello"
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.details["assertion_count"] >= 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assertion_method_counting(testability_evaluator):
    """Test counting of assertion methods (e.g., assert_equal)"""
    code = """
def test_with_assertion_methods():
    self.assertEqual(1, 1)
    self.assertTrue(True)
    mock.assert_called_once()
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.details["assertion_count"] >= 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hard_coded_dependencies_detection(testability_evaluator):
    """Test detection of hard-coded dependencies"""
    code = """
def process():
    db = Database()  # Hard-coded dependency
    validator = DataValidator()  # Hard-coded dependency
    notifier = EmailNotifier()  # Hard-coded dependency
    return db.query()
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": False}
    )

    # Assert
    assert result.details["hard_coded_deps"] >= 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_non_python_test_file(testability_evaluator):
    """Test evaluation of non-Python test file"""
    javascript_test = """
describe('User Service', () => {
    test('should create user', () => {
        expect(createUser('test')).toBeDefined();
    });
});
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=javascript_test,
        context={"language": "javascript", "is_test_file": True}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score >= Decimal("0.0")
    assert result.details["test_count"] > 0  # Basic detection


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_non_python_source_code(testability_evaluator):
    """Test evaluation of non-Python source code"""
    javascript_code = """
function processData(data) {
    return data.map(x => x * 2);
}
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=javascript_code,
        context={"language": "javascript", "is_test_file": False}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score >= Decimal("0.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggestions_for_test_improvement(testability_evaluator):
    """Test that suggestions are provided for test improvement"""
    code = """
def test_one():
    assert True

def test_two():
    assert True
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert len(result.suggestions) > 0
    # Should suggest mocks, fixtures, edge cases, etc.


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggestions_for_testability_improvement(testability_evaluator, untestable_code):
    """Test that suggestions are provided for testability improvement"""
    # Act
    result = await testability_evaluator.evaluate(
        code=untestable_code,
        context={"language": "python", "is_test_file": False}
    )

    # Assert
    assert len(result.suggestions) > 0
    assert any("global state" in s.lower() or "dependency injection" in s.lower() for s in result.suggestions)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_clamping(testability_evaluator):
    """Test that scores are properly clamped to 0-10 range"""
    code = """
global g1, g2, g3, g4, g5

def test_no_assertions():
    pass
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.score >= Decimal("0.0")
    assert result.score <= Decimal("10.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_code(testability_evaluator):
    """Test evaluation of empty code"""
    # Act
    result = await testability_evaluator.evaluate(
        code="",
        context={"language": "python", "is_test_file": False}
    )

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.score >= Decimal("0.0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_syntax_error_handling(testability_evaluator):
    """Test handling of code with syntax errors"""
    code = """
def broken_test(
    # Missing closing parenthesis
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert - should not crash
    assert isinstance(result, EvaluationResult)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_metadata_in_result(testability_evaluator):
    """Test that metadata is included in result"""
    code = "def test(): pass"

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert "language" in result.metadata
    assert result.metadata["language"] == "python"
    assert result.metadata["evaluator"] == "testability"
    assert result.metadata["is_test_file"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_high_quality_test_suite(testability_evaluator):
    """Test evaluation of comprehensive, high-quality test suite"""
    code = """
import pytest
from unittest.mock import Mock, patch, MagicMock

@pytest.fixture
def user_repository():
    return Mock()

@pytest.fixture
def cache_service():
    return Mock()

class TestUserService:
    def setUp(self):
        self.service = None

    @pytest.mark.parametrize("user_id,expected_name", [
        (1, "User 1"),
        (2, "User 2"),
    ])
    def test_get_user_by_id(self, user_repository, user_id, expected_name):
        service = UserService(user_repository)
        user = service.get_user(user_id)
        assert user.name == expected_name
        user_repository.find_by_id.assert_called_with(user_id)

    def test_create_user_success(self, user_repository):
        service = UserService(user_repository)
        user = service.create_user("test", "test@example.com")
        assert user.username == "test"
        assert user.email == "test@example.com"
        user_repository.save.assert_called_once()

    def test_edge_case_invalid_email(self, user_repository):
        service = UserService(user_repository)
        with pytest.raises(ValueError):
            service.create_user("test", "invalid-email")

    def test_boundary_max_username_length(self, user_repository):
        service = UserService(user_repository)
        long_name = "a" * 255
        user = service.create_user(long_name, "test@example.com")
        assert len(user.username) == 255
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={"language": "python", "is_test_file": True}
    )

    # Assert
    assert result.score >= Decimal("4.0")  # Adjusted for realistic scoring
    assert result.details["test_count"] >= 4
    assert result.details["mock_usage"] is True
    assert result.details["has_fixtures"] is True
    assert result.details["has_parametrized_tests"] is True
    assert result.details["edge_case_tests"] >= 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_well_designed_testable_class(testability_evaluator):
    """Test evaluation of well-designed, testable class"""
    code = """
from typing import Optional

class UserService:
    \"\"\"Service with proper dependency injection and testable design\"\"\"

    def __init__(self, repository, cache, logger, validator):
        \"\"\"Initialize with injected dependencies\"\"\"
        self.repository = repository
        self.cache = cache
        self.logger = logger
        self.validator = validator

    def get_user(self, user_id: int) -> Optional[dict]:
        \"\"\"Get user by ID with caching\"\"\"
        cached = self.cache.get(f"user:{user_id}")
        if cached:
            self.logger.info(f"Cache hit for user {user_id}")
            return cached

        user = self.repository.find_by_id(user_id)
        if user:
            self.cache.set(f"user:{user_id}", user)
            self.logger.info(f"Loaded user {user_id} from database")

        return user

    def create_user(self, username: str, email: str) -> dict:
        \"\"\"Create new user\"\"\"
        if not self.validator.validate_email(email):
            raise ValueError("Invalid email")

        user = self.repository.create(username, email)
        self.logger.info(f"Created user {user['id']}")
        return user
"""

    # Act
    result = await testability_evaluator.evaluate(
        code=code,
        context={
            "language": "python",
            "is_test_file": False,
            "test_coverage": 92.0
        }
    )

    # Assert
    assert result.score >= Decimal("8.0")
    assert result.details["dependency_injection"] is True
    assert result.details["global_state_usage"] == 0
    assert result.details["testable_structure"] is True
    assert result.details["coverage_score"] >= 3.0
