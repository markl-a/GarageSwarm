"""
Authentication Example Script

Demonstrates how to use the JWT authentication system.

Usage:
    python examples/auth_example.py
"""

import asyncio
import httpx
from typing import Optional


class AuthClient:
    """Simple client for testing authentication"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    async def register(self, username: str, email: str, password: str):
        """Register a new user"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/register",
                json={
                    "username": username,
                    "email": email,
                    "password": password,
                },
            )
            response.raise_for_status()
            data = response.json()
            print(f"✓ User registered: {data['user']['username']}")
            return data

    async def login(self, username: str, password: str):
        """Login and store tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "username": username,
                    "password": password,
                },
            )
            response.raise_for_status()
            data = response.json()

            self.access_token = data["tokens"]["access_token"]
            self.refresh_token = data["tokens"]["refresh_token"]

            print(f"✓ Logged in as: {data['user']['username']}")
            print(f"  Access token expires in: {data['tokens']['expires_in']} seconds")
            return data

    async def get_profile(self):
        """Get current user profile"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call login() first.")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            print(f"✓ Profile retrieved: {data['username']} ({data['email']})")
            return data

    async def refresh_access_token(self):
        """Refresh access token"""
        if not self.refresh_token:
            raise ValueError("No refresh token available.")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token},
            )
            response.raise_for_status()
            data = response.json()

            self.access_token = data["access_token"]
            print("✓ Access token refreshed")
            return data

    async def change_password(self, current_password: str, new_password: str):
        """Change password"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call login() first.")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={
                    "current_password": current_password,
                    "new_password": new_password,
                },
            )
            response.raise_for_status()
            data = response.json()
            print(f"✓ Password changed: {data['message']}")
            return data

    async def logout(self):
        """Logout and blacklist tokens"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call login() first.")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                },
            )
            response.raise_for_status()
            data = response.json()

            self.access_token = None
            self.refresh_token = None

            print(f"✓ Logged out: {data['message']}")
            return data


async def main():
    """Run authentication examples"""
    print("=" * 60)
    print("JWT Authentication Example")
    print("=" * 60)
    print()

    auth = AuthClient()

    try:
        # 1. Register a new user
        print("1. Registering new user...")
        await auth.register(
            username="demo_user",
            email="demo@example.com",
            password="SecurePass123!",
        )
        print()

        # 2. Login
        print("2. Logging in...")
        await auth.login(username="demo_user", password="SecurePass123!")
        print()

        # 3. Get user profile
        print("3. Getting user profile...")
        await auth.get_profile()
        print()

        # 4. Refresh access token
        print("4. Refreshing access token...")
        await auth.refresh_access_token()
        print()

        # 5. Change password
        print("5. Changing password...")
        await auth.change_password(
            current_password="SecurePass123!",
            new_password="NewSecurePass123!",
        )
        print()

        # 6. Login with new password
        print("6. Logging in with new password...")
        await auth.login(username="demo_user", password="NewSecurePass123!")
        print()

        # 7. Logout
        print("7. Logging out...")
        await auth.logout()
        print()

        # 8. Try to access protected endpoint after logout (should fail)
        print("8. Trying to access profile after logout...")
        try:
            await auth.get_profile()
        except ValueError as e:
            print(f"✓ Expected error: {e}")
        print()

        print("=" * 60)
        print("Authentication Example Complete!")
        print("=" * 60)

    except httpx.HTTPStatusError as e:
        print(f"✗ HTTP Error: {e.response.status_code}")
        print(f"  Detail: {e.response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    print("Make sure the backend server is running on http://localhost:8000")
    print("Press Ctrl+C to exit")
    print()

    asyncio.run(main())
