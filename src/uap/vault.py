"""
UAP Credential Vault
Secure storage for agent API keys tied to user Gmail identity.
Keys are encrypted using PBKDF2-derived Fernet keys and stored per-user.
"""

import json
import os
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from uap.protocol import get_uap_home


# Vault format version — used to detect and migrate legacy XOR data
_VAULT_FORMAT_VERSION = 2
_KDF_ITERATIONS = 480_000  # OWASP recommended minimum for PBKDF2-SHA256


def get_vault_path() -> Path:
    """Get path to credential vault directory."""
    vault_dir = get_uap_home() / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    return vault_dir


def _get_user_vault_path(user_email: str) -> Path:
    """Get vault path for specific user."""
    email_hash = hashlib.sha256(user_email.lower().encode()).hexdigest()[:16]
    user_dir = get_vault_path() / email_hash
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _derive_fernet_key(user_email: str, salt: bytes) -> bytes:
    """Derive a Fernet key from the user's email and a random salt via PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(user_email.encode()))


def _fernet_encrypt(data: str, user_email: str) -> dict:
    """Encrypt data with PBKDF2+Fernet. Returns dict with salt and ciphertext."""
    salt = os.urandom(16)
    key = _derive_fernet_key(user_email, salt)
    token = Fernet(key).encrypt(data.encode())
    return {
        "salt": base64.b64encode(salt).decode(),
        "ciphertext": token.decode(),
    }


def _fernet_decrypt(encrypted: dict, user_email: str) -> str:
    """Decrypt a Fernet-encrypted payload."""
    salt = base64.b64decode(encrypted["salt"])
    key = _derive_fernet_key(user_email, salt)
    return Fernet(key).decrypt(encrypted["ciphertext"].encode()).decode()


# ---------------------------------------------------------------------------
# Legacy XOR helpers (kept only for migration of old vault files)
# ---------------------------------------------------------------------------

def _legacy_xor_decrypt(encrypted_data: str, user_email: str) -> str:
    """Decrypt data stored with the old XOR scheme (vault format v1)."""
    key = hashlib.sha256(user_email.encode()).digest()
    encrypted = base64.b64decode(encrypted_data.encode())
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(encrypted))
    return decrypted.decode()


def _is_legacy_format(cred_data: dict) -> bool:
    """Check whether a credential file uses the old XOR format."""
    return cred_data.get("vault_version", 1) < _VAULT_FORMAT_VERSION


def _migrate_credential(user_email: str, provider: str, cred_data: dict) -> Optional[dict]:
    """
    Migrate a legacy XOR-encrypted credential to Fernet.
    Returns the new cred_data dict, or None on failure.
    """
    try:
        plaintext = _legacy_xor_decrypt(cred_data["encrypted_key"], user_email)
        enc = _fernet_encrypt(plaintext, user_email)
        cred_data["encrypted_key"] = enc
        cred_data["vault_version"] = _VAULT_FORMAT_VERSION
        return cred_data
    except Exception:
        return None


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
        
        enc = _fernet_encrypt(api_key, user_email)
        cred_data = {
            "provider": provider,
            "encrypted_key": enc,
            "vault_version": _VAULT_FORMAT_VERSION,
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
        
        # Auto-migrate legacy XOR format to Fernet
        if _is_legacy_format(cred_data):
            migrated = _migrate_credential(user_email, provider, cred_data)
            if migrated:
                with open(cred_file, "w") as f:
                    json.dump(migrated, f, indent=2)
                cred_data = migrated
            else:
                return None
        
        return _fernet_decrypt(cred_data["encrypted_key"], user_email)
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
            except Exception:
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
