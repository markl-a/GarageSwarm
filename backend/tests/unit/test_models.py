"""Unit tests for database models"""

import pytest
from uuid import UUID
from datetime import datetime

from src.models.user import User
from src.models.worker import Worker
from src.models.task import Task
from src.models.subtask import Subtask


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_user(db_session, sample_user_data):
    """Test creating a user"""
    user = User(**sample_user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.user_id is not None
    assert isinstance(user.user_id, UUID)
    assert user.username == sample_user_data["username"]
    assert user.email == sample_user_data["email"]
    assert isinstance(user.created_at, datetime)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_worker(db_session, sample_worker_data):
    """Test creating a worker"""
    worker = Worker(**sample_worker_data)
    db_session.add(worker)
    await db_session.commit()
    await db_session.refresh(worker)

    assert worker.worker_id is not None
    assert isinstance(worker.worker_id, UUID)
    assert worker.machine_id == sample_worker_data["machine_id"]
    assert worker.machine_name == sample_worker_data["machine_name"]
    assert worker.status == "offline"  # Default status
    assert worker.system_info == sample_worker_data["system_info"]
    assert worker.tools == sample_worker_data["tools"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task(db_session, sample_user_data, sample_task_data):
    """Test creating a task"""
    # First create a user
    user = User(**sample_user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create task
    task = Task(
        user_id=user.user_id,
        **sample_task_data
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    assert task.task_id is not None
    assert isinstance(task.task_id, UUID)
    assert task.user_id == user.user_id
    assert task.description == sample_task_data["description"]
    assert task.status == "pending"  # Default status
    assert task.progress == 0  # Default progress


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_subtask(db_session, sample_user_data, sample_task_data):
    """Test creating a subtask"""
    # Create user and task
    user = User(**sample_user_data)
    db_session.add(user)
    await db_session.commit()

    task = Task(user_id=user.user_id, **sample_task_data)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Create subtask
    subtask = Subtask(
        task_id=task.task_id,
        name="Test Subtask",
        description="Test subtask description",
        recommended_tool="claude_code"
    )
    db_session.add(subtask)
    await db_session.commit()
    await db_session.refresh(subtask)

    assert subtask.subtask_id is not None
    assert isinstance(subtask.subtask_id, UUID)
    assert subtask.task_id == task.task_id
    assert subtask.status == "pending"  # Default status
    assert subtask.progress == 0  # Default progress


@pytest.mark.unit
@pytest.mark.asyncio
async def test_worker_status_update(db_session, sample_worker_data):
    """Test updating worker status"""
    worker = Worker(**sample_worker_data)
    db_session.add(worker)
    await db_session.commit()

    # Update status
    worker.status = "online"
    worker.cpu_percent = 45.5
    worker.memory_percent = 60.2
    worker.disk_percent = 75.0

    await db_session.commit()
    await db_session.refresh(worker)

    assert worker.status == "online"
    assert worker.cpu_percent == 45.5
    assert worker.memory_percent == 60.2
    assert worker.disk_percent == 75.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_progress_update(db_session, sample_user_data, sample_task_data):
    """Test updating task progress"""
    user = User(**sample_user_data)
    db_session.add(user)
    await db_session.commit()

    task = Task(user_id=user.user_id, **sample_task_data)
    db_session.add(task)
    await db_session.commit()

    # Update progress
    task.status = "in_progress"
    task.progress = 50

    await db_session.commit()
    await db_session.refresh(task)

    assert task.status == "in_progress"
    assert task.progress == 50
