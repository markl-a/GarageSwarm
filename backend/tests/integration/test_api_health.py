"""Integration tests for health check API"""

import pytest
from httpx import AsyncClient
from src.main import app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint():
    """Test GET /api/v1/health endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert "database" in data
        assert "redis" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint_response_structure():
    """Test health endpoint response structure"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        required_keys = ["status", "database", "redis"]
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"

        # Verify status is a string
        assert isinstance(data["status"], str)
