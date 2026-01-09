"""Configuration management for worker agent"""

import os
import re
from pathlib import Path
from typing import Any, Dict
import yaml
import structlog

logger = structlog.get_logger()


def substitute_env_vars(value: Any) -> Any:
    """Recursively substitute environment variables in config values

    Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax

    Args:
        value: Config value (can be str, dict, list, or other)

    Returns:
        Value with environment variables substituted
    """
    if isinstance(value, str):
        # Pattern: ${VAR_NAME} or ${VAR_NAME:default}
        pattern = r'\$\{([^:}]+)(?::([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default_value)

        return re.sub(pattern, replacer, value)

    elif isinstance(value, dict):
        return {k: substitute_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [substitute_env_vars(item) for item in value]

    else:
        return value


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file

    Args:
        config_path: Path to config YAML file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    logger.info("Loading configuration", config_path=config_path)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Substitute environment variables
    config = substitute_env_vars(config)

    # Validate required fields
    validate_config(config)

    logger.info("Configuration loaded successfully")
    return config


def validate_config(config: dict):
    """Validate configuration structure

    Args:
        config: Configuration dictionary

    Raises:
        ValueError: If required fields are missing or invalid
    """
    required_fields = ["backend_url", "machine_name"]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")

    # Validate backend_url format
    if not config["backend_url"].startswith(("http://", "https://")):
        raise ValueError("backend_url must start with http:// or https://")

    # Validate api_key - warn if not set (required for heartbeat/websocket, but not for registration)
    api_key = config.get("api_key", "")
    if not api_key or api_key.strip() == "":
        logger.warning(
            "api_key not configured. Worker can register but heartbeat/websocket will fail. "
            "Set WORKER_API_KEY environment variable or configure in agent.yaml after registration."
        )
        config["api_key"] = ""  # Ensure empty string, not None

    # Set defaults
    if "heartbeat_interval" not in config:
        config["heartbeat_interval"] = 30
        logger.info("Using default heartbeat_interval", value=30)

    if "tools" not in config:
        config["tools"] = []
        logger.warning("No tools configured")

    if "resource_monitoring" not in config:
        config["resource_monitoring"] = {
            "cpu_threshold": 90,
            "memory_threshold": 85,
            "disk_threshold": 90
        }
        logger.info("Using default resource thresholds")


def get_machine_id_path() -> Path:
    """Get path to machine ID file

    Returns:
        Path to machine ID file in home directory
    """
    return Path.home() / ".multi_agent_worker_id"


def load_or_create_machine_id() -> str:
    """Load existing machine ID or create a new one

    Priority order:
    1. MACHINE_ID environment variable (for Docker/container deployments)
    2. Existing file (~/.multi_agent_worker_id)
    3. Generate new UUID and save to file

    Returns:
        Machine ID string (UUID format)
    """
    import uuid

    # Check environment variable first (for Docker deployments)
    env_machine_id = os.environ.get("MACHINE_ID", "").strip()
    if env_machine_id:
        logger.info("Using machine ID from environment", machine_id=env_machine_id)
        return env_machine_id

    # Check existing file
    machine_id_file = get_machine_id_path()

    if machine_id_file.exists():
        machine_id = machine_id_file.read_text().strip()
        logger.info("Loaded existing machine ID", machine_id=machine_id)
        return machine_id
    else:
        machine_id = str(uuid.uuid4())
        machine_id_file.write_text(machine_id)
        logger.info("Created new machine ID", machine_id=machine_id)
        return machine_id


def save_config(config: dict, config_path: str):
    """Save configuration to YAML file

    Args:
        config: Configuration dictionary
        config_path: Path to save config file

    Raises:
        IOError: If file cannot be written
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False)

    logger.info("Configuration saved", config_path=config_path)
