"""
Evaluation Model

Store automated evaluation results for subtask quality assessment
"""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, Numeric, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Evaluation(Base):
    """Evaluation model - automated quality evaluation for subtasks"""

    __tablename__ = "evaluations"

    # Primary key
    evaluation_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique evaluation identifier",
    )

    # Foreign key to subtask
    subtask_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subtasks.subtask_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Evaluated subtask ID",
    )

    # Evaluation scores (0-10, 1 decimal place)
    code_quality = Column(
        Numeric(3, 1), nullable=True, comment="Code quality score (0-10)"
    )

    completeness = Column(
        Numeric(3, 1), nullable=True, comment="Completeness score (0-10)"
    )

    security = Column(Numeric(3, 1), nullable=True, comment="Security score (0-10)")

    architecture = Column(
        Numeric(3, 1), nullable=True, comment="Architecture alignment score (0-10)"
    )

    testability = Column(
        Numeric(3, 1), nullable=True, comment="Testability score (0-10)"
    )

    # Overall score (weighted average)
    overall_score = Column(
        Numeric(3, 1),
        nullable=True,
        index=True,
        comment="Weighted average overall score (0-10)",
    )

    # Detailed results (JSONB)
    details = Column(
        JSONB,
        nullable=True,
        comment="Detailed evaluation results: {code_quality: {issues: [...], score_breakdown: {...}}, ...}",
    )

    # Timestamp
    evaluated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Evaluation time",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "code_quality IS NULL OR (code_quality >= 0 AND code_quality <= 10)",
            name="chk_code_quality",
        ),
        CheckConstraint(
            "completeness IS NULL OR (completeness >= 0 AND completeness <= 10)",
            name="chk_completeness",
        ),
        CheckConstraint(
            "security IS NULL OR (security >= 0 AND security <= 10)",
            name="chk_security",
        ),
        CheckConstraint(
            "architecture IS NULL OR (architecture >= 0 AND architecture <= 10)",
            name="chk_architecture",
        ),
        CheckConstraint(
            "testability IS NULL OR (testability >= 0 AND testability <= 10)",
            name="chk_testability",
        ),
        CheckConstraint(
            "overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 10)",
            name="chk_overall_score",
        ),
    )

    # Relationships
    subtask = relationship("Subtask", back_populates="evaluations")

    def __repr__(self):
        return f"<Evaluation(evaluation_id={self.evaluation_id}, overall_score={self.overall_score})>"

    def calculate_overall_score(self) -> Decimal:
        """
        Calculate weighted overall score

        Weights:
        - Security: 2.0x
        - Code Quality: 1.5x
        - Completeness: 1.5x
        - Architecture: 1.0x
        - Testability: 1.0x
        """
        scores = []
        weights = []

        if self.security is not None:
            scores.append(float(self.security))
            weights.append(2.0)

        if self.code_quality is not None:
            scores.append(float(self.code_quality))
            weights.append(1.5)

        if self.completeness is not None:
            scores.append(float(self.completeness))
            weights.append(1.5)

        if self.architecture is not None:
            scores.append(float(self.architecture))
            weights.append(1.0)

        if self.testability is not None:
            scores.append(float(self.testability))
            weights.append(1.0)

        if not scores:
            return Decimal("0.0")

        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        total_weight = sum(weights)

        return Decimal(str(round(weighted_sum / total_weight, 1)))

    def is_passing(self, threshold: float = 7.0) -> bool:
        """Check if evaluation passed the threshold"""
        if self.overall_score is None:
            return False
        return float(self.overall_score) >= threshold

    def has_critical_issues(self) -> bool:
        """Check if evaluation has critical issues (security < 7.0)"""
        if self.security is None:
            return False
        return float(self.security) < 7.0
