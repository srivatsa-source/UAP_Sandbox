"""
UAP Credential Vault
Secure storage for agent API keys tied to user identity.
Uses OS-native keyring for credentials.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import keyring

from uap.core.config import get_uap_home


def get_vault_path() -> Path:
    """Get path to credential vault directory."""
    vault_dir = get_uap_home() / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    return vault_dir


def _get_user_vault_path(user_identifier: str) -> Path:
    """Get vault path for specific user via hashed identity."""
    email_hash = hashlib.sha256(user_identifier.lower().encode()).hexdigest()[:16]
    user_dir = get_vault_path() / email_hash
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def _get_metadata_file(user_identifier: str) -> Path:
    return _get_user_vault_path(user_identifier) / "metadata.json"

def _load_metadata(user_identifier: str) -> dict:
    meta_file = _get_metadata_file(user_identifier)
    if meta_file.exists():
        try:
            with open(meta_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_metadata(user_identifier: str, metadata: dict):
    meta_file = _get_metadata_file(user_identifier)
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)

def store_credential(user_identifier: str, provider: str, api_key: str, metadata: Dict[str, Any] = None) -> bool:
    """
    Store an API key for a provider securely using keyring.
    """
    try:
        service_name = f"uap-{provider}"
        keyring.set_password(service_name, user_identifier, api_key)
        
        all_meta = _load_metadata(user_identifier)
        all_meta[provider] = {
            "linked_at": datetime.now().isoformat(),
            "verified": True,
            "metadata": metadata or {}
        }
        _save_metadata(user_identifier, all_meta)

        return True
    except Exception as e:
        print(f"Error storing credential for {provider}: {e}")
        return False


def get_credential(user_identifier: str, provider: str) -> Optional[str]:
    """Retrieve an API key for a provider."""
    try:
        service_name = f"uap-{provider}"
        return keyring.get_password(service_name, user_identifier)
    except Exception as e:
        print(f"Error retrieving credential for {provider}: {e}")
        return None


def get_linked_agents(user_identifier: str) -> Dict[str, Dict[str, Any]]:
    """Get all correctly formatted agents linked to identity."""
    providers = {
        "gemini": {"name": "Gemini", "provider": "Google", "oauth_based": True},
        "openai": {"name": "GPT-4", "provider": "OpenAI", "oauth_based": False},
        "anthropic": {"name": "Claude Desktop", "provider": "Anthropic", "oauth_based": False},
        "ollama": {"name": "Ollama", "provider": "Ollama", "oauth_based": False},
    }

    all_meta = _load_metadata(user_identifier)

    result = {}
    for provider_id, info in providers.items():
        agent_info = {
            "name": info["name"],
            "provider": info["provider"],
            "oauth_based": info["oauth_based"],
            "linked": False,
            "linked_at": None,
            "verified": False
        }

        if provider_id == "gemini":
            oauth_creds = get_uap_home() / "credentials.json"
            if oauth_creds.exists():
                agent_info["linked"] = True
                agent_info["verified"] = True
                agent_info["linked_at"] = datetime.fromtimestamp(oauth_creds.stat().st_mtime).isoformat()
        else:
            try:
                service_name = f"uap-{provider_id}"
                has_cred = keyring.get_password(service_name, user_identifier) is not None
                if has_cred:
                    agent_info["linked"] = True
                    p_meta = all_meta.get(provider_id, {})
                    agent_info["linked_at"] = p_meta.get("linked_at")
                    agent_info["verified"] = p_meta.get("verified", False)
            except Exception:
                pass

        result[provider_id] = agent_info

    return result


def unlink_agent(user_identifier: str, provider: str) -> bool:
    """Remove a linked agent."""
    try:
        service_name = f"uap-{provider}"
        try:
            keyring.delete_password(service_name, user_identifier)
        except keyring.errors.PasswordDeleteError:
            pass # Maybe it didn't exist
            
        all_meta = _load_metadata(user_identifier)
        if provider in all_meta:
            del all_meta[provider]
            _save_metadata(user_identifier, all_meta)
            
        return True
    except Exception as e:
        print(f"Error unlinking agent: {e}")
        return False
