#!/usr/bin/env python3
"""
Developer Tools for BMAD Backend

A collection of utilities for development, debugging, and testing.

Usage:
    python scripts/dev_tools.py <command> [options]

Commands:
    health          Check all service health
    db-status       Show database connection status
    redis-status    Show Redis connection status
    create-user     Create a test user
    get-token       Get JWT token for a user
    list-tasks      List recent tasks
    system-info     Show system information
    clear-cache     Clear Redis cache
    seed-templates  Seed default workflow templates
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

# Default API base URL
DEFAULT_BASE_URL = "http://localhost:8002/api/v1"


class DevTools:
    """Developer tools for BMAD backend"""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None

    async def health_check(self) -> dict:
        """Check all service health"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health", timeout=10)
                return response.json()
            except Exception as e:
                return {"status": "error", "error": str(e)}

    async def db_status(self) -> dict:
        """Get database status"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health/database", timeout=10)
                return response.json()
            except Exception as e:
                return {"status": "error", "error": str(e)}

    async def redis_status(self) -> dict:
        """Get Redis status"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health/redis", timeout=10)
                return response.json()
            except Exception as e:
                return {"status": "error", "error": str(e)}

    async def create_user(self, email: str, password: str, username: str) -> dict:
        """Create a new user"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/auth/register",
                    json={
                        "email": email,
                        "password": password,
                        "username": username
                    },
                    timeout=10
                )
                return response.json()
            except Exception as e:
                return {"status": "error", "error": str(e)}

    async def get_token(self, email: str, password: str) -> dict:
        """Get JWT token for a user"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/auth/login",
                    json={
                        "email": email,
                        "password": password
                    },
                    timeout=10
                )
                data = response.json()
                if "access_token" in data:
                    self.token = data["access_token"]
                return data
            except Exception as e:
                return {"status": "error", "error": str(e)}

    async def list_tasks(self, limit: int = 10) -> dict:
        """List recent tasks"""
        if not self.token:
            return {"error": "No token. Login first."}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/tasks",
                    params={"limit": limit},
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10
                )
                return response.json()
            except Exception as e:
                return {"status": "error", "error": str(e)}

    async def get_analytics(self) -> dict:
        """Get system analytics"""
        if not self.token:
            return {"error": "No token. Login first."}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/analytics/system",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10
                )
                return response.json()
            except Exception as e:
                return {"status": "error", "error": str(e)}


def print_health(data: dict):
    """Pretty print health check results"""
    status_color = "green" if data.get("status") == "healthy" else "red"

    table = Table(title="Service Health")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style=status_color)

    for key, value in data.items():
        if key != "status":
            color = "green" if value == "connected" else "red"
            table.add_row(key.capitalize(), f"[{color}]{value}[/{color}]")

    console.print(table)
    console.print(f"\n[bold]Overall Status:[/bold] [{status_color}]{data.get('status', 'unknown')}[/{status_color}]")


def print_db_status(data: dict):
    """Pretty print database status"""
    if "error" in data:
        console.print(f"[red]Error: {data['error']}[/red]")
        return

    panel = Panel(
        f"""[cyan]Status:[/cyan] {data.get('status', 'unknown')}
[cyan]Database:[/cyan] {data.get('database', 'unknown')}
[cyan]Version:[/cyan] {data.get('version', 'unknown')}""",
        title="Database Status",
        border_style="green" if data.get("status") == "connected" else "red"
    )
    console.print(panel)


def print_redis_status(data: dict):
    """Pretty print Redis status"""
    if "error" in data:
        console.print(f"[red]Error: {data['error']}[/red]")
        return

    panel = Panel(
        f"""[cyan]Status:[/cyan] {data.get('status', 'unknown')}
[cyan]Version:[/cyan] {data.get('redis_version', 'unknown')}
[cyan]Clients:[/cyan] {data.get('connected_clients', 0)}
[cyan]Memory:[/cyan] {data.get('used_memory', 'unknown')}
[cyan]Uptime:[/cyan] {data.get('uptime_days', 0)} days""",
        title="Redis Status",
        border_style="green" if data.get("status") == "connected" else "red"
    )
    console.print(panel)


def print_tasks(data: dict):
    """Pretty print task list"""
    if "error" in data:
        console.print(f"[red]Error: {data['error']}[/red]")
        return

    tasks = data.get("tasks", [])
    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        return

    table = Table(title=f"Tasks ({data.get('total', len(tasks))} total)")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Description", max_width=40)
    table.add_column("Status")
    table.add_column("Progress")
    table.add_column("Created")

    status_colors = {
        "pending": "yellow",
        "in_progress": "blue",
        "completed": "green",
        "failed": "red",
        "cancelled": "dim"
    }

    for task in tasks:
        status = task.get("status", "unknown")
        color = status_colors.get(status, "white")
        table.add_row(
            task.get("task_id", "")[:8] + "...",
            task.get("description", "")[:40],
            f"[{color}]{status}[/{color}]",
            f"{task.get('progress', 0)}%",
            task.get("created_at", "")[:10]
        )

    console.print(table)


def print_analytics(data: dict):
    """Pretty print system analytics"""
    if "error" in data:
        console.print(f"[red]Error: {data['error']}[/red]")
        return

    # Task stats
    tasks = data.get("tasks", {})
    console.print(Panel(
        f"""[bold]Task Statistics[/bold]
Total: {tasks.get('total_tasks', 0)}
Active: {tasks.get('active_tasks', 0)}
Pending: {tasks.get('pending_tasks', 0)}
Completion Rate: {tasks.get('completion_rate', 0):.1f}%
Failure Rate: {tasks.get('failure_rate', 0):.1f}%""",
        title="Tasks"
    ))

    # Worker stats
    workers = data.get("workers", {})
    console.print(Panel(
        f"""[bold]Worker Statistics[/bold]
Total: {workers.get('total_workers', 0)}
Online: {workers.get('online_workers', 0)}
Busy: {workers.get('busy_workers', 0)}
Idle: {workers.get('idle_workers', 0)}""",
        title="Workers"
    ))

    # System stats
    console.print(Panel(
        f"""[bold]System Metrics[/bold]
Queue Length: {data.get('queue_length', 0)}
Throughput: {data.get('throughput_per_hour', 0):.2f} tasks/hour""",
        title="System"
    ))


async def main():
    parser = argparse.ArgumentParser(
        description="BMAD Developer Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Health check
    subparsers.add_parser("health", help="Check all service health")

    # DB status
    subparsers.add_parser("db-status", help="Show database status")

    # Redis status
    subparsers.add_parser("redis-status", help="Show Redis status")

    # Create user
    create_user_parser = subparsers.add_parser("create-user", help="Create a test user")
    create_user_parser.add_argument("--email", required=True, help="User email")
    create_user_parser.add_argument("--password", required=True, help="User password")
    create_user_parser.add_argument("--username", required=True, help="Username")

    # Get token
    token_parser = subparsers.add_parser("get-token", help="Get JWT token")
    token_parser.add_argument("--email", required=True, help="User email")
    token_parser.add_argument("--password", required=True, help="User password")

    # List tasks
    tasks_parser = subparsers.add_parser("list-tasks", help="List recent tasks")
    tasks_parser.add_argument("--limit", type=int, default=10, help="Number of tasks")
    tasks_parser.add_argument("--token", required=True, help="JWT token")

    # Analytics
    analytics_parser = subparsers.add_parser("analytics", help="Show system analytics")
    analytics_parser.add_argument("--token", required=True, help="JWT token")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    tools = DevTools(base_url=args.base_url)

    console.print(f"\n[bold blue]BMAD Developer Tools[/bold blue]")
    console.print(f"[dim]Target: {args.base_url}[/dim]\n")

    if args.command == "health":
        data = await tools.health_check()
        print_health(data)

    elif args.command == "db-status":
        data = await tools.db_status()
        print_db_status(data)

    elif args.command == "redis-status":
        data = await tools.redis_status()
        print_redis_status(data)

    elif args.command == "create-user":
        data = await tools.create_user(args.email, args.password, args.username)
        if "user_id" in data:
            console.print(f"[green]User created successfully![/green]")
            console.print(f"User ID: {data['user_id']}")
        else:
            console.print(f"[red]Error: {data}[/red]")

    elif args.command == "get-token":
        data = await tools.get_token(args.email, args.password)
        if "access_token" in data:
            console.print(f"[green]Login successful![/green]")
            console.print(f"\n[bold]Access Token:[/bold]")
            console.print(f"[dim]{data['access_token']}[/dim]")
            console.print(f"\n[bold]Token Type:[/bold] {data.get('token_type', 'bearer')}")
        else:
            console.print(f"[red]Error: {data}[/red]")

    elif args.command == "list-tasks":
        tools.token = args.token
        data = await tools.list_tasks(limit=args.limit)
        print_tasks(data)

    elif args.command == "analytics":
        tools.token = args.token
        data = await tools.get_analytics()
        print_analytics(data)


if __name__ == "__main__":
    asyncio.run(main())
