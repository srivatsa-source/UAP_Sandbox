"""
UAP Credential Vault
Secure storage for agent API keys tied to user Gmail identity.
Keys are encrypted and stored per-user.
"""

import json
import os
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from uap.protocol import get_uap_home


def get_vault_path() -> Path:
    """Get path to credential vault directory."""
    vault_dir = get_uap_home() / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    return vault_dir


def _get_user_vault_path(user_email: str) -> Path:
    """Get vault path for specific user."""
    # Hash email for filesystem-safe directory name
    email_hash = hashlib.sha256(user_email.lower().encode()).hexdigest()[:16]
    user_dir = get_vault_path() / email_hash
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _simple_encrypt(data: str, user_email: str) -> str:
    """Simple obfuscation - in production use proper encryption (Fernet, KMS)."""
    # XOR with email-derived key (NOT secure - placeholder for real encryption)
    key = hashlib.sha256(user_email.encode()).digest()
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data.encode()))
    return base64.b64encode(encrypted).decode()


def _simple_decrypt(encrypted_data: str, user_email: str) -> str:
    """Decrypt data."""
    key = hashlib.sha256(user_email.encode()).digest()
    encrypted = base64.b64decode(encrypted_data.encode())
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(encrypted))
    return decrypted.decode()


def store_credential(user_email: str, provider: str, api_key: str, metadata: Dict[str, Any] = None) -> bool:
    """
    Store an API key for a provider, linked to user's email identity.
    
    Args:
        user_email: Gmail address (identity anchor)
        provider: Provider name (openai, anthropic, mistral, groq)
        api_key: The API key to store
        metadata: Optional metadata (linked_at, verified, etc.)
    
    Returns:
        True if stored successfully
    """
    try:
        user_vault = _get_user_vault_path(user_email)
        cred_file = user_vault / f"{provider}.json"
        
        cred_data = {
            "provider": provider,
            "encrypted_key": _simple_encrypt(api_key, user_email),
            "linked_at": datetime.now().isoformat(),
            "user_email": user_email,
            "verified": True,
            "metadata": metadata or {}
        }
        
        with open(cred_file, "w") as f:
            json.dump(cred_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error storing credential: {e}")
        return False


def get_credential(user_email: str, provider: str) -> Optional[str]:
    """
    Retrieve an API key for a provider.
    
    Args:
        user_email: Gmail address (identity anchor)
        provider: Provider name
    
    Returns:
        Decrypted API key or None if not found
    """
    try:
        user_vault = _get_user_vault_path(user_email)
        cred_file = user_vault / f"{provider}.json"
        
        if not cred_file.exists():
            return None
        
        with open(cred_file, "r") as f:
            cred_data = json.load(f)
        
        return _simple_decrypt(cred_data["encrypted_key"], user_email)
    except Exception as e:
        print(f"Error retrieving credential: {e}")
        return None


def get_linked_agents(user_email: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all agents linked to a user's identity.
    
    Returns:
        Dict of provider -> {linked: bool, linked_at: str, verified: bool}
    """
    # All possible providers
    providers = {
        "gemini": {"name": "Gemini", "provider": "Google", "oauth_based": True},
        "openai": {"name": "GPT-4", "provider": "OpenAI", "oauth_based": False},
        "anthropic": {"name": "Claude", "provider": "Anthropic", "oauth_based": False},
        "mistral": {"name": "Mistral", "provider": "Mistral AI", "oauth_based": False},
        "groq": {"name": "Groq", "provider": "Groq", "oauth_based": False},
    }
    
    user_vault = _get_user_vault_path(user_email)
    
    result = {}
    for provider_id, info in providers.items():
        cred_file = user_vault / f"{provider_id}.json"
        
        agent_info = {
            "name": info["name"],
            "provider": info["provider"],
            "oauth_based": info["oauth_based"],
            "linked": False,
            "linked_at": None,
            "verified": False
        }
        
        if provider_id == "gemini":
            # Gemini is linked via OAuth, check OAuth credentials
            oauth_creds = get_uap_home() / "credentials.json"
            if oauth_creds.exists():
                agent_info["linked"] = True
                agent_info["verified"] = True
                agent_info["linked_at"] = datetime.fromtimestamp(oauth_creds.stat().st_mtime).isoformat()
        elif cred_file.exists():
            try:
                with open(cred_file, "r") as f:
                    cred_data = json.load(f)
                agent_info["linked"] = True
                agent_info["linked_at"] = cred_data.get("linked_at")
                agent_info["verified"] = cred_data.get("verified", False)
            except:
                pass
        
        result[provider_id] = agent_info
    
    return result


def unlink_agent(user_email: str, provider: str) -> bool:
    """Remove a linked agent."""
    try:
        user_vault = _get_user_vault_path(user_email)
        cred_file = user_vault / f"{provider}.json"
        
        if cred_file.exists():
            cred_file.unlink()
            return True
        return False
    except Exception as e:
        print(f"Error unlinking agent: {e}")
        return False


def generate_link_token(user_email: str, provider: str) -> str:
    """
    Generate a one-time token for email verification linking.
    
    In production, this would be stored in a database with expiry.
    """
    token_data = f"{user_email}:{provider}:{datetime.now().isoformat()}"
    return base64.urlsafe_b64encode(hashlib.sha256(token_data.encode()).digest()).decode()[:32]


def verify_link_token(token: str, user_email: str, provider: str) -> bool:
    """
    Verify a link token (simplified - in production check against stored tokens).
    """
    # In production: check token against database, verify expiry
    # For now, accept any token for the demo
    return len(token) > 0
