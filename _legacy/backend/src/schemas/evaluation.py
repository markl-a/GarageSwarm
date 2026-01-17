"""Evaluation-related Pydantic schemas"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class QualityGrade(str, Enum):
    """Quality grade enum"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAIL = "fail"


class EvaluationRequest(BaseModel):
    """Request to evaluate a subtask"""
    code: str = Field(..., description="Source code to evaluate")
    language: str = Field(default="python", description="Programming language")
    description: Optional[str] = Field(None, description="Task/subtask description")
    requirements: List[str] = Field(default_factory=list, description="Explicit requirements list")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "def hello():\n    print('Hello, World!')",
                "language": "python",
                "description": "Create a hello world function",
                "requirements": ["Create a function", "Print greeting"],
                "context": {}
            }
        }
    )


class ComponentScore(BaseModel):
    """Individual component evaluation score"""
    score: float = Field(..., ge=0, le=10, description="Component score (0-10)")
    weight: float = Field(..., ge=0, le=1, description="Weight in overall score")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed breakdown")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Issues found")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "score": 8.5,
                "weight": 0.25,
                "details": {"syntax_errors": 0, "lint_warnings": 2},
                "issues": [],
                "suggestions": ["Add more comments"]
            }
        }
    )


class EvaluationSummary(BaseModel):
    """Summary of evaluation results"""
    overall_assessment: str = Field(..., description="Human-readable assessment")
    strengths: List[str] = Field(default_factory=list, description="Code strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Code weaknesses")
    critical_actions: List[str] = Field(default_factory=list, description="Critical actions needed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "overall_assessment": "Code quality is good with minor improvements needed",
                "strengths": ["Code Quality: 8.5/10", "Security: 9.0/10"],
                "weaknesses": ["Completeness: 5.5/10"],
                "critical_actions": []
            }
        }
    )


class EvaluationReportResponse(BaseModel):
    """Complete evaluation report"""
    overall_score: float = Field(..., ge=0, le=10, description="Overall weighted score (0-10)")
    quality_grade: QualityGrade = Field(..., description="Quality grade category")
    component_scores: Dict[str, float] = Field(..., description="Individual component scores")
    weights: Dict[str, float] = Field(..., description="Weight configuration used")
    detailed_results: Dict[str, ComponentScore] = Field(..., description="Detailed component results")
    all_issues: List[Dict[str, Any]] = Field(..., description="All issues sorted by severity")
    all_suggestions: List[str] = Field(..., description="All improvement suggestions")
    summary: EvaluationSummary = Field(..., description="Human-readable summary")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "overall_score": 7.8,
                "quality_grade": "good",
                "component_scores": {
                    "code_quality": 8.5,
                    "completeness": 7.0,
                    "security": 8.0
                },
                "weights": {
                    "code_quality": 0.25,
                    "completeness": 0.30,
                    "security": 0.25,
                    "reserved": 0.20
                },
                "detailed_results": {},
                "all_issues": [],
                "all_suggestions": ["Add more unit tests"],
                "summary": {
                    "overall_assessment": "Code quality is good",
                    "strengths": ["Code Quality: 8.5/10"],
                    "weaknesses": [],
                    "critical_actions": []
                }
            }
        }
    )


class SubtaskEvaluationResponse(BaseModel):
    """Evaluation result stored in database"""
    evaluation_id: UUID = Field(..., description="Unique evaluation identifier")
    subtask_id: UUID = Field(..., description="Evaluated subtask ID")
    code_quality: Optional[float] = Field(None, ge=0, le=10, description="Code quality score")
    completeness: Optional[float] = Field(None, ge=0, le=10, description="Completeness score")
    security: Optional[float] = Field(None, ge=0, le=10, description="Security score")
    architecture: Optional[float] = Field(None, ge=0, le=10, description="Architecture score")
    testability: Optional[float] = Field(None, ge=0, le=10, description="Testability score")
    overall_score: float = Field(..., ge=0, le=10, description="Overall weighted score")
    details: Optional[Dict[str, Any]] = Field(None, description="Detailed evaluation results")
    evaluated_at: datetime = Field(..., description="Evaluation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "evaluation_id": "789e0123-e89b-12d3-a456-426614174002",
                "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                "code_quality": 8.5,
                "completeness": 7.0,
                "security": 8.0,
                "architecture": None,
                "testability": None,
                "overall_score": 7.8,
                "details": {
                    "code_quality": {"syntax_errors": 0},
                    "completeness": {"requirement_coverage": 70.0},
                    "security": {"high_risk_count": 0}
                },
                "evaluated_at": "2025-12-08T10:00:00Z"
            }
        }
    )


class EvaluationListResponse(BaseModel):
    """List of evaluations"""
    evaluations: List[SubtaskEvaluationResponse]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "evaluations": [],
                "total": 0
            }
        }
    )


class EvaluationStatsResponse(BaseModel):
    """Evaluation statistics"""
    total_evaluations: int = Field(..., description="Total number of evaluations")
    average_score: float = Field(..., ge=0, le=10, description="Average overall score")
    grade_distribution: Dict[str, int] = Field(..., description="Count by quality grade")
    component_averages: Dict[str, float] = Field(..., description="Average scores by component")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_evaluations": 100,
                "average_score": 7.5,
                "grade_distribution": {
                    "excellent": 10,
                    "good": 40,
                    "acceptable": 30,
                    "poor": 15,
                    "fail": 5
                },
                "component_averages": {
                    "code_quality": 7.8,
                    "completeness": 7.2,
                    "security": 8.0
                }
            }
        }
    )


class WeightsConfigRequest(BaseModel):
    """Request to update evaluation weights"""
    code_quality: float = Field(default=0.25, ge=0, le=1, description="Code quality weight")
    completeness: float = Field(default=0.30, ge=0, le=1, description="Completeness weight")
    security: float = Field(default=0.25, ge=0, le=1, description="Security weight")
    reserved: float = Field(default=0.20, ge=0, le=1, description="Reserved weight")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code_quality": 0.25,
                "completeness": 0.30,
                "security": 0.25,
                "reserved": 0.20
            }
        }
    )


class WeightsConfigResponse(BaseModel):
    """Current weights configuration"""
    weights: Dict[str, float] = Field(..., description="Current weight configuration")
    message: str = Field(..., description="Response message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "weights": {
                    "code_quality": 0.25,
                    "completeness": 0.30,
                    "security": 0.25,
                    "reserved": 0.20
                },
                "message": "Weights updated successfully"
            }
        }
    )
