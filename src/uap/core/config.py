"""
UAP Core Config
Global configuration and environment access.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


def get_uap_home() -> Path:
    """Get the base directory for UAP storage."""
    home = Path(os.getenv("UAP_HOME", Path.home() / ".uap"))
    home.mkdir(parents=True, exist_ok=True)
    return home


def get_config_path() -> Path:
    """Get path to config.yaml."""
    return get_uap_home() / "config.yaml"


def get_config() -> dict:
    """Load configuration from disk."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def set_config(key: str, value: str) -> None:
    """Set a configuration value."""
    config = get_config()
    config[key] = value
    
    with open(get_config_path(), "w") as f:
        yaml.safe_dump(config, f)


def _load_env_if_present() -> None:
    """Load .env file if it exists in current directory."""
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)


_load_env_if_present()


def get_config_value(key: str, default: str = None) -> str:
    """Get a configuration value, falling back to env vars and then default."""
    config = get_config()
    return config.get(key, os.getenv(key.upper(), default))
