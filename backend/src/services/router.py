"""
Intelligent Task Router

Routes tasks to the most suitable worker based on multiple factors:
- Capability matching (tool support)
- Historical success rate
- Current load
- Cost efficiency
- Latency estimates
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.task import Task, TaskStatus
from src.models.worker import Worker, WorkerStatus

logger = logging.getLogger(__name__)


@dataclass
class RoutingFactors:
    """Weights for routing decision factors."""
    capability_match: float = 0.30
    historical_success: float = 0.25
    current_load: float = 0.20
    cost_efficiency: float = 0.15
    latency_estimate: float = 0.10


@dataclass
class WorkerPerformance:
    """Historical performance data for a worker."""
    worker_id: UUID
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_execution_time: float = 0.0
    last_failure: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.5  # Default for new workers
        return self.successful_tasks / self.total_tasks


@dataclass
class RoutingDecision:
    """Result of a routing decision."""
    worker_id: UUID
    worker_name: str
    score: float
    factors: Dict[str, float] = field(default_factory=dict)
    reason: str = ""


@dataclass
class CostEstimate:
    """Cost estimate for executing a task on a worker."""
    worker_id: UUID
    tool: str
    estimated_cost: float
    is_local: bool


class CostTracker:
    """Tracks and estimates costs for different tools."""

    # Approximate costs per 1K tokens (or per call for local)
    COST_MAP = {
        "claude_code": {"input": 0.003, "output": 0.015, "is_local": False},
        "gemini_cli": {"input": 0.00025, "output": 0.0005, "is_local": False},
        "ollama": {"input": 0.0, "output": 0.0, "is_local": True},
        "codex_cli": {"input": 0.002, "output": 0.008, "is_local": False},
    }

    def estimate_cost(self, worker: Worker, task: Task) -> float:
        """Estimate cost for a task on a worker."""
        tool = task.tool if hasattr(task, 'tool') else 'ollama'
        cost_info = self.COST_MAP.get(tool, {"input": 0.001, "output": 0.005, "is_local": False})

        if cost_info["is_local"]:
            return 0.0

        # Rough estimate: assume 500 input tokens, 1000 output tokens
        estimated_input_tokens = 0.5  # in thousands
        estimated_output_tokens = 1.0  # in thousands

        return (
            cost_info["input"] * estimated_input_tokens +
            cost_info["output"] * estimated_output_tokens
        )


class IntelligentRouter:
    """
    Intelligent task router that selects the best worker for a task.

    Uses multi-dimensional scoring to make routing decisions:
    1. Capability matching - Does the worker support the required tool?
    2. Historical success - What's the worker's track record?
    3. Current load - How busy is the worker?
    4. Cost efficiency - Is it a local or API-based tool?
    5. Latency estimate - Expected response time
    """

    def __init__(
        self,
        factors: Optional[RoutingFactors] = None,
        exploration_rate: float = 0.1
    ):
        """
        Initialize the router.

        Args:
            factors: Scoring weights for different factors
            exploration_rate: Probability of selecting non-optimal worker (for exploration)
        """
        self.factors = factors or RoutingFactors()
        self.exploration_rate = exploration_rate
        self.cost_tracker = CostTracker()
        self._performance_cache: Dict[UUID, WorkerPerformance] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._last_cache_update: Optional[datetime] = None

    async def route_task(
        self,
        task: Task,
        db: AsyncSession,
        preferred_worker_id: Optional[UUID] = None
    ) -> Optional[RoutingDecision]:
        """
        Route a task to the most suitable worker.

        Args:
            task: The task to route
            db: Database session
            preferred_worker_id: Optional preferred worker

        Returns:
            RoutingDecision with selected worker, or None if no suitable worker
        """
        # Get available workers
        candidates = await self._get_capable_workers(task, db)

        if not candidates:
            logger.warning(f"No capable workers found for task {task.id}")
            return None

        # If preferred worker is available and capable, use it
        if preferred_worker_id:
            for worker in candidates:
                if worker.id == preferred_worker_id:
                    return RoutingDecision(
                        worker_id=worker.id,
                        worker_name=worker.name,
                        score=1.0,
                        reason="Preferred worker selected"
                    )

        # Calculate scores for all candidates
        scored_workers = []
        for worker in candidates:
            score, factors = await self._calculate_score(worker, task, db)
            scored_workers.append((worker, score, factors))

        # Sort by score (descending)
        scored_workers.sort(key=lambda x: x[1], reverse=True)

        # Select worker with exploration
        selected = self._select_with_exploration(scored_workers)

        if selected:
            worker, score, factors = selected
            return RoutingDecision(
                worker_id=worker.id,
                worker_name=worker.name,
                score=score,
                factors=factors,
                reason=self._generate_reason(factors)
            )

        return None

    async def _get_capable_workers(
        self,
        task: Task,
        db: AsyncSession
    ) -> List[Worker]:
        """Get workers that can handle the task."""
        # Get all online/idle workers
        query = select(Worker).where(
            Worker.status.in_([WorkerStatus.ONLINE, WorkerStatus.IDLE]),
            Worker.is_active == True
        )

        result = await db.execute(query)
        workers = result.scalars().all()

        # Filter by tool capability
        tool_required = getattr(task, 'tool', None)
        if tool_required:
            capable = []
            for worker in workers:
                # Check if worker supports the required tool
                tools = worker.tools if worker.tools else []
                if tool_required in tools or not tool_required:
                    capable.append(worker)
            return capable

        return list(workers)

    async def _calculate_score(
        self,
        worker: Worker,
        task: Task,
        db: AsyncSession
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate multi-factor score for a worker.

        Returns:
            Tuple of (total_score, factor_breakdown)
        """
        factors = {}
        total = 0.0

        # 1. Capability match
        capability_score = await self._score_capability(worker, task)
        factors["capability_match"] = capability_score
        total += capability_score * self.factors.capability_match

        # 2. Historical success rate
        performance = await self._get_worker_performance(worker.id, db)
        success_score = performance.success_rate
        factors["historical_success"] = success_score
        total += success_score * self.factors.historical_success

        # 3. Current load
        load_score = self._score_current_load(worker)
        factors["current_load"] = load_score
        total += load_score * self.factors.current_load

        # 4. Cost efficiency
        cost_score = self._score_cost_efficiency(worker, task)
        factors["cost_efficiency"] = cost_score
        total += cost_score * self.factors.cost_efficiency

        # 5. Latency estimate
        latency_score = self._score_latency(worker, performance)
        factors["latency_estimate"] = latency_score
        total += latency_score * self.factors.latency_estimate

        return total, factors

    async def _score_capability(self, worker: Worker, task: Task) -> float:
        """Score based on tool capability match."""
        tool_required = getattr(task, 'tool', None)

        if not tool_required:
            return 1.0  # Any worker can handle generic tasks

        tools = worker.tools if worker.tools else []

        if tool_required in tools:
            return 1.0

        # Partial match for similar tools
        similar_tools = {
            "claude_code": ["codex_cli", "gemini_cli"],
            "gemini_cli": ["claude_code", "codex_cli"],
            "ollama": ["gemini_cli"],
        }

        if tool_required in similar_tools:
            for alt in similar_tools[tool_required]:
                if alt in tools:
                    return 0.7  # Can handle but not optimal

        return 0.0

    async def _get_worker_performance(
        self,
        worker_id: UUID,
        db: AsyncSession
    ) -> WorkerPerformance:
        """Get or calculate worker performance metrics."""
        # Check cache
        if worker_id in self._performance_cache:
            cached = self._performance_cache[worker_id]
            if self._last_cache_update and datetime.utcnow() - self._last_cache_update < self._cache_ttl:
                return cached

        # Calculate from database
        total_query = select(func.count(Task.id)).where(
            Task.worker_id == worker_id,
            Task.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED])
        )
        total_result = await db.execute(total_query)
        total_tasks = total_result.scalar() or 0

        success_query = select(func.count(Task.id)).where(
            Task.worker_id == worker_id,
            Task.status == TaskStatus.COMPLETED
        )
        success_result = await db.execute(success_query)
        successful_tasks = success_result.scalar() or 0

        failed_tasks = total_tasks - successful_tasks

        performance = WorkerPerformance(
            worker_id=worker_id,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks
        )

        # Update cache
        self._performance_cache[worker_id] = performance
        self._last_cache_update = datetime.utcnow()

        return performance

    def _score_current_load(self, worker: Worker) -> float:
        """Score based on current worker load."""
        # Prefer idle workers
        if worker.status == WorkerStatus.IDLE:
            return 1.0
        elif worker.status == WorkerStatus.ONLINE:
            return 0.7
        elif worker.status == WorkerStatus.BUSY:
            return 0.3
        return 0.0

    def _score_cost_efficiency(self, worker: Worker, task: Task) -> float:
        """Score based on cost efficiency."""
        cost = self.cost_tracker.estimate_cost(worker, task)

        # Local (free) tools get highest score
        if cost == 0.0:
            return 1.0

        # Scale inversely with cost
        return 1.0 / (1.0 + cost * 10)

    def _score_latency(self, worker: Worker, performance: WorkerPerformance) -> float:
        """Score based on expected latency."""
        # Use historical execution time if available
        if performance.avg_execution_time > 0:
            # Assume 60 seconds is baseline
            ratio = 60.0 / max(performance.avg_execution_time, 1.0)
            return min(ratio, 1.0)

        # Default based on worker status
        if worker.status == WorkerStatus.IDLE:
            return 1.0
        elif worker.status == WorkerStatus.ONLINE:
            return 0.8
        return 0.5

    def _select_with_exploration(
        self,
        scored_workers: List[Tuple[Worker, float, Dict[str, float]]]
    ) -> Optional[Tuple[Worker, float, Dict[str, float]]]:
        """
        Select a worker with optional exploration.

        Most of the time, select the highest scorer.
        Sometimes (exploration_rate), select randomly to discover better options.
        """
        if not scored_workers:
            return None

        # Exploration: occasionally pick a random worker
        if random.random() < self.exploration_rate and len(scored_workers) > 1:
            # Weighted random selection (still prefer higher scores)
            weights = [s[1] + 0.1 for s in scored_workers]  # Add small base weight
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]

            selected_idx = random.choices(range(len(scored_workers)), weights=weights, k=1)[0]
            return scored_workers[selected_idx]

        # Exploitation: select highest scorer
        return scored_workers[0]

    def _generate_reason(self, factors: Dict[str, float]) -> str:
        """Generate human-readable reason for selection."""
        top_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:2]
        reasons = []

        for factor, score in top_factors:
            if factor == "capability_match" and score > 0.8:
                reasons.append("best tool match")
            elif factor == "historical_success" and score > 0.8:
                reasons.append("high success rate")
            elif factor == "current_load" and score > 0.8:
                reasons.append("low load")
            elif factor == "cost_efficiency" and score > 0.8:
                reasons.append("cost effective")
            elif factor == "latency_estimate" and score > 0.8:
                reasons.append("fast response")

        if reasons:
            return "Selected due to: " + ", ".join(reasons)
        return "Best available worker"


# Singleton instance
_router_instance: Optional[IntelligentRouter] = None


def get_router() -> IntelligentRouter:
    """Get the singleton router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = IntelligentRouter()
    return _router_instance
