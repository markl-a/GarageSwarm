# JWT Authentication System

Complete JWT-based authentication system for the Multi-Agent on the Web platform.

## Features

- **JWT Tokens**: Access (15 min) and refresh (7 day) tokens
- **Password Security**: Bcrypt hashing with salt
- **Token Blacklist**: Logout functionality via token revocation
- **FastAPI Dependencies**: Easy-to-use authentication decorators
- **Optional Middleware**: Global auth enforcement and rate limiting

## Architecture

```
auth/
├── __init__.py           # Package exports
├── jwt_handler.py        # Token creation, verification, blacklist
├── password.py           # Password hashing with bcrypt
├── dependencies.py       # FastAPI auth dependencies
└── README.md            # This file
```

## Quick Start

### 1. Register a New User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

Response:
```json
{
  "user": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "created_at": "2025-01-09T10:00:00Z",
    "last_login": null,
    "is_active": true
  },
  "message": "User registered successfully"
}
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePass123!"
  }'
```

Response:
```json
{
  "user": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "created_at": "2025-01-09T10:00:00Z",
    "last_login": "2025-01-09T10:05:00Z",
    "is_active": true
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 900
  },
  "message": "Login successful"
}
```

### 3. Access Protected Endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 4. Refresh Access Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### 5. Logout

```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

## Using Authentication in Your Endpoints

### Require Authentication

```python
from fastapi import APIRouter, Depends
from src.auth.dependencies import require_auth
from src.models.user import User

router = APIRouter()

@router.post("/tasks")
async def create_task(
    task_data: TaskCreate,
    user: User = Depends(require_auth)
):
    """Only authenticated users can create tasks"""
    return await task_service.create(task_data, user.user_id)
```

### Optional Authentication

```python
from typing import Optional
from fastapi import APIRouter, Depends
from src.auth.dependencies import optional_auth
from src.models.user import User

router = APIRouter()

@router.get("/data")
async def get_data(user: Optional[User] = Depends(optional_auth)):
    """Returns different data based on auth status"""
    if user:
        return {"data": "premium", "user": user.username}
    return {"data": "basic"}
```

### Get Current User

```python
from fastapi import APIRouter, Depends
from src.auth.dependencies import get_current_active_user
from src.models.user import User

router = APIRouter()

@router.get("/profile")
async def get_profile(user: User = Depends(get_current_active_user)):
    """Get authenticated user's profile"""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email
    }
```

## Token Structure

### Access Token Payload

```json
{
  "sub": "123e4567-e89b-12d3-a456-426614174000",
  "username": "john_doe",
  "type": "access",
  "exp": 1704876300,
  "iat": 1704875400
}
```

### Refresh Token Payload

```json
{
  "sub": "123e4567-e89b-12d3-a456-426614174000",
  "username": "john_doe",
  "type": "refresh",
  "exp": 1705481100,
  "iat": 1704875400
}
```

## Security Best Practices

### 1. Secret Key Management

**Never commit your SECRET_KEY to version control!**

Generate a secure secret key:

```python
import secrets
print(secrets.token_urlsafe(32))
```

Set it via environment variable:

```bash
export SECRET_KEY="your-super-secure-random-key-here"
```

### 2. Password Requirements

Current requirements:
- Minimum 8 characters
- No maximum (hashed to fixed length)

Consider adding in production:
- Uppercase + lowercase letters
- Numbers
- Special characters
- Check against common password lists

### 3. HTTPS Only

**Always use HTTPS in production!** HTTP Bearer tokens can be intercepted.

### 4. Token Storage (Frontend)

**Do NOT store tokens in localStorage** - vulnerable to XSS attacks.

Recommended approaches:
- **HttpOnly cookies** (server-side managed)
- **Memory storage** (lost on refresh, requires re-login)
- **Secure session storage** with encryption

### 5. Token Blacklist in Production

Current implementation uses in-memory blacklist. For production:

```python
# Use Redis for distributed token blacklist
class RedisTokenBlacklist:
    async def add(self, token: str, expiry: int):
        await redis_client.setex(f"blacklist:{token}", expiry, "1")

    async def is_blacklisted(self, token: str) -> bool:
        return await redis_client.exists(f"blacklist:{token}")
```

### 6. Rate Limiting

Protect auth endpoints from brute force:

```python
from src.middleware.auth_middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    max_requests=10,  # 10 requests
    window_seconds=60  # per minute
)
```

## Optional Middleware

### Global Authentication Enforcement

```python
from src.middleware.auth_middleware import AuthMiddleware

app.add_middleware(
    AuthMiddleware,
    public_paths=[
        "/",
        "/api/v1/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/docs",
        "/openapi.json"
    ],
    enforce_auth=True  # Require auth on all non-public routes
)
```

### Rate Limiting

```python
from src.middleware.auth_middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,  # 100 requests
    window_seconds=60  # per minute
)
```

## Database Migration

Run the migration to add `is_active` field:

```bash
cd backend
alembic upgrade head
```

Or apply specific migration:

```bash
alembic upgrade 003_add_user_is_active
```

## Configuration

Set these in `.env` file:

```bash
# Security
SECRET_KEY=your-super-secure-random-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login and get tokens | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | No (requires refresh token) |
| POST | `/api/v1/auth/logout` | Logout (blacklist tokens) | Yes |
| GET | `/api/v1/auth/me` | Get current user profile | Yes |
| POST | `/api/v1/auth/change-password` | Change password | Yes |
| GET | `/api/v1/auth/public` | Example public endpoint | Optional |

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "User account is inactive"
}
```

### 409 Conflict

```json
{
  "detail": "Username already registered"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded. Maximum 100 requests per 60 seconds."
}
```

## Testing

Run authentication tests:

```bash
cd backend
pytest tests/unit/test_auth.py -v
pytest tests/integration/test_auth_api.py -v
```

## Troubleshooting

### "Invalid or expired token"

- Check token hasn't expired (access: 15 min, refresh: 7 days)
- Verify SECRET_KEY matches between token creation and verification
- Check token isn't blacklisted (after logout)

### "User not found"

- User may have been deleted from database
- Check user_id in token matches database

### "User account is inactive"

- User's `is_active` field is set to False
- Contact admin to reactivate account

## Future Enhancements

1. **Email Verification**: Require email verification on registration
2. **Password Reset**: Email-based password reset flow
3. **2FA/MFA**: Two-factor authentication support
4. **OAuth2**: Social login (Google, GitHub, etc.)
5. **Role-Based Access Control (RBAC)**: User roles and permissions
6. **Session Management**: View and revoke active sessions
7. **Audit Logging**: Track all authentication events
8. **Redis Token Blacklist**: Distributed blacklist for production
9. **Refresh Token Rotation**: Issue new refresh token on each use
10. **Password History**: Prevent password reuse

## References

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io](https://jwt.io/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Python-JOSE Documentation](https://python-jose.readthedocs.io/)
- [Passlib Documentation](https://passlib.readthedocs.io/)
