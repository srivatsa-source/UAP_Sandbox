"""
UAP OAuth Module
Handles Google OAuth authentication for Gmail-based identity.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from uap.protocol import get_uap_home


# OAuth scopes - email for identity, Gemini API for LLM access
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

# Client config - users should replace with their own OAuth client
DEFAULT_CLIENT_CONFIG = {
    "installed": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "client_secret": "YOUR_CLIENT_SECRET",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8080", "urn:ietf:wg:oauth:2.0:oob"]
    }
}


def get_credentials_path() -> Path:
    """Get path to stored OAuth credentials."""
    return get_uap_home() / "credentials.json"


def get_client_secrets_path() -> Path:
    """Get path to OAuth client secrets file."""
    return get_uap_home() / "client_secrets.json"


def get_user_profile_path() -> Path:
    """Get path to cached user profile."""
    return get_uap_home() / "user_profile.json"


def save_credentials(credentials) -> Path:
    """Save OAuth credentials to disk."""
    creds_path = get_credentials_path()
    creds_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None
    }
    
    with open(creds_path, "w") as f:
        json.dump(creds_data, f, indent=2)
    
    return creds_path


def load_credentials():
    """Load OAuth credentials from disk."""
    creds_path = get_credentials_path()
    
    if not creds_path.exists():
        return None
    
    try:
        from google.oauth2.credentials import Credentials
        
        with open(creds_path, "r") as f:
            creds_data = json.load(f)
        
        credentials = Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
            scopes=creds_data.get("scopes")
        )
        
        return credentials
    except (json.JSONDecodeError, KeyError, ImportError):
        return None


def refresh_credentials(credentials):
    """Refresh expired credentials."""
    from google.auth.transport.requests import Request
    
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_credentials(credentials)
    return credentials


def get_valid_credentials():
    """Get valid credentials, refreshing if necessary."""
    credentials = load_credentials()
    
    if not credentials:
        return None
    
    if credentials.expired and credentials.refresh_token:
        try:
            credentials = refresh_credentials(credentials)
        except Exception:
            return None
    
    return credentials


def get_user_info(credentials) -> Dict[str, Any]:
    """Fetch user profile information from Google."""
    try:
        from googleapiclient.discovery import build
        
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        # Cache user profile
        profile = {
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "id": user_info.get("id"),
            "fetched_at": datetime.now().isoformat()
        }
        
        with open(get_user_profile_path(), "w") as f:
            json.dump(profile, f, indent=2)
        
        return profile
    except Exception as e:
        return {"error": str(e)}


def get_cached_user_profile() -> Optional[Dict[str, Any]]:
    """Get cached user profile without API call."""
    profile_path = get_user_profile_path()
    
    if profile_path.exists():
        try:
            with open(profile_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    
    return None


def clear_credentials() -> bool:
    """Clear stored credentials (logout)."""
    creds_path = get_credentials_path()
    profile_path = get_user_profile_path()
    
    cleared = False
    
    if creds_path.exists():
        creds_path.unlink()
        cleared = True
    
    if profile_path.exists():
        profile_path.unlink()
        cleared = True
    
    return cleared


def run_cli_oauth_flow():
    """
    Run OAuth flow for CLI authentication.
    Opens browser for user consent and handles callback.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    client_secrets_path = get_client_secrets_path()
    
    if client_secrets_path.exists():
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_path),
            scopes=SCOPES
        )
    else:
        flow = InstalledAppFlow.from_client_config(
            DEFAULT_CLIENT_CONFIG,
            scopes=SCOPES
        )
    
    # Run local server to handle OAuth callback
    credentials = flow.run_local_server(
        port=8080,
        prompt='consent',
        success_message='UAP authentication successful! You can close this window.'
    )
    
    # Save credentials
    save_credentials(credentials)
    
    return credentials


def create_web_oauth_flow(redirect_uri: str):
    """
    Create OAuth flow for web application.
    Returns authorization URL for redirect.
    """
    from google_auth_oauthlib.flow import Flow
    
    client_secrets_path = get_client_secrets_path()
    
    if client_secrets_path.exists():
        flow = Flow.from_client_secrets_file(
            str(client_secrets_path),
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    else:
        # Use web client config for Streamlit
        web_config = {
            "web": {
                "client_id": DEFAULT_CLIENT_CONFIG["installed"]["client_id"],
                "client_secret": DEFAULT_CLIENT_CONFIG["installed"]["client_secret"],
                "auth_uri": DEFAULT_CLIENT_CONFIG["installed"]["auth_uri"],
                "token_uri": DEFAULT_CLIENT_CONFIG["installed"]["token_uri"],
                "redirect_uris": [redirect_uri]
            }
        }
        flow = Flow.from_client_config(
            web_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    
    return flow


def is_authenticated() -> bool:
    """Check if user is currently authenticated."""
    credentials = get_valid_credentials()
    if credentials is None:
        return False
    return not credentials.expired


class UAPOAuth:
    """
    OAuth authentication wrapper class for UAP Protocol.
    Provides a convenient interface for authentication operations.
    """
    
    def __init__(self):
        self._credentials = None
        self._user_info = None
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return is_authenticated()
    
    def authenticate(self):
        """
        Run OAuth authentication flow.
        Returns credentials on success.
        """
        credentials = run_cli_oauth_flow()
        self._credentials = credentials
        return credentials
    
    def load_credentials(self):
        """Load existing credentials from disk."""
        credentials = get_valid_credentials()
        if credentials:
            self._credentials = credentials
        return credentials
    
    def get_user_info(self, credentials=None):
        """Get user profile information."""
        creds = credentials or self._credentials
        if creds:
            return get_user_info(creds)
        return None
    
    def get_cached_profile(self):
        """Get cached user profile without API call."""
        return get_cached_user_profile()
    
    def logout(self) -> bool:
        """Clear credentials and log out."""
        self._credentials = None
        self._user_info = None
        return clear_credentials()
    
    @property
    def credentials(self):
        """Get current credentials."""
        return self._credentials
    
    @property
    def user_info(self):
        """Get cached user info."""
        if self._user_info is None:
            self._user_info = get_cached_user_profile()
        return self._user_info
