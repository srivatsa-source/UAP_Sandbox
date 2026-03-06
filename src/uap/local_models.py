"""
UAP Local Model Manager
Discovers, monitors, and routes to local LLM backends:
  - Ollama   (localhost:11434)
  - LM Studio (localhost:1234)  — OpenAI-compatible
  - llama.cpp (localhost:8080)  — native /completion endpoint
  - vLLM      (localhost:8000)  — OpenAI-compatible
"""

import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from uap.config import get_config

# -------------------------------------------------------------------
# Backend descriptors
# -------------------------------------------------------------------

BACKENDS = {
    "ollama": {
        "name": "Ollama",
        "default_url": "http://localhost:11434",
        "config_key": "ollama_url",
        "health_path": "/api/tags",
        "models_path": "/api/tags",
        "api_style": "ollama",
    },
    "lmstudio": {
        "name": "LM Studio",
        "default_url": "http://localhost:1234",
        "config_key": "lmstudio_url",
        "health_path": "/v1/models",
        "models_path": "/v1/models",
        "api_style": "openai",
    },
    "llamacpp": {
        "name": "llama.cpp",
        "default_url": "http://localhost:8080",
        "config_key": "llamacpp_url",
        "health_path": "/health",
        "models_path": None,
        "api_style": "llamacpp",
    },
    "vllm": {
        "name": "vLLM",
        "default_url": "http://localhost:8000",
        "config_key": "vllm_url",
        "health_path": "/v1/models",
        "models_path": "/v1/models",
        "api_style": "openai",
    },
}


@dataclass
class BackendStatus:
    """Health-check result for a single local backend."""
    backend: str
    name: str
    url: str
    online: bool = False
    latency_ms: float = 0.0
    models: list[str] = field(default_factory=list)
    error: Optional[str] = None


class LocalModelManager:
    """Discover, probe, and list local LLM backends."""

    def __init__(self):
        self._config = get_config()

    def _base_url(self, backend_id: str) -> str:
        info = BACKENDS[backend_id]
        return self._config.get(info["config_key"], info["default_url"]).rstrip("/")

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self, backend_id: str) -> BackendStatus:
        """Probe a single backend and return its status."""
        if backend_id not in BACKENDS:
            return BackendStatus(
                backend=backend_id, name=backend_id, url="",
                error=f"Unknown backend: {backend_id}",
            )

        info = BACKENDS[backend_id]
        url = self._base_url(backend_id)
        status = BackendStatus(backend=backend_id, name=info["name"], url=url)

        try:
            start = time.perf_counter()
            resp = requests.get(f"{url}{info['health_path']}", timeout=3)
            status.latency_ms = (time.perf_counter() - start) * 1000
            resp.raise_for_status()
            status.online = True
        except Exception as e:
            status.error = str(e)

        return status

    # ------------------------------------------------------------------
    # Model listing
    # ------------------------------------------------------------------

    def list_models(self, backend_id: str) -> list[str]:
        """Return model names available on *backend_id*."""
        if backend_id not in BACKENDS:
            return []

        info = BACKENDS[backend_id]
        url = self._base_url(backend_id)

        if info["models_path"] is None:
            # llama.cpp loads one model at a time; no model list endpoint
            hc = self.health_check(backend_id)
            return ["(loaded model)"] if hc.online else []

        try:
            resp = requests.get(f"{url}{info['models_path']}", timeout=5)
            resp.raise_for_status()
            data = resp.json()

            if info["api_style"] == "ollama":
                return [m["name"] for m in data.get("models", [])]
            else:
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Discovery / aggregate
    # ------------------------------------------------------------------

    def discover(self) -> list[BackendStatus]:
        """Probe all known backends and return their status."""
        results = []
        for bid in BACKENDS:
            st = self.health_check(bid)
            if st.online:
                st.models = self.list_models(bid)
            results.append(st)
        return results

    def get_status(self) -> dict:
        """Return a dashboard-friendly dict of all backend statuses."""
        statuses = self.discover()
        return {
            "backends": {
                s.backend: {
                    "name": s.name,
                    "url": s.url,
                    "online": s.online,
                    "latency_ms": round(s.latency_ms, 1),
                    "models": s.models,
                    "error": s.error,
                }
                for s in statuses
            },
            "online_count": sum(1 for s in statuses if s.online),
            "total_models": sum(len(s.models) for s in statuses),
        }

    def monitor(self) -> dict:
        """Alias for get_status() — kept for API consistency."""
        return self.get_status()
