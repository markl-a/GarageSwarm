"""
Unit tests for authentication system

Tests JWT token handling, password hashing, and token blacklist.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from jose import jwt, JWTError

from src.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    blacklist_token,
    TokenType,
    TokenBlacklist,
)
from src.auth.password import hash_password, verify_password
from src.config import settings


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "my_secure_password"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format

    def test_verify_password_success(self):
        """Test successful password verification"""
        password = "my_secure_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Test failed password verification"""
        password = "my_secure_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_password_unique_salts(self):
        """Test that same password produces different hashes (salt)"""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token creation and verification"""

    def setup_method(self):
        """Clear token blacklist before each test"""
        TokenBlacklist.clear()

    def test_create_access_token(self):
        """Test access token creation"""
        user_id = uuid4()
        username = "test_user"

        token = create_access_token(user_id, username)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify payload
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["username"] == username
        assert payload["type"] == TokenType.ACCESS.value

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        user_id = uuid4()
        username = "test_user"

        token = create_refresh_token(user_id, username)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify payload
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["username"] == username
        assert payload["type"] == TokenType.REFRESH.value

    def test_verify_access_token_success(self):
        """Test successful access token verification"""
        user_id = uuid4()
        username = "test_user"

        token = create_access_token(user_id, username)
        payload = verify_token(token, TokenType.ACCESS)

        assert payload["sub"] == str(user_id)
        assert payload["username"] == username
        assert payload["type"] == TokenType.ACCESS.value

    def test_verify_refresh_token_success(self):
        """Test successful refresh token verification"""
        user_id = uuid4()
        username = "test_user"

        token = create_refresh_token(user_id, username)
        payload = verify_token(token, TokenType.REFRESH)

        assert payload["sub"] == str(user_id)
        assert payload["username"] == username
        assert payload["type"] == TokenType.REFRESH.value

    def test_verify_token_type_mismatch(self):
        """Test token type verification failure"""
        user_id = uuid4()
        username = "test_user"

        # Create access token but verify as refresh
        token = create_access_token(user_id, username)

        with pytest.raises(ValueError, match="Expected refresh token"):
            verify_token(token, TokenType.REFRESH)

    def test_verify_expired_token(self):
        """Test expired token verification"""
        user_id = uuid4()
        username = "test_user"

        # Create token with negative expiry (already expired)
        expire = datetime.utcnow() - timedelta(minutes=1)
        claims = {
            "sub": str(user_id),
            "username": username,
            "type": TokenType.ACCESS.value,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        with pytest.raises(JWTError):
            verify_token(token, TokenType.ACCESS)

    def test_verify_invalid_token(self):
        """Test invalid token verification"""
        with pytest.raises(JWTError):
            verify_token("invalid.token.here", TokenType.ACCESS)

    def test_verify_token_wrong_secret(self):
        """Test token verification with wrong secret key"""
        user_id = uuid4()
        username = "test_user"

        # Create token with different secret
        expire = datetime.utcnow() + timedelta(minutes=15)
        claims = {
            "sub": str(user_id),
            "username": username,
            "type": TokenType.ACCESS.value,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(claims, "wrong_secret_key", algorithm=settings.ALGORITHM)

        with pytest.raises(JWTError):
            verify_token(token, TokenType.ACCESS)

    def test_decode_token(self):
        """Test token decoding without verification"""
        user_id = uuid4()
        username = "test_user"

        token = create_access_token(user_id, username)
        payload = decode_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["username"] == username

    def test_create_token_with_additional_claims(self):
        """Test creating token with additional claims"""
        user_id = uuid4()
        username = "test_user"
        additional_claims = {"role": "admin", "permissions": ["read", "write"]}

        token = create_access_token(user_id, username, additional_claims)
        payload = verify_token(token, TokenType.ACCESS)

        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]


class TestTokenBlacklist:
    """Test token blacklist functionality"""

    def setup_method(self):
        """Clear token blacklist before each test"""
        TokenBlacklist.clear()

    def test_blacklist_token(self):
        """Test adding token to blacklist"""
        token = "sample.jwt.token"

        blacklist_token(token)

        assert TokenBlacklist.is_blacklisted(token) is True

    def test_non_blacklisted_token(self):
        """Test checking non-blacklisted token"""
        token = "sample.jwt.token"

        assert TokenBlacklist.is_blacklisted(token) is False

    def test_verify_blacklisted_token(self):
        """Test that blacklisted tokens fail verification"""
        user_id = uuid4()
        username = "test_user"

        token = create_access_token(user_id, username)

        # Verify token works before blacklisting
        payload = verify_token(token, TokenType.ACCESS)
        assert payload["sub"] == str(user_id)

        # Blacklist token
        blacklist_token(token)

        # Verify token fails after blacklisting
        with pytest.raises(JWTError, match="Token has been revoked"):
            verify_token(token, TokenType.ACCESS)

    def test_clear_blacklist(self):
        """Test clearing blacklist"""
        token = "sample.jwt.token"

        blacklist_token(token)
        assert TokenBlacklist.is_blacklisted(token) is True

        TokenBlacklist.clear()
        assert TokenBlacklist.is_blacklisted(token) is False


class TestTokenExpiry:
    """Test token expiration times"""

    def test_access_token_expiry(self):
        """Test access token expires in 15 minutes"""
        user_id = uuid4()
        username = "test_user"

        token = create_access_token(user_id, username)
        payload = decode_token(token)

        exp = datetime.fromtimestamp(payload["exp"])
        iat = datetime.fromtimestamp(payload["iat"])

        expiry_minutes = (exp - iat).total_seconds() / 60

        # Should be 15 minutes (with small margin for execution time)
        assert 14.9 < expiry_minutes <= 15.0

    def test_refresh_token_expiry(self):
        """Test refresh token expires in 7 days"""
        user_id = uuid4()
        username = "test_user"

        token = create_refresh_token(user_id, username)
        payload = decode_token(token)

        exp = datetime.fromtimestamp(payload["exp"])
        iat = datetime.fromtimestamp(payload["iat"])

        expiry_days = (exp - iat).total_seconds() / 86400  # 86400 seconds in a day

        # Should be 7 days (with small margin for execution time)
        assert 6.99 < expiry_days <= 7.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
