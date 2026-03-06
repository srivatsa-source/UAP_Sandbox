"""
UAP Telemetry - Segment-style Analytics for Agent Interactions
Tracks events, latency, handoff success, and usage metrics.
All data is stored locally in ~/.uap/telemetry/.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from uap.protocol import get_uap_home


def _get_telemetry_dir() -> Path:
    """Get telemetry storage directory (~/.uap/telemetry)."""
    telemetry_dir = get_uap_home() / "telemetry"
    telemetry_dir.mkdir(exist_ok=True)
    return telemetry_dir


class TelemetryCollector:
    """
    Segment-style analytics collector for UAP agent interactions.
    
    Records:
    - dispatch events (agent called, latency, token estimate)
    - handoff events (from → to, reason, ACT size)
    - chain events (full chain completion, total latency)
    - error events (failures, timeouts)
    
    All data stored locally as JSONL in ~/.uap/telemetry/events-YYYY-MM-DD.jsonl
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._telemetry_dir = _get_telemetry_dir()
        self._session_id: Optional[str] = None
        self._buffer: list[dict] = []
        self._buffer_limit = 50
    
    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
    
    def _event_file(self) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._telemetry_dir / f"events-{date_str}.jsonl"
    
    def _base_event(self, event_type: str) -> dict:
        return {
            "event_id": str(uuid.uuid4())[:12],
            "event_type": event_type,
            "timestamp": self._now_iso(),
            "session_id": self._session_id,
        }
    
    def _write_event(self, event: dict):
        """Append event to buffer and flush if needed."""
        if not self.enabled:
            return
        self._buffer.append(event)
        if len(self._buffer) >= self._buffer_limit:
            self.flush()
    
    def flush(self):
        """Write buffered events to disk."""
        if not self._buffer:
            return
        filepath = self._event_file()
        with open(filepath, "a", encoding="utf-8") as f:
            for event in self._buffer:
                f.write(json.dumps(event, default=str) + "\n")
        self._buffer.clear()
    
    def set_session(self, session_id: str):
        """Associate telemetry with an ACT session."""
        self._session_id = session_id
    
    # =========================================================================
    # Event tracking methods
    # =========================================================================
    
    def track_dispatch(
        self,
        agent_id: str,
        agent_type: str,
        backend: str,
        model: str,
        latency_ms: float,
        success: bool,
        response_length: int = 0,
        error: Optional[str] = None,
    ):
        """Track an agent dispatch (call) event."""
        event = self._base_event("dispatch")
        event.update({
            "agent_id": agent_id,
            "agent_type": agent_type,
            "backend": backend,
            "model": model,
            "latency_ms": round(latency_ms, 2),
            "success": success,
            "response_length": response_length,
            "error": error,
        })
        self._write_event(event)
    
    def track_handoff(
        self,
        from_agent: str,
        to_agent: str,
        session_id: str,
        reason: str,
        act_size_bytes: int = 0,
    ):
        """Track an ACT handoff between agents."""
        event = self._base_event("handoff")
        event.update({
            "from_agent": from_agent,
            "to_agent": to_agent,
            "act_session_id": session_id,
            "reason": reason,
            "act_size_bytes": act_size_bytes,
        })
        self._write_event(event)
    
    def track_chain(
        self,
        session_id: str,
        agents: list[str],
        total_latency_ms: float,
        success: bool,
        task_preview: str = "",
    ):
        """Track a full chain completion."""
        event = self._base_event("chain_complete")
        event.update({
            "act_session_id": session_id,
            "agents": agents,
            "agent_count": len(agents),
            "total_latency_ms": round(total_latency_ms, 2),
            "success": success,
            "task_preview": task_preview[:200],
        })
        self._write_event(event)
    
    def track_error(
        self,
        agent_id: str,
        error_type: str,
        error_message: str,
        backend: Optional[str] = None,
    ):
        """Track an error event."""
        event = self._base_event("error")
        event.update({
            "agent_id": agent_id,
            "error_type": error_type,
            "error_message": error_message[:500],
            "backend": backend,
        })
        self._write_event(event)
    
    # =========================================================================
    # Timer context manager for latency tracking
    # =========================================================================
    
    class Timer:
        """Simple timer for measuring latency."""
        def __init__(self):
            self.start_time: float = 0
            self.elapsed_ms: float = 0
        
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
        
        def __exit__(self, *args):
            self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000
    
    def timer(self) -> "TelemetryCollector.Timer":
        """Create a timer for measuring operation latency."""
        return self.Timer()
    
    # =========================================================================
    # Query methods for dashboard analytics
    # =========================================================================
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 500,
    ) -> list[dict]:
        """
        Read events from disk, optionally filtered by type and date.
        
        Args:
            event_type: Filter to specific event type (dispatch, handoff, chain_complete, error)
            since: ISO date string to filter events after (e.g. "2025-01-01")
            limit: Maximum number of events to return
        """
        # Flush pending events first
        self.flush()
        
        events = []
        for filepath in sorted(self._telemetry_dir.glob("events-*.jsonl"), reverse=True):
            # Apply date filter on filename
            if since:
                file_date = filepath.stem.replace("events-", "")
                if file_date < since:
                    continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event_type and event.get("event_type") != event_type:
                        continue
                    events.append(event)
                    if len(events) >= limit:
                        return events
        
        return events
    
    def get_summary(self, since: Optional[str] = None) -> dict:
        """
        Get aggregated telemetry summary for the dashboard.
        
        Returns:
            Dict with counts, avg latency, success rates, top agents, etc.
        """
        events = self.get_events(since=since, limit=10000)
        
        dispatches = [e for e in events if e["event_type"] == "dispatch"]
        handoffs = [e for e in events if e["event_type"] == "handoff"]
        chains = [e for e in events if e["event_type"] == "chain_complete"]
        errors = [e for e in events if e["event_type"] == "error"]
        
        # Compute stats
        total_dispatches = len(dispatches)
        successful = [d for d in dispatches if d.get("success")]
        latencies = [d["latency_ms"] for d in dispatches if "latency_ms" in d]
        
        # Agent frequency
        agent_counts: dict[str, int] = {}
        backend_counts: dict[str, int] = {}
        for d in dispatches:
            agent_counts[d.get("agent_id", "unknown")] = agent_counts.get(d.get("agent_id", "unknown"), 0) + 1
            backend_counts[d.get("backend", "unknown")] = backend_counts.get(d.get("backend", "unknown"), 0) + 1
        
        return {
            "total_dispatches": total_dispatches,
            "total_handoffs": len(handoffs),
            "total_chains": len(chains),
            "total_errors": len(errors),
            "success_rate": len(successful) / total_dispatches if total_dispatches else 0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            "agent_counts": agent_counts,
            "backend_counts": backend_counts,
            "unique_sessions": len(set(e.get("act_session_id") or e.get("session_id", "") for e in events)),
        }
    
    def __del__(self):
        """Flush remaining events on cleanup."""
        try:
            self.flush()
        except Exception:
            pass


# Module-level singleton for convenience
_default_collector: Optional[TelemetryCollector] = None


def get_telemetry() -> TelemetryCollector:
    """Get the default telemetry collector singleton."""
    global _default_collector
    if _default_collector is None:
        _default_collector = TelemetryCollector()
    return _default_collector
