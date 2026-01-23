"""
UAP Configuration Management
Handles user config stored in ~/.uap/config.yaml
"""

import os
from pathlib import Path
from typing import Any, Optional
import yaml


def get_uap_home() -> Path:
    """Get UAP home directory (~/.uap)"""
    uap_home = Path.home() / ".uap"
    uap_home.mkdir(exist_ok=True)
    return uap_home


def get_config_path() -> Path:
    """Get config file path."""
    return get_uap_home() / "config.yaml"


def get_config() -> dict:
    """Load configuration from ~/.uap/config.yaml"""
    config_path = get_config_path()
    
    # Default config
    config = {
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "google_api_key": os.getenv("GOOGLE_API_KEY") or os.getenv("UAP_GEMINI_KEY", ""),
        "ollama_url": "http://localhost:11434",
        "default_backend": "groq",
        "default_model": "llama-3.3-70b-versatile",
    }
    
    # Load from file if exists
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                file_config = yaml.safe_load(f) or {}
                config.update(file_config)
        except yaml.YAMLError:
            pass
    
    # Environment variables override file config
    if os.getenv("GROQ_API_KEY"):
        config["groq_api_key"] = os.getenv("GROQ_API_KEY")
    if os.getenv("GOOGLE_API_KEY") or os.getenv("UAP_GEMINI_KEY"):
        config["google_api_key"] = os.getenv("GOOGLE_API_KEY") or os.getenv("UAP_GEMINI_KEY")
    
    return config


def set_config(key: str, value: Any) -> None:
    """Set a configuration value."""
    config_path = get_config_path()
    
    # Load existing config
    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            config = {}
    
    # Update value
    config[key] = value
    
    # Save
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a specific configuration value."""
    config = get_config()
    return config.get(key, default)


def list_config() -> dict:
    """List all configuration values (masking secrets)."""
    config = get_config()
    
    # Mask sensitive values
    masked = {}
    for key, value in config.items():
        if "key" in key.lower() or "secret" in key.lower() or "password" in key.lower():
            if value:
                masked[key] = value[:8] + "..." + value[-4:] if len(str(value)) > 12 else "***"
            else:
                masked[key] = "(not set)"
        else:
            masked[key] = value
    
    return masked


def init_config() -> Path:
    """Initialize default config file."""
    config_path = get_config_path()
    
    if not config_path.exists():
        default_config = {
            "groq_api_key": "",
            "ollama_url": "http://localhost:11434",
            "default_backend": "groq",
            "default_model": "llama-3.1-8b-instant",
        }
        
        with open(config_path, "w") as f:
            yaml.safe_dump(default_config, f, default_flow_style=False)
            f.write("\n# Add your API keys above\n")
            f.write("# Example: groq_api_key: gsk_xxxx\n")
    
    return config_path
