"""
Aggregation Score Engine

Combines multiple evaluator results into a single overall score with quality grading.
"""

from typing import Any, Dict, List, Optional
from decimal import Decimal
from enum import Enum
import structlog

from .base import BaseEvaluator, EvaluationResult
from .code_quality import CodeQualityEvaluator
from .completeness import CompletenessEvaluator
from .security import SecurityEvaluator

logger = structlog.get_logger()


class QualityGrade(str, Enum):
    """Quality grade categories"""
    EXCELLENT = "excellent"  # 9.0 - 10.0
    GOOD = "good"            # 7.0 - 8.9
    ACCEPTABLE = "acceptable"  # 5.0 - 6.9
    POOR = "poor"            # 3.0 - 4.9
    FAIL = "fail"            # 0.0 - 2.9


class EvaluationAggregator:
    """
    Aggregates results from multiple evaluators into a single score

    Default weights:
    - Code Quality: 25%
    - Completeness: 30%
    - Security: 25%
    - Reserved: 20% (for future evaluators)
    """

    DEFAULT_WEIGHTS = {
        "code_quality": 0.25,
        "completeness": 0.30,
        "security": 0.25,
        "reserved": 0.20
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize aggregator with custom weights

        Args:
            weights: Custom weight configuration (optional)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()

        # Initialize evaluators
        self.evaluators = {
            "code_quality": CodeQualityEvaluator(weight=self.weights["code_quality"]),
            "completeness": CompletenessEvaluator(weight=self.weights["completeness"]),
            "security": SecurityEvaluator(weight=self.weights["security"])
        }

    def _validate_weights(self) -> None:
        """Validate that weights sum to approximately 1.0"""
        total = sum(self.weights.values())
        if not (0.99 <= total <= 1.01):
            logger.warning(
                "Weights do not sum to 1.0, normalizing",
                total=total,
                weights=self.weights
            )
            # Normalize weights
            for key in self.weights:
                self.weights[key] = self.weights[key] / total

    async def evaluate_all(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all evaluators and aggregate results

        Args:
            code: Source code to evaluate
            context: Context information

        Returns:
            Aggregated evaluation report
        """
        results = {}
        all_issues = []
        all_suggestions = []

        # Run each evaluator
        for name, evaluator in self.evaluators.items():
            try:
                logger.info(f"Running {name} evaluator")
                result = await evaluator.evaluate(code, context)
                results[name] = result

                # Collect all issues and suggestions
                all_issues.extend([
                    {**issue, "evaluator": name}
                    for issue in result.issues
                ])
                all_suggestions.extend([
                    f"[{name.upper()}] {suggestion}"
                    for suggestion in result.suggestions
                ])

            except Exception as e:
                logger.error(
                    f"Evaluator {name} failed",
                    evaluator=name,
                    error=str(e)
                )
                # Create a failed result
                results[name] = EvaluationResult(
                    score=Decimal("0.0"),
                    details={"error": str(e)},
                    suggestions=[f"Evaluator failed: {str(e)}"],
                    issues=[{
                        "type": "evaluator_error",
                        "severity": "critical",
                        "message": f"Evaluator failed: {str(e)}"
                    }]
                )

        # Calculate aggregate score
        total_score = self._calculate_aggregate_score(results)

        # Determine quality grade
        grade = self._determine_grade(total_score)

        # Compile aggregate report
        report = {
            "overall_score": float(total_score),
            "quality_grade": grade.value,
            "component_scores": {
                name: float(result.score)
                for name, result in results.items()
            },
            "weights": self.weights,
            "detailed_results": {
                name: result.to_dict()
                for name, result in results.items()
            },
            "all_issues": self._prioritize_issues(all_issues),
            "all_suggestions": self._deduplicate_suggestions(all_suggestions),
            "summary": self._generate_summary(total_score, grade, results)
        }

        return report

    def _calculate_aggregate_score(self, results: Dict[str, EvaluationResult]) -> Decimal:
        """
        Calculate weighted aggregate score

        Formula: total_score = Σ(score_i * weight_i) / Σ(weight_i)
        """
        weighted_sum = Decimal("0.0")
        total_weight = Decimal("0.0")

        for name, result in results.items():
            weight = Decimal(str(self.weights.get(name, 0)))
            weighted_sum += result.score * weight
            total_weight += weight

        # Add reserved weight to total (assuming perfect score for unused portion)
        reserved_weight = Decimal(str(self.weights.get("reserved", 0)))
        if reserved_weight > Decimal("0"):
            weighted_sum += Decimal("10.0") * reserved_weight
            total_weight += reserved_weight

        if total_weight > Decimal("0"):
            final_score = weighted_sum / total_weight
        else:
            final_score = Decimal("0.0")

        return Decimal(str(round(float(final_score), 1)))

    def _determine_grade(self, score: Decimal) -> QualityGrade:
        """Determine quality grade based on score"""
        score_float = float(score)

        if score_float >= 9.0:
            return QualityGrade.EXCELLENT
        elif score_float >= 7.0:
            return QualityGrade.GOOD
        elif score_float >= 5.0:
            return QualityGrade.ACCEPTABLE
        elif score_float >= 3.0:
            return QualityGrade.POOR
        else:
            return QualityGrade.FAIL

    def _prioritize_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort issues by severity (critical > high > medium > low)"""
        severity_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }

        return sorted(
            issues,
            key=lambda x: severity_order.get(x.get("severity", "low"), 3)
        )

    def _deduplicate_suggestions(self, suggestions: List[str]) -> List[str]:
        """Remove duplicate suggestions while preserving order"""
        seen = set()
        unique = []

        for suggestion in suggestions:
            # Normalize for comparison
            normalized = suggestion.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(suggestion)

        return unique

    def _generate_summary(
        self,
        score: Decimal,
        grade: QualityGrade,
        results: Dict[str, EvaluationResult]
    ) -> Dict[str, Any]:
        """Generate human-readable summary"""
        summary = {
            "overall_assessment": self._get_grade_description(grade),
            "strengths": [],
            "weaknesses": [],
            "critical_actions": []
        }

        # Identify strengths (scores >= 8.0)
        for name, result in results.items():
            if result.score >= Decimal("8.0"):
                summary["strengths"].append(f"{name.replace('_', ' ').title()}: {float(result.score):.1f}/10")

        # Identify weaknesses (scores < 6.0)
        for name, result in results.items():
            if result.score < Decimal("6.0"):
                summary["weaknesses"].append(f"{name.replace('_', ' ').title()}: {float(result.score):.1f}/10")

        # Critical actions from security issues
        security_result = results.get("security")
        if security_result and security_result.details.get("requires_human_review"):
            summary["critical_actions"].append("CRITICAL: Code requires human security review")

        # High priority issues
        high_priority_count = sum(
            1 for result in results.values()
            for issue in result.issues
            if issue.get("severity") in ["critical", "high"]
        )
        if high_priority_count > 0:
            summary["critical_actions"].append(
                f"Address {high_priority_count} high-priority issue(s)"
            )

        return summary

    def _get_grade_description(self, grade: QualityGrade) -> str:
        """Get human-readable description for grade"""
        descriptions = {
            QualityGrade.EXCELLENT: "Code quality is excellent with minimal issues",
            QualityGrade.GOOD: "Code quality is good with minor improvements needed",
            QualityGrade.ACCEPTABLE: "Code quality is acceptable but has room for improvement",
            QualityGrade.POOR: "Code quality is poor and requires significant improvements",
            QualityGrade.FAIL: "Code quality is unacceptable and needs major rework"
        }
        return descriptions.get(grade, "Unknown quality grade")

    def get_weights(self) -> Dict[str, float]:
        """Get current weights configuration"""
        return self.weights.copy()

    def update_weights(self, weights: Dict[str, float]) -> None:
        """
        Update weights configuration

        Args:
            weights: New weight configuration
        """
        self.weights.update(weights)
        self._validate_weights()

        # Update evaluator weights
        for name, evaluator in self.evaluators.items():
            if name in self.weights:
                evaluator.set_weight(self.weights[name])

    def add_evaluator(self, name: str, evaluator: BaseEvaluator, weight: float) -> None:
        """
        Add a custom evaluator to the aggregation

        Args:
            name: Evaluator name
            evaluator: Evaluator instance
            weight: Weight for this evaluator
        """
        self.evaluators[name] = evaluator
        self.weights[name] = weight
        self._validate_weights()

    def __repr__(self) -> str:
        return f"<EvaluationAggregator(evaluators={len(self.evaluators)}, weights={self.weights})>"
