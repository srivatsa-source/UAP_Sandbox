# UAP OAuth Integration

Google OAuth integration for user identity and Gemini authentication.

## Prerequisites

1. A Google Cloud Project with OAuth 2.0 credentials
2. Python 3.10+ with the UAP package installed

## Setup

### 1. Create Google Cloud OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project  
3. Enable **Google+ API** and **Generative Language API** (for Gemini)
4. Go to **Credentials** → **Create Credentials** → **OAuth Client ID**
5. Select **Desktop app**
6. Download the credentials or note the Client ID and Secret

### 2. Configure UAP

Run the interactive setup:

```bash
uap-run --setup
```

Or manually place `client_secrets.json` at `~/.uap/client_secrets.json`:

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost:8080"]
  }
}
```

## CLI Usage

### Login

```bash
uap auth login
```

Opens a browser for Google OAuth consent. Credentials are saved to `~/.uap/credentials.json`.

### Check Current User

```bash
uap auth whoami
```

### Logout

```bash
uap auth logout
```

### Start a Task

```bash
uap new "Build a REST API with FastAPI" --agents planner,coder --auto
```

## Web Portal

Run the OAuth-enabled Streamlit dashboard:

```bash
uap-dashboard
# or
streamlit run src/uap/dashboard/oauth_app.py
```

The portal will:
1. Show a "Connect Google Account" button
2. Redirect to Google for OAuth consent
3. Display the Agent State Packet for authenticated users
4. Allow chat-based task creation with agents

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   CLI/Web    │────▶│    OAuth     │────▶│   Gemini     │
│   Frontend   │     │   Module     │     │   Backend    │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│  Dispatcher  │◀───▶│    State     │
│   (Router)   │     │   Manager    │
└──────────────┘     └──────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `src/uap/oauth.py` | OAuth authentication module |
| `src/uap/cli.py` | Typer CLI (`uap auth login/whoami/logout`) |
| `src/uap/dashboard/oauth_app.py` | Streamlit OAuth web portal |
| `src/uap/vault.py` | Fernet-encrypted secret storage |

## Security Notes

- Credentials are stored locally in `~/.uap/credentials.json`
- API keys are encrypted at rest via the Fernet vault (`~/.uap/vault.enc`)
- Refresh tokens enable persistent sessions
- Use `uap auth logout` to clear credentials
- Never commit `credentials.json` or `client_secrets.json` to version control
