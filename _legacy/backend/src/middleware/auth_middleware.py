"""
Authentication Middleware

Optional middleware for global authentication enforcement and request logging.
"""

from typing import Callable
from datetime import datetime

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.jwt_handler import verify_token, TokenType
from src.logging_config import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication Middleware

    Optionally enforces authentication on all routes except whitelisted paths.
    Also logs all authenticated requests.

    Usage:
        app.add_middleware(
            AuthMiddleware,
            public_paths=["/", "/api/v1/health", "/docs", "/openapi.json"],
            enforce_auth=False,  # Set to True to require auth on all routes
        )
    """

    def __init__(
        self,
        app,
        public_paths: list[str] = None,
        enforce_auth: bool = False,
    ):
        """
        Initialize middleware

        Args:
            app: FastAPI application
            public_paths: List of paths that don't require authentication
            enforce_auth: If True, require auth on all non-public paths
        """
        super().__init__(app)
        self.public_paths = public_paths or []
        self.enforce_auth = enforce_auth

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        start_time = datetime.utcnow()

        # Check if path is public
        is_public = any(
            request.url.path.startswith(path) for path in self.public_paths
        )

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        user_id = None
        username = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

            try:
                # Verify token (use async version for proper blacklist checking)
                from src.auth.jwt_handler import verify_token_async
                payload = await verify_token_async(token, expected_type=TokenType.ACCESS)
                user_id = payload.get("sub")
                username = payload.get("username")

                # Add user info to request state for downstream handlers
                request.state.user_id = user_id
                request.state.username = username
                request.state.authenticated = True

            except Exception as e:
                logger.debug("Token verification failed in middleware", error=str(e))
                request.state.authenticated = False

                # If auth is enforced on non-public paths, reject request
                if self.enforce_auth and not is_public:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid or expired token"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
        else:
            request.state.authenticated = False

            # If auth is enforced on non-public paths, reject request
            if self.enforce_auth and not is_public:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Process request
        response = await call_next(request)

        # Calculate request duration
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Log request (only log successful requests to reduce noise)
        if response.status_code < 400:
            logger.info(
                "Request processed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
                authenticated=request.state.authenticated,
                user_id=user_id,
                username=username,
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware

    Limits requests per user/IP to prevent abuse.

    Usage:
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=100,
            window_seconds=60,
        )
    """

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        """
        Initialize rate limiter

        Args:
            app: FastAPI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict = {}  # {identifier: [(timestamp, ...), ...]}

    def _clean_old_requests(self, identifier: str) -> None:
        """Remove requests outside the time window"""
        if identifier not in self.requests:
            return

        cutoff_time = datetime.utcnow().timestamp() - self.window_seconds
        self.requests[identifier] = [
            ts for ts in self.requests[identifier] if ts > cutoff_time
        ]

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request with rate limiting

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response or 429 if rate limit exceeded
        """
        # Use user_id if authenticated, otherwise use IP address
        identifier = (
            getattr(request.state, "user_id", None)
            or request.client.host
            if request.client
            else "unknown"
        )

        # Clean old requests
        self._clean_old_requests(identifier)

        # Check rate limit
        if identifier in self.requests:
            if len(self.requests[identifier]) >= self.max_requests:
                logger.warning(
                    "Rate limit exceeded",
                    identifier=identifier,
                    requests=len(self.requests[identifier]),
                    window_seconds=self.window_seconds,
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds} seconds."
                    },
                    headers={
                        "Retry-After": str(self.window_seconds),
                    },
                )

        # Add current request
        if identifier not in self.requests:
            self.requests[identifier] = []
        self.requests[identifier].append(datetime.utcnow().timestamp())

        # Process request
        response = await call_next(request)
        return response
