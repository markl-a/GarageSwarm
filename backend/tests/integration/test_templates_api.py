"""
Integration tests for Templates API endpoints

Tests template CRUD operations, authentication, and template application to tasks.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.models.template import WorkflowTemplate, TemplateStep
from src.models.task import Task
from src.models.subtask import Subtask


# Sample template data for testing
@pytest.fixture
def sample_template_data():
    """Sample template creation data"""
    return {
        "name": "Test API Template",
        "description": "A test template for API development workflow",
        "category": "development",
        "steps": [
            {
                "name": "Design API",
                "description": "Design API endpoints and models",
                "step_order": 1,
                "step_type": "analysis",
                "complexity": 2,
                "priority": 100,
                "is_required": True,
                "is_parallel": False,
            },
            {
                "name": "Implement API",
                "description": "Implement the API endpoints",
                "step_order": 2,
                "step_type": "code_generation",
                "depends_on": [1],
                "recommended_tool": "claude_code",
                "complexity": 3,
                "priority": 90,
                "is_required": True,
                "is_parallel": False,
            },
            {
                "name": "Write Tests",
                "description": "Write unit and integration tests",
                "step_order": 3,
                "step_type": "test",
                "depends_on": [2],
                "recommended_tool": "gemini_cli",
                "complexity": 2,
                "priority": 80,
                "is_required": True,
                "is_parallel": False,
            },
        ],
        "tags": ["api", "backend", "testing"],
        "estimated_duration": 120,
        "complexity_level": 3,
        "default_checkpoint_frequency": "medium",
        "default_privacy_level": "normal",
    }


@pytest.fixture
async def auth_headers(test_client: AsyncClient):
    """Get authentication headers for testing"""
    # Register a test user
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "username": "template_user",
            "email": "template@example.com",
            "password": "SecurePass123!",
        },
    )

    # Login to get token
    login_response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "username": "template_user",
            "password": "SecurePass123!",
        },
    )
    access_token = login_response.json()["tokens"]["access_token"]

    return {"Authorization": f"Bearer {access_token}"}


class TestTemplateCreation:
    """Test template creation endpoint"""

    async def test_create_template_success(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test successful template creation"""
        response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert "template_id" in data
        assert data["name"] == sample_template_data["name"]
        assert data["message"] == "Template created successfully"

        # Verify UUID format
        template_id = UUID(data["template_id"])
        assert isinstance(template_id, UUID)

    async def test_create_template_duplicate_name(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test creating template with duplicate name fails"""
        # Create first template
        await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )

        # Try to create second template with same name
        response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_create_template_no_steps(
        self, test_client: AsyncClient, auth_headers: dict
    ):
        """Test creating template without steps fails"""
        template_data = {
            "name": "Empty Template",
            "description": "Template with no steps",
            "category": "development",
            "steps": [],
        }

        response = await test_client.post(
            "/api/v1/templates",
            json=template_data,
            headers=auth_headers,
        )

        assert response.status_code == 422

    async def test_create_template_no_auth(
        self, test_client: AsyncClient, sample_template_data: dict
    ):
        """Test creating template without authentication fails"""
        response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
        )

        assert response.status_code == 403


class TestTemplateList:
    """Test template listing endpoint"""

    async def test_list_templates_success(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test listing templates"""
        # Create a template
        create_response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        # List templates
        response = await test_client.get(
            "/api/v1/templates",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "templates" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["templates"]) > 0
        assert data["total"] > 0

        # Check template structure
        template = data["templates"][0]
        assert "template_id" in template
        assert "name" in template
        assert "category" in template
        assert "step_count" in template

    async def test_list_templates_filter_by_category(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test filtering templates by category"""
        # Create template
        await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )

        # Filter by category
        response = await test_client.get(
            "/api/v1/templates?category=development",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) > 0
        assert all(t["category"] == "development" for t in data["templates"])

    async def test_list_templates_pagination(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test template pagination"""
        # Create multiple templates
        for i in range(3):
            template_data = sample_template_data.copy()
            template_data["name"] = f"Test Template {i}"
            await test_client.post(
                "/api/v1/templates",
                json=template_data,
                headers=auth_headers,
            )

        # Test pagination
        response = await test_client.get(
            "/api/v1/templates?limit=2&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert len(data["templates"]) <= 2

    async def test_list_templates_no_auth(self, test_client: AsyncClient):
        """Test listing templates without authentication fails"""
        response = await test_client.get("/api/v1/templates")

        assert response.status_code == 403


class TestTemplateDetail:
    """Test template detail endpoint"""

    async def test_get_template_success(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test getting template details"""
        # Create template
        create_response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )
        template_id = create_response.json()["template_id"]

        # Get template details
        response = await test_client.get(
            f"/api/v1/templates/{template_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["template_id"] == template_id
        assert data["name"] == sample_template_data["name"]
        assert data["description"] == sample_template_data["description"]
        assert data["category"] == sample_template_data["category"]
        assert len(data["steps"]) == len(sample_template_data["steps"])

        # Verify step details
        for step in data["steps"]:
            assert "step_id" in step
            assert "name" in step
            assert "step_order" in step
            assert "step_type" in step

    async def test_get_template_not_found(
        self, test_client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent template"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(
            f"/api/v1/templates/{fake_uuid}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_get_template_no_auth(self, test_client: AsyncClient):
        """Test getting template without authentication fails"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/api/v1/templates/{fake_uuid}")

        assert response.status_code == 403


class TestTemplateUpdate:
    """Test template update endpoint"""

    async def test_update_template_success(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test updating template"""
        # Create template
        create_response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )
        template_id = create_response.json()["template_id"]

        # Update template
        update_data = {
            "description": "Updated description",
            "tags": ["api", "backend", "updated"],
            "is_active": True,
        }

        response = await test_client.patch(
            f"/api/v1/templates/{template_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["description"] == update_data["description"]
        assert set(data["tags"]) == set(update_data["tags"])
        assert data["is_active"] == update_data["is_active"]

    async def test_update_template_not_found(
        self, test_client: AsyncClient, auth_headers: dict
    ):
        """Test updating non-existent template"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/templates/{fake_uuid}",
            json={"description": "Updated"},
            headers=auth_headers,
        )

        assert response.status_code == 400

    async def test_update_template_no_auth(self, test_client: AsyncClient):
        """Test updating template without authentication fails"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await test_client.patch(
            f"/api/v1/templates/{fake_uuid}",
            json={"description": "Updated"},
        )

        assert response.status_code == 403


class TestTemplateDelete:
    """Test template deletion endpoint"""

    async def test_delete_template_success(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test deleting template"""
        # Create template
        create_response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )
        template_id = create_response.json()["template_id"]

        # Delete template
        response = await test_client.delete(
            f"/api/v1/templates/{template_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify template is deleted
        get_response = await test_client.get(
            f"/api/v1/templates/{template_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_delete_template_not_found(
        self, test_client: AsyncClient, auth_headers: dict
    ):
        """Test deleting non-existent template"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(
            f"/api/v1/templates/{fake_uuid}",
            headers=auth_headers,
        )

        assert response.status_code == 400

    async def test_delete_template_no_auth(self, test_client: AsyncClient):
        """Test deleting template without authentication fails"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await test_client.delete(f"/api/v1/templates/{fake_uuid}")

        assert response.status_code == 403


class TestTemplateApply:
    """Test template application to tasks"""

    async def test_apply_template_to_task_success(
        self,
        test_client: AsyncClient,
        auth_headers: dict,
        sample_template_data: dict,
        db_session: AsyncSession,
    ):
        """Test applying template to a task"""
        # Create template
        create_response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )
        template_id = create_response.json()["template_id"]

        # Create a task
        task_response = await test_client.post(
            "/api/v1/tasks",
            json={
                "description": "Test task for template application",
                "task_metadata": {"test": "data"},
            },
            headers=auth_headers,
        )
        task_id = task_response.json()["task_id"]

        # Apply template to task
        response = await test_client.post(
            f"/api/v1/tasks/{task_id}/apply-template",
            json={"template_id": template_id},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == task_id
        assert data["template_id"] == template_id
        assert data["template_name"] == sample_template_data["name"]
        assert data["subtask_count"] == len(sample_template_data["steps"])
        assert "successfully" in data["message"]

        # Verify subtasks were created
        result = await db_session.execute(
            select(Subtask).where(Subtask.task_id == UUID(task_id))
        )
        subtasks = list(result.scalars().all())
        assert len(subtasks) == len(sample_template_data["steps"])

    async def test_apply_template_not_found(
        self, test_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test applying non-existent template"""
        # Create a task
        task_response = await test_client.post(
            "/api/v1/tasks",
            json={"description": "Test task"},
            headers=auth_headers,
        )
        task_id = task_response.json()["task_id"]

        fake_template_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.post(
            f"/api/v1/tasks/{task_id}/apply-template",
            json={"template_id": fake_template_id},
            headers=auth_headers,
        )

        assert response.status_code == 400

    async def test_apply_template_task_not_found(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test applying template to non-existent task"""
        # Create template
        create_response = await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )
        template_id = create_response.json()["template_id"]

        fake_task_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.post(
            f"/api/v1/tasks/{fake_task_id}/apply-template",
            json={"template_id": template_id},
            headers=auth_headers,
        )

        assert response.status_code == 400

    async def test_apply_template_no_auth(self, test_client: AsyncClient):
        """Test applying template without authentication fails"""
        fake_task_id = "00000000-0000-0000-0000-000000000000"
        fake_template_id = "00000000-0000-0000-0000-000000000000"

        response = await test_client.post(
            f"/api/v1/tasks/{fake_task_id}/apply-template",
            json={"template_id": fake_template_id},
        )

        assert response.status_code == 403


class TestPopularTemplates:
    """Test popular templates endpoint"""

    async def test_get_popular_templates(
        self, test_client: AsyncClient, auth_headers: dict, sample_template_data: dict
    ):
        """Test getting popular templates"""
        # Create template
        await test_client.post(
            "/api/v1/templates",
            json=sample_template_data,
            headers=auth_headers,
        )

        # Get popular templates
        response = await test_client.get(
            "/api/v1/templates/popular?limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "templates" in data
        assert "total" in data
        assert isinstance(data["templates"], list)

    async def test_get_popular_templates_no_auth(self, test_client: AsyncClient):
        """Test getting popular templates without authentication fails"""
        response = await test_client.get("/api/v1/templates/popular")

        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
