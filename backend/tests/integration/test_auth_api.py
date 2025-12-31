"""
Integration tests for authentication API endpoints

Tests the complete authentication flow including registration, login, refresh, and logout.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.auth.jwt_handler import TokenBlacklist, decode_token


@pytest.fixture(autouse=True)
async def clear_blacklist():
    """Clear token blacklist before each test"""
    TokenBlacklist.clear()
    yield
    TokenBlacklist.clear()


class TestUserRegistration:
    """Test user registration endpoint"""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "new_user",
                "email": "new_user@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "user" in data
        assert data["user"]["username"] == "new_user"
        assert data["user"]["email"] == "new_user@example.com"
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]
        assert data["message"] == "User registered successfully"

    async def test_register_duplicate_username(self, client: AsyncClient, db: AsyncSession):
        """Test registration with existing username"""
        # Create first user
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "existing_user",
                "email": "user1@example.com",
                "password": "SecurePass123!",
            },
        )

        # Try to create second user with same username
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "existing_user",
                "email": "user2@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 409
        assert "Username already registered" in response.json()["detail"]

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Test registration with existing email"""
        # Create first user
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "user1",
                "email": "existing@example.com",
                "password": "SecurePass123!",
            },
        )

        # Try to create second user with same email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "user2",
                "email": "existing@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 409
        assert "Email already registered" in response.json()["detail"]

    async def test_register_invalid_username(self, client: AsyncClient):
        """Test registration with invalid username"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "ab",  # Too short
                "email": "user@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "test_user",
                "email": "not-an-email",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422

    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "test_user",
                "email": "user@example.com",
                "password": "short",  # Too short
            },
        )

        assert response.status_code == 422


class TestUserLogin:
    """Test user login endpoint"""

    async def test_login_success(self, client: AsyncClient):
        """Test successful login"""
        # Register user
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "login_user",
                "email": "login@example.com",
                "password": "SecurePass123!",
            },
        )

        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "login_user",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "user" in data
        assert "tokens" in data
        assert data["user"]["username"] == "login_user"
        assert data["tokens"]["token_type"] == "bearer"
        assert len(data["tokens"]["access_token"]) > 0
        assert len(data["tokens"]["refresh_token"]) > 0
        assert data["tokens"]["expires_in"] == 900  # 15 minutes in seconds

    async def test_login_with_email(self, client: AsyncClient):
        """Test login using email instead of username"""
        # Register user
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "email_user",
                "email": "email@example.com",
                "password": "SecurePass123!",
            },
        )

        # Login with email
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "email@example.com",  # Using email
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        assert response.json()["user"]["username"] == "email_user"

    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with wrong password"""
        # Register user
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "test_user",
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )

        # Login with wrong password
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_user",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    async def test_login_updates_last_login(self, client: AsyncClient, db: AsyncSession):
        """Test that login updates last_login timestamp"""
        # Register user
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "timestamp_user",
                "email": "timestamp@example.com",
                "password": "SecurePass123!",
            },
        )

        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "timestamp_user",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200

        # Check that last_login was updated
        result = await db.execute(
            select(User).where(User.username == "timestamp_user")
        )
        user = result.scalar_one()
        assert user.last_login is not None


class TestProtectedEndpoints:
    """Test protected endpoints requiring authentication"""

    async def test_get_current_user(self, client: AsyncClient):
        """Test getting current user profile"""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "profile_user",
                "email": "profile@example.com",
                "password": "SecurePass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "profile_user",
                "password": "SecurePass123!",
            },
        )
        access_token = login_response.json()["tokens"]["access_token"]

        # Get profile
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "profile_user"
        assert data["email"] == "profile@example.com"

    async def test_protected_endpoint_no_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 403  # No credentials provided

    async def test_protected_endpoint_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh endpoint"""

    async def test_refresh_token_success(self, client: AsyncClient):
        """Test successful token refresh"""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "refresh_user",
                "email": "refresh@example.com",
                "password": "SecurePass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "refresh_user",
                "password": "SecurePass123!",
            },
        )
        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_with_access_token_fails(self, client: AsyncClient):
        """Test that access token cannot be used for refresh"""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "test_user",
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_user",
                "password": "SecurePass123!",
            },
        )
        access_token = login_response.json()["tokens"]["access_token"]

        # Try to refresh with access token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401


class TestLogout:
    """Test logout endpoint"""

    async def test_logout_success(self, client: AsyncClient):
        """Test successful logout"""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "logout_user",
                "email": "logout@example.com",
                "password": "SecurePass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "logout_user",
                "password": "SecurePass123!",
            },
        )
        tokens = login_response.json()["tokens"]

        # Logout
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            },
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"

    async def test_logout_blacklists_token(self, client: AsyncClient):
        """Test that logout blacklists tokens"""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "blacklist_user",
                "email": "blacklist@example.com",
                "password": "SecurePass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "blacklist_user",
                "password": "SecurePass123!",
            },
        )
        access_token = login_response.json()["tokens"]["access_token"]

        # Verify token works before logout
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

        # Logout
        await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"access_token": access_token},
        )

        # Verify token doesn't work after logout
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 401


class TestPasswordChange:
    """Test password change endpoint"""

    async def test_change_password_success(self, client: AsyncClient):
        """Test successful password change"""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "password_user",
                "email": "password@example.com",
                "password": "OldPass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "password_user",
                "password": "OldPass123!",
            },
        )
        access_token = login_response.json()["tokens"]["access_token"]

        # Change password
        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "OldPass123!",
                "new_password": "NewPass123!",
            },
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

        # Verify new password works
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "password_user",
                "password": "NewPass123!",
            },
        )
        assert login_response.status_code == 200

    async def test_change_password_wrong_current(self, client: AsyncClient):
        """Test password change with wrong current password"""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "test_user",
                "email": "test@example.com",
                "password": "CurrentPass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_user",
                "password": "CurrentPass123!",
            },
        )
        access_token = login_response.json()["tokens"]["access_token"]

        # Try to change with wrong current password
        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "WrongPass123!",
                "new_password": "NewPass123!",
            },
        )

        assert response.status_code == 401


class TestPublicEndpoint:
    """Test optional authentication endpoint"""

    async def test_public_endpoint_authenticated(self, client: AsyncClient):
        """Test public endpoint with authentication"""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "public_user",
                "email": "public@example.com",
                "password": "SecurePass123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "public_user",
                "password": "SecurePass123!",
            },
        )
        access_token = login_response.json()["tokens"]["access_token"]

        # Access public endpoint with token
        response = await client.get(
            "/api/v1/auth/public",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert "public_user" in data["message"]

    async def test_public_endpoint_unauthenticated(self, client: AsyncClient):
        """Test public endpoint without authentication"""
        response = await client.get("/api/v1/auth/public")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert "Guest" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
