# UAP OAuth Integration

This guide explains how to use Gmail OAuth authentication with UAP.

## Prerequisites

1. A Google Cloud Project with OAuth 2.0 credentials
2. Python 3.10+ with the UAP package installed

## Setup

### 1. Create Google Cloud OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - **Google+ API** (for user profile info)
   - **Generative Language API** (for Gemini, if using)
4. Go to **Credentials** → **Create Credentials** → **OAuth Client ID**
5. Select **Desktop app** for CLI usage
6. Download the credentials or note the Client ID and Secret

### 2. Configure UAP with your credentials

Run the interactive setup:

```bash
uap-cli setup
```

Or manually create `~/.uap/client_secrets.json`:

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
uap-cli login
```

This opens a browser window for Google OAuth consent. After authentication, credentials are saved to `~/.uap/credentials.json`.

### Check Current User

```bash
uap-cli whoami
```

### Start a New Task

```bash
uap-cli new "Build a REST API with FastAPI" --agents planner,coder
```

### Auto-chain Agents

```bash
uap-cli new "Create a CLI tool" --agents planner,coder,reviewer --auto
```

### View Sessions

```bash
uap-cli sessions
```

### Check Status

```bash
uap-cli status
```

### Logout

```bash
uap-cli logout
```

## Web Portal

### Run the OAuth-enabled Streamlit App

```bash
streamlit run uap-segment-dashboard/src/oauth_app.py
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

## Files Created

| File | Purpose |
|------|---------|
| `src/uap/oauth.py` | OAuth authentication module |
| `src/uap/uap_cli.py` | Click-based CLI tool |
| `uap-segment-dashboard/src/oauth_app.py` | Streamlit OAuth web portal |
| `requirements-oauth.txt` | OAuth-specific dependencies |

## Security Notes

- Credentials are stored locally in `~/.uap/credentials.json`
- Refresh tokens enable persistent sessions
- Use `uap-cli logout` to clear credentials
- Never commit `credentials.json` or `client_secrets.json` to version control
