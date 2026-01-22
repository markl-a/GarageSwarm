"""
Human Review System

Handles human review requests, decisions, and notifications for workflow nodes
that require human intervention (HumanReviewNode).

Features:
- Review request creation and management
- Review queue with filtering
- Decision processing with modification support
- Notification hooks for various channels
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis
from redis.asyncio import Redis
from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class ReviewStatus(str, Enum):
    """Status of a review request."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ReviewType(str, Enum):
    """Type of review required."""
    APPROVAL = "approval"  # Simple approve/reject
    INPUT = "input"  # Requires user input
    SELECTION = "selection"  # Choose from options
    EDIT = "edit"  # Edit and approve data


class DecisionType(str, Enum):
    """Type of decision made on a review."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    DEFER = "defer"  # Pass to another reviewer


class NotificationType(str, Enum):
    """Notification channel types."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    SLACK = "slack"
    TEAMS = "teams"
    SMS = "sms"


class Urgency(str, Enum):
    """Urgency levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== Data Models ====================

class ReviewRequest(BaseModel):
    """
    A request for human review within a workflow.

    Created when a HumanReviewNode is reached in workflow execution.
    """
    # Identity
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Workflow context
    workflow_id: UUID
    workflow_name: str = ""
    node_id: str
    node_name: str = ""

    # Review configuration
    review_type: ReviewType = ReviewType.APPROVAL
    instructions: str = ""
    required_fields: List[str] = Field(default_factory=list)

    # State snapshot (data to review)
    state_snapshot: Dict[str, Any] = Field(default_factory=dict)
    context_summary: str = ""

    # Assignment
    assigned_to: Optional[UUID] = None  # Specific user
    assigned_role: Optional[str] = None  # Or role-based
    assigned_at: Optional[datetime] = None

    # Status
    status: ReviewStatus = ReviewStatus.PENDING

    # Timing
    timeout_hours: float = 24.0
    expires_at: Optional[datetime] = None

    # Urgency
    urgency: Urgency = Urgency.NORMAL

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context) -> None:
        """Set expiration time after initialization."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=self.timeout_hours)


class ReviewDecision(BaseModel):
    """
    A decision made on a review request.

    Captures the reviewer's decision along with any modifications or comments.
    """
    # Identity
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str

    # Decision
    decision_type: DecisionType

    # Reviewer
    reviewer_id: UUID
    reviewer_name: str = ""

    # Content
    comments: str = ""
    modifications: Dict[str, Any] = Field(default_factory=dict)  # Modified state values

    # Required field responses (for INPUT type)
    field_responses: Dict[str, Any] = Field(default_factory=dict)

    # Selected option (for SELECTION type)
    selected_option: Optional[str] = None

    # Timing
    decided_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReviewEvent(BaseModel):
    """An event in the review lifecycle for audit logging."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    event_type: str  # created, assigned, viewed, decided, expired, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor_id: Optional[UUID] = None
    data: Dict[str, Any] = Field(default_factory=dict)


# ==================== Notification Service ====================

class NotificationHandler(ABC):
    """Abstract base class for notification handlers."""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        urgency: Urgency,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Send a notification.

        Args:
            recipient: Target address/identifier
            subject: Notification subject/title
            body: Notification content
            urgency: Urgency level
            metadata: Additional data

        Returns:
            True if sent successfully
        """
        pass


class EmailNotificationHandler(NotificationHandler):
    """Email notification handler (placeholder implementation)."""

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        urgency: Urgency,
        metadata: Dict[str, Any]
    ) -> bool:
        """Send email notification."""
        # Placeholder - integrate with email service (SendGrid, SES, etc.)
        logger.info(
            f"Email notification: to={recipient}, subject={subject}, urgency={urgency}"
        )
        # In production, integrate with actual email service
        return True


class WebhookNotificationHandler(NotificationHandler):
    """Webhook notification handler."""

    def __init__(self, default_url: Optional[str] = None):
        self.default_url = default_url

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        urgency: Urgency,
        metadata: Dict[str, Any]
    ) -> bool:
        """Send webhook notification."""
        import aiohttp

        url = recipient or self.default_url
        if not url:
            logger.warning("No webhook URL configured")
            return False

        payload = {
            "subject": subject,
            "body": body,
            "urgency": urgency.value,
            "timestamp": datetime.utcnow().isoformat(),
            **metadata
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status < 300:
                        logger.info(f"Webhook sent to {url}")
                        return True
                    else:
                        logger.warning(f"Webhook failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False


class WebSocketNotificationHandler(NotificationHandler):
    """WebSocket notification handler for real-time updates."""

    def __init__(self, connection_manager: Optional[Any] = None):
        self.connection_manager = connection_manager

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        urgency: Urgency,
        metadata: Dict[str, Any]
    ) -> bool:
        """Send WebSocket notification."""
        if not self.connection_manager:
            logger.warning("No WebSocket connection manager configured")
            return False

        message = {
            "type": "review_notification",
            "subject": subject,
            "body": body,
            "urgency": urgency.value,
            "timestamp": datetime.utcnow().isoformat(),
            **metadata
        }

        try:
            # Assumes connection_manager has a send_to_user method
            await self.connection_manager.send_to_user(recipient, json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"WebSocket notification error: {e}")
            return False


class NotificationService:
    """
    Service for sending notifications through various channels.

    Supports multiple notification handlers (email, webhook, websocket, etc.)
    with configurable routing based on urgency and user preferences.
    """

    def __init__(self):
        self._handlers: Dict[NotificationType, NotificationHandler] = {}
        self._user_preferences: Dict[str, List[NotificationType]] = {}
        self._default_channels: List[NotificationType] = [NotificationType.WEBSOCKET]

    def register_handler(
        self,
        notification_type: NotificationType,
        handler: NotificationHandler
    ) -> None:
        """Register a notification handler for a channel type."""
        self._handlers[notification_type] = handler
        logger.info(f"Registered notification handler: {notification_type}")

    def set_user_preferences(
        self,
        user_id: str,
        channels: List[NotificationType]
    ) -> None:
        """Set notification preferences for a user."""
        self._user_preferences[user_id] = channels

    def set_default_channels(self, channels: List[NotificationType]) -> None:
        """Set default notification channels."""
        self._default_channels = channels

    async def notify_review_created(
        self,
        request: ReviewRequest,
        recipients: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send notification when a review request is created.

        Args:
            request: The review request
            recipients: List of recipient identifiers (user IDs or addresses)

        Returns:
            Dict mapping recipient to success status
        """
        subject = f"[{request.urgency.value.upper()}] Review Required: {request.node_name or request.node_id}"
        body = self._format_review_notification(request)

        return await self._send_to_recipients(
            recipients or [],
            subject,
            body,
            request.urgency,
            {
                "request_id": request.request_id,
                "workflow_id": str(request.workflow_id),
                "review_type": request.review_type.value
            }
        )

    async def notify_review_assigned(
        self,
        request: ReviewRequest,
        assignee_id: str
    ) -> bool:
        """Notify a user that a review has been assigned to them."""
        subject = f"Review Assigned: {request.node_name or request.node_id}"
        body = f"You have been assigned to review:\n\n{request.instructions}"

        results = await self._send_to_recipients(
            [assignee_id],
            subject,
            body,
            request.urgency,
            {"request_id": request.request_id}
        )
        return results.get(assignee_id, False)

    async def notify_review_completed(
        self,
        request: ReviewRequest,
        decision: ReviewDecision,
        recipients: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Notify that a review has been completed."""
        subject = f"Review {decision.decision_type.value.title()}: {request.node_name or request.node_id}"
        body = f"Review decision: {decision.decision_type.value}\n\nComments: {decision.comments}"

        return await self._send_to_recipients(
            recipients or [],
            subject,
            body,
            Urgency.NORMAL,
            {
                "request_id": request.request_id,
                "decision_type": decision.decision_type.value
            }
        )

    async def notify_review_expired(
        self,
        request: ReviewRequest,
        recipients: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Notify that a review has expired."""
        subject = f"Review Expired: {request.node_name or request.node_id}"
        body = f"The review request has expired without a decision."

        return await self._send_to_recipients(
            recipients or [],
            subject,
            body,
            Urgency.HIGH,
            {"request_id": request.request_id}
        )

    def _format_review_notification(self, request: ReviewRequest) -> str:
        """Format a review request into notification body."""
        lines = [
            f"Workflow: {request.workflow_name or str(request.workflow_id)}",
            f"Node: {request.node_name or request.node_id}",
            f"Type: {request.review_type.value}",
            "",
            "Instructions:",
            request.instructions or "No instructions provided.",
            "",
            f"Expires: {request.expires_at.isoformat() if request.expires_at else 'Never'}",
        ]

        if request.required_fields:
            lines.extend(["", "Required fields:", *[f"  - {f}" for f in request.required_fields]])

        if request.context_summary:
            lines.extend(["", "Context:", request.context_summary])

        return "\n".join(lines)

    async def _send_to_recipients(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        urgency: Urgency,
        metadata: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Send notifications to multiple recipients."""
        results = {}

        for recipient in recipients:
            # Get user's preferred channels or use defaults
            channels = self._user_preferences.get(recipient, self._default_channels)

            # Try each channel until one succeeds
            sent = False
            for channel in channels:
                handler = self._handlers.get(channel)
                if handler:
                    try:
                        sent = await handler.send(recipient, subject, body, urgency, metadata)
                        if sent:
                            break
                    except Exception as e:
                        logger.error(f"Notification error ({channel}): {e}")

            results[recipient] = sent

        return results


# ==================== Human Review Manager ====================

class HumanReviewManager:
    """
    Main manager for human review operations.

    Handles:
    - Creating review requests when HumanReviewNode is reached
    - Managing the review queue
    - Processing review decisions
    - Coordinating notifications
    """

    # Redis key prefixes
    KEY_REQUEST = "review:request:{request_id}"
    KEY_QUEUE = "review:queue"
    KEY_USER_QUEUE = "review:user:{user_id}"
    KEY_WORKFLOW_REVIEWS = "review:workflow:{workflow_id}"
    KEY_EVENTS = "review:events:{request_id}"
    KEY_DECISION = "review:decision:{request_id}"

    # Defaults
    DEFAULT_TTL = 3600 * 24 * 7  # 7 days

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        redis_url: str = "redis://localhost:6379",
        notification_service: Optional[NotificationService] = None
    ):
        """
        Initialize the review manager.

        Args:
            redis_client: Existing Redis client or None to create new
            redis_url: Redis connection URL
            notification_service: Optional notification service
        """
        self._redis: Optional[Redis] = redis_client
        self._redis_url = redis_url
        self._connected = False
        self._notification_service = notification_service or NotificationService()

        # Callbacks for workflow integration
        self._on_decision_callbacks: List[Callable] = []

    @property
    def notification_service(self) -> NotificationService:
        """Get the notification service."""
        return self._notification_service

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        self._connected = True
        logger.info("HumanReviewManager connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._connected = False
        logger.info("HumanReviewManager disconnected")

    def _ensure_connected(self) -> None:
        """Ensure Redis is connected."""
        if not self._connected or self._redis is None:
            raise RuntimeError("HumanReviewManager not connected. Call connect() first.")

    def register_decision_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called when a decision is made.

        Callback signature: async def callback(request: ReviewRequest, decision: ReviewDecision)
        """
        self._on_decision_callbacks.append(callback)

    # ==================== Review Request Operations ====================

    async def create_review_request(
        self,
        workflow_id: UUID,
        node_id: str,
        state: Dict[str, Any],
        instructions: str,
        review_type: ReviewType = ReviewType.APPROVAL,
        required_fields: Optional[List[str]] = None,
        timeout_hours: float = 24.0,
        urgency: Urgency = Urgency.NORMAL,
        assigned_to: Optional[UUID] = None,
        workflow_name: str = "",
        node_name: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        notify_recipients: Optional[List[str]] = None
    ) -> ReviewRequest:
        """
        Create a new review request when HumanReviewNode is reached.

        Args:
            workflow_id: ID of the workflow
            node_id: ID of the HumanReviewNode
            state: Current workflow state snapshot
            instructions: Instructions for the reviewer
            review_type: Type of review required
            required_fields: Fields that must be provided (for INPUT type)
            timeout_hours: Hours until expiration
            urgency: Urgency level
            assigned_to: Specific user to assign to
            workflow_name: Name of the workflow
            node_name: Name of the node
            tags: Tags for categorization
            metadata: Additional metadata
            notify_recipients: Users to notify

        Returns:
            Created ReviewRequest
        """
        self._ensure_connected()

        # Create the request
        request = ReviewRequest(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            node_id=node_id,
            node_name=node_name,
            review_type=review_type,
            instructions=instructions,
            required_fields=required_fields or [],
            state_snapshot=state,
            timeout_hours=timeout_hours,
            urgency=urgency,
            assigned_to=assigned_to,
            tags=tags or [],
            metadata=metadata or {}
        )

        if assigned_to:
            request.assigned_at = datetime.utcnow()
            request.status = ReviewStatus.PENDING

        # Generate context summary
        request.context_summary = self._generate_context_summary(state)

        # Store in Redis
        await self._store_request(request)

        # Add to queues
        await self._add_to_queues(request)

        # Log creation event
        await self._log_event(
            request.request_id,
            "created",
            {"workflow_id": str(workflow_id), "node_id": node_id}
        )

        # Send notifications
        if notify_recipients:
            await self._notification_service.notify_review_created(request, notify_recipients)

        logger.info(
            f"Review request created: {request.request_id} "
            f"(workflow={workflow_id}, node={node_id})"
        )

        return request

    async def get_review_request(self, request_id: str) -> Optional[ReviewRequest]:
        """
        Get a review request by ID.

        Args:
            request_id: The request ID

        Returns:
            ReviewRequest or None if not found
        """
        self._ensure_connected()

        key = self.KEY_REQUEST.format(request_id=request_id)
        data = await self._redis.get(key)

        if data:
            return ReviewRequest.model_validate_json(data)
        return None

    async def get_pending_reviews(
        self,
        user_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        review_type: Optional[ReviewType] = None,
        urgency: Optional[Urgency] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ReviewRequest]:
        """
        Get pending review requests with optional filtering.

        Args:
            user_id: Filter by assigned user
            workflow_id: Filter by workflow
            review_type: Filter by review type
            urgency: Filter by urgency
            tags: Filter by tags (any match)
            limit: Maximum results
            offset: Skip first N results

        Returns:
            List of pending ReviewRequests
        """
        self._ensure_connected()

        # Get request IDs from appropriate queue
        if user_id:
            queue_key = self.KEY_USER_QUEUE.format(user_id=str(user_id))
        elif workflow_id:
            queue_key = self.KEY_WORKFLOW_REVIEWS.format(workflow_id=str(workflow_id))
        else:
            queue_key = self.KEY_QUEUE

        # Get all request IDs (we'll filter after fetching)
        request_ids = await self._redis.zrevrange(queue_key, 0, -1)

        # Fetch and filter requests
        results = []
        skipped = 0

        for request_id in request_ids:
            request = await self.get_review_request(request_id)

            if not request:
                continue

            # Check if expired
            if request.expires_at and datetime.utcnow() > request.expires_at:
                if request.status == ReviewStatus.PENDING:
                    await self._handle_expiration(request)
                continue

            # Apply filters
            if request.status not in (ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS):
                continue

            if user_id and request.assigned_to != user_id:
                continue

            if workflow_id and request.workflow_id != workflow_id:
                continue

            if review_type and request.review_type != review_type:
                continue

            if urgency and request.urgency != urgency:
                continue

            if tags and not any(t in request.tags for t in tags):
                continue

            # Apply pagination
            if skipped < offset:
                skipped += 1
                continue

            results.append(request)

            if len(results) >= limit:
                break

        return results

    async def get_review_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a review request.

        Args:
            request_id: The request ID

        Returns:
            Status dict with request and decision info, or None
        """
        self._ensure_connected()

        request = await self.get_review_request(request_id)
        if not request:
            return None

        # Get decision if exists
        decision_key = self.KEY_DECISION.format(request_id=request_id)
        decision_data = await self._redis.get(decision_key)
        decision = ReviewDecision.model_validate_json(decision_data) if decision_data else None

        # Get events
        events = await self._get_events(request_id)

        return {
            "request": request.model_dump(),
            "decision": decision.model_dump() if decision else None,
            "events": [e.model_dump() for e in events],
            "is_expired": request.expires_at and datetime.utcnow() > request.expires_at,
            "is_decided": decision is not None
        }

    # ==================== Decision Processing ====================

    async def submit_decision(
        self,
        request_id: str,
        decision_type: DecisionType,
        reviewer_id: UUID,
        comments: str = "",
        modifications: Optional[Dict[str, Any]] = None,
        field_responses: Optional[Dict[str, Any]] = None,
        selected_option: Optional[str] = None,
        reviewer_name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        notify_recipients: Optional[List[str]] = None
    ) -> ReviewDecision:
        """
        Submit a decision on a review request.

        Args:
            request_id: The request ID
            decision_type: Type of decision (approve/reject/modify/defer)
            reviewer_id: ID of the reviewer
            comments: Optional comments
            modifications: Modified state values (for MODIFY decision)
            field_responses: Responses to required fields (for INPUT type)
            selected_option: Selected option (for SELECTION type)
            reviewer_name: Name of reviewer
            metadata: Additional metadata
            notify_recipients: Users to notify

        Returns:
            The created ReviewDecision

        Raises:
            ValueError: If request not found or already decided
        """
        self._ensure_connected()

        # Get and validate request
        request = await self.get_review_request(request_id)
        if not request:
            raise ValueError(f"Review request not found: {request_id}")

        if request.status in (ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.MODIFIED):
            raise ValueError(f"Review already decided: {request.status}")

        if request.status == ReviewStatus.EXPIRED:
            raise ValueError("Review request has expired")

        if request.status == ReviewStatus.CANCELLED:
            raise ValueError("Review request was cancelled")

        # Validate required fields for INPUT type
        if request.review_type == ReviewType.INPUT and request.required_fields:
            missing = [f for f in request.required_fields if f not in (field_responses or {})]
            if missing and decision_type == DecisionType.APPROVE:
                raise ValueError(f"Missing required fields: {missing}")

        # Create decision
        decision = ReviewDecision(
            request_id=request_id,
            decision_type=decision_type,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            comments=comments,
            modifications=modifications or {},
            field_responses=field_responses or {},
            selected_option=selected_option,
            metadata=metadata or {}
        )

        # Update request status
        status_map = {
            DecisionType.APPROVE: ReviewStatus.APPROVED,
            DecisionType.REJECT: ReviewStatus.REJECTED,
            DecisionType.MODIFY: ReviewStatus.MODIFIED,
            DecisionType.DEFER: ReviewStatus.PENDING  # Stays pending when deferred
        }
        request.status = status_map[decision_type]

        # Store decision
        decision_key = self.KEY_DECISION.format(request_id=request_id)
        await self._redis.set(decision_key, decision.model_dump_json())
        await self._redis.expire(decision_key, self.DEFAULT_TTL)

        # Update request
        await self._store_request(request)

        # Remove from pending queues (unless deferred)
        if decision_type != DecisionType.DEFER:
            await self._remove_from_queues(request)

        # Log event
        await self._log_event(
            request_id,
            "decided",
            {
                "decision_type": decision_type.value,
                "reviewer_id": str(reviewer_id)
            },
            reviewer_id
        )

        # Call callbacks
        for callback in self._on_decision_callbacks:
            try:
                await callback(request, decision)
            except Exception as e:
                logger.error(f"Decision callback error: {e}")

        # Send notifications
        if notify_recipients:
            await self._notification_service.notify_review_completed(
                request, decision, notify_recipients
            )

        logger.info(
            f"Review decision submitted: {request_id} -> {decision_type.value} "
            f"by {reviewer_id}"
        )

        return decision

    async def assign_review(
        self,
        request_id: str,
        user_id: UUID,
        notify: bool = True
    ) -> ReviewRequest:
        """
        Assign a review to a specific user.

        Args:
            request_id: The request ID
            user_id: User to assign to
            notify: Whether to send notification

        Returns:
            Updated ReviewRequest
        """
        self._ensure_connected()

        request = await self.get_review_request(request_id)
        if not request:
            raise ValueError(f"Review request not found: {request_id}")

        # Update assignment
        old_assignee = request.assigned_to
        request.assigned_to = user_id
        request.assigned_at = datetime.utcnow()

        await self._store_request(request)

        # Update user queues
        if old_assignee:
            old_queue_key = self.KEY_USER_QUEUE.format(user_id=str(old_assignee))
            await self._redis.zrem(old_queue_key, request_id)

        new_queue_key = self.KEY_USER_QUEUE.format(user_id=str(user_id))
        await self._redis.zadd(
            new_queue_key,
            {request_id: request.created_at.timestamp()}
        )

        # Log event
        await self._log_event(
            request_id,
            "assigned",
            {"assigned_to": str(user_id), "previous": str(old_assignee) if old_assignee else None}
        )

        # Notify
        if notify:
            await self._notification_service.notify_review_assigned(request, str(user_id))

        return request

    async def cancel_review(
        self,
        request_id: str,
        reason: str = "",
        actor_id: Optional[UUID] = None
    ) -> ReviewRequest:
        """
        Cancel a review request.

        Args:
            request_id: The request ID
            reason: Reason for cancellation
            actor_id: User who cancelled

        Returns:
            Updated ReviewRequest
        """
        self._ensure_connected()

        request = await self.get_review_request(request_id)
        if not request:
            raise ValueError(f"Review request not found: {request_id}")

        request.status = ReviewStatus.CANCELLED
        await self._store_request(request)

        # Remove from queues
        await self._remove_from_queues(request)

        # Log event
        await self._log_event(
            request_id,
            "cancelled",
            {"reason": reason},
            actor_id
        )

        logger.info(f"Review cancelled: {request_id}, reason: {reason}")

        return request

    # ==================== Internal Methods ====================

    async def _store_request(self, request: ReviewRequest) -> None:
        """Store a review request in Redis."""
        key = self.KEY_REQUEST.format(request_id=request.request_id)
        await self._redis.set(key, request.model_dump_json())

        # Set TTL based on expiration
        if request.expires_at:
            ttl = int((request.expires_at - datetime.utcnow()).total_seconds())
            if ttl > 0:
                await self._redis.expire(key, ttl + 3600)  # Extra hour buffer
            else:
                await self._redis.expire(key, self.DEFAULT_TTL)
        else:
            await self._redis.expire(key, self.DEFAULT_TTL)

    async def _add_to_queues(self, request: ReviewRequest) -> None:
        """Add request to appropriate queues."""
        score = request.created_at.timestamp()

        # Add to main queue
        await self._redis.zadd(self.KEY_QUEUE, {request.request_id: score})

        # Add to workflow queue
        workflow_key = self.KEY_WORKFLOW_REVIEWS.format(workflow_id=str(request.workflow_id))
        await self._redis.zadd(workflow_key, {request.request_id: score})

        # Add to user queue if assigned
        if request.assigned_to:
            user_key = self.KEY_USER_QUEUE.format(user_id=str(request.assigned_to))
            await self._redis.zadd(user_key, {request.request_id: score})

    async def _remove_from_queues(self, request: ReviewRequest) -> None:
        """Remove request from queues."""
        await self._redis.zrem(self.KEY_QUEUE, request.request_id)

        workflow_key = self.KEY_WORKFLOW_REVIEWS.format(workflow_id=str(request.workflow_id))
        await self._redis.zrem(workflow_key, request.request_id)

        if request.assigned_to:
            user_key = self.KEY_USER_QUEUE.format(user_id=str(request.assigned_to))
            await self._redis.zrem(user_key, request.request_id)

    async def _log_event(
        self,
        request_id: str,
        event_type: str,
        data: Dict[str, Any],
        actor_id: Optional[UUID] = None
    ) -> None:
        """Log a review event."""
        event = ReviewEvent(
            request_id=request_id,
            event_type=event_type,
            actor_id=actor_id,
            data=data
        )

        events_key = self.KEY_EVENTS.format(request_id=request_id)
        await self._redis.lpush(events_key, event.model_dump_json())
        await self._redis.expire(events_key, self.DEFAULT_TTL)

    async def _get_events(self, request_id: str) -> List[ReviewEvent]:
        """Get all events for a request."""
        events_key = self.KEY_EVENTS.format(request_id=request_id)
        raw_events = await self._redis.lrange(events_key, 0, -1)

        return [ReviewEvent.model_validate_json(raw) for raw in raw_events]

    async def _handle_expiration(self, request: ReviewRequest) -> None:
        """Handle an expired review request."""
        request.status = ReviewStatus.EXPIRED
        await self._store_request(request)
        await self._remove_from_queues(request)

        await self._log_event(
            request.request_id,
            "expired",
            {"expired_at": datetime.utcnow().isoformat()}
        )

        # Notify about expiration
        await self._notification_service.notify_review_expired(request)

        logger.info(f"Review expired: {request.request_id}")

    def _generate_context_summary(self, state: Dict[str, Any], max_length: int = 500) -> str:
        """Generate a summary of the workflow state for review."""
        # Simple summarization - in production, could use LLM
        summary_parts = []

        for key, value in state.items():
            if key.startswith("_"):  # Skip internal keys
                continue

            if isinstance(value, dict):
                summary_parts.append(f"{key}: {{{len(value)} items}}")
            elif isinstance(value, list):
                summary_parts.append(f"{key}: [{len(value)} items]")
            elif isinstance(value, str) and len(value) > 100:
                summary_parts.append(f"{key}: {value[:100]}...")
            else:
                summary_parts.append(f"{key}: {value}")

        summary = "\n".join(summary_parts)
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

    async def check_expired_reviews(self) -> List[str]:
        """
        Check for and handle expired reviews.

        This can be called periodically by a background task.

        Returns:
            List of expired request IDs
        """
        self._ensure_connected()

        expired_ids = []
        request_ids = await self._redis.zrange(self.KEY_QUEUE, 0, -1)

        for request_id in request_ids:
            request = await self.get_review_request(request_id)
            if request and request.expires_at and datetime.utcnow() > request.expires_at:
                if request.status == ReviewStatus.PENDING:
                    await self._handle_expiration(request)
                    expired_ids.append(request_id)

        return expired_ids


# ==================== Singleton Factory ====================

_review_manager_instance: Optional[HumanReviewManager] = None


def get_review_manager() -> HumanReviewManager:
    """Get the singleton HumanReviewManager instance."""
    global _review_manager_instance
    if _review_manager_instance is None:
        _review_manager_instance = HumanReviewManager(
            redis_url=settings.REDIS_URL
        )
    return _review_manager_instance
