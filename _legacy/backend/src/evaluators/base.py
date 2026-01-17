"""
Base Evaluator Architecture

Provides abstract base class for all evaluators with a pluggable architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from decimal import Decimal


@dataclass
class EvaluationResult:
    """
    Result of an evaluation

    Attributes:
        score: Evaluation score (0.0-10.0)
        details: Detailed breakdown of the evaluation
        suggestions: List of improvement suggestions
        issues: List of identified issues
        metadata: Additional metadata about the evaluation
    """
    score: Decimal
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate score is within valid range"""
        if not isinstance(self.score, Decimal):
            self.score = Decimal(str(self.score))

        if self.score < Decimal("0.0") or self.score > Decimal("10.0"):
            raise ValueError(f"Score must be between 0.0 and 10.0, got {self.score}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "score": float(self.score),
            "details": self.details,
            "suggestions": self.suggestions,
            "issues": self.issues,
            "metadata": self.metadata
        }


class BaseEvaluator(ABC):
    """
    Abstract base class for all evaluators

    Evaluators assess different aspects of generated code and provide
    quantitative scores with detailed feedback.
    """

    def __init__(self, weight: float = 1.0, config: Optional[Dict[str, Any]] = None):
        """
        Initialize evaluator

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
        """
        Evaluate code and return result

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

    def get_weight(self) -> float:
        """Get evaluator weight"""
        return self.weight

    def set_weight(self, weight: float) -> None:
        """Set evaluator weight"""
        if weight < 0:
            raise ValueError(f"Weight must be non-negative, got {weight}")
        self.weight = weight

    def get_config(self) -> Dict[str, Any]:
        """Get evaluator configuration"""
        return self.config.copy()

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update evaluator configuration"""
        self.config.update(config)

    def _clamp_score(self, score: float, min_score: float = 0.0, max_score: float = 10.0) -> Decimal:
        """
        Clamp score to valid range and convert to Decimal

        Args:
            score: Raw score to clamp
            min_score: Minimum allowed score
            max_score: Maximum allowed score

        Returns:
            Clamped score as Decimal rounded to 1 decimal place
        """
        clamped = max(min_score, min(max_score, score))
        return Decimal(str(round(clamped, 1)))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(weight={self.weight})>"
