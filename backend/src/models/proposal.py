"""
Proposal Model

Multi-agent voting system for code/output proposals and consensus-based selection
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, Float, ForeignKey, Integer, String, TEXT, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Proposal(Base):
    """Proposal model - worker-generated code/output proposals for voting"""

    __tablename__ = "proposals"

    # Primary key
    proposal_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique proposal identifier",
    )

    # Foreign keys
    subtask_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subtasks.subtask_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated subtask ID",
    )

    worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workers.worker_id"),
        nullable=False,
        index=True,
        comment="Worker that generated this proposal",
    )

    # Proposal content
    content = Column(
        TEXT,
        nullable=False,
        comment="Generated code/output content",
    )

    # Evaluation and voting
    evaluation_score = Column(
        Float,
        nullable=True,
        comment="Automated evaluation score (0-10)",
    )

    votes = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total votes received from other workers",
    )

    # Proposal status
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Proposal status: pending | selected | rejected",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Proposal creation time",
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update time",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'selected', 'rejected')",
            name="chk_proposal_status",
        ),
        CheckConstraint(
            "evaluation_score IS NULL OR (evaluation_score >= 0 AND evaluation_score <= 10)",
            name="chk_evaluation_score",
        ),
        CheckConstraint(
            "votes >= 0",
            name="chk_votes_non_negative",
        ),
    )

    # Relationships
    subtask = relationship("Subtask", back_populates="proposals")
    worker = relationship("Worker", back_populates="proposals")
    proposal_votes = relationship(
        "ProposalVote",
        back_populates="proposal",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Proposal(proposal_id={self.proposal_id}, subtask_id={self.subtask_id}, status={self.status}, votes={self.votes})>"

    def is_pending(self) -> bool:
        """Check if proposal is pending"""
        return self.status == "pending"

    def is_selected(self) -> bool:
        """Check if proposal was selected"""
        return self.status == "selected"

    def is_rejected(self) -> bool:
        """Check if proposal was rejected"""
        return self.status == "rejected"

    def add_vote(self) -> None:
        """Increment vote count"""
        self.votes += 1

    def get_vote_count(self) -> int:
        """Get total vote count"""
        return self.votes


class ProposalVote(Base):
    """ProposalVote model - individual worker votes on proposals"""

    __tablename__ = "proposal_votes"

    # Primary key
    vote_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique vote identifier",
    )

    # Foreign keys
    proposal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proposals.proposal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Voted proposal ID",
    )

    voter_worker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workers.worker_id"),
        nullable=False,
        index=True,
        comment="Worker who cast this vote",
    )

    # Vote details
    vote_value = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Vote value: 1 (approve), 0 (neutral), -1 (reject)",
    )

    reasoning = Column(
        TEXT,
        nullable=True,
        comment="Optional reasoning/comments for the vote",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Vote creation time",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "vote_value IN (-1, 0, 1)",
            name="chk_vote_value",
        ),
        # Ensure one vote per worker per proposal
        # Note: This is a unique constraint, not a check constraint
        # Adding it as a tuple element
    )

    # Relationships
    proposal = relationship("Proposal", back_populates="proposal_votes")
    voter = relationship("Worker", foreign_keys=[voter_worker_id])

    def __repr__(self):
        return f"<ProposalVote(vote_id={self.vote_id}, proposal_id={self.proposal_id}, voter_worker_id={self.voter_worker_id}, vote_value={self.vote_value})>"

    def is_approve(self) -> bool:
        """Check if vote is an approval"""
        return self.vote_value == 1

    def is_neutral(self) -> bool:
        """Check if vote is neutral"""
        return self.vote_value == 0

    def is_reject(self) -> bool:
        """Check if vote is a rejection"""
        return self.vote_value == -1
