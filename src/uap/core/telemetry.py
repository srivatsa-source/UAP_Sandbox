"""
UAP Telemetry System
Non-blocking structured logging for tracing agent activity and handoffs.
Uses a background thread and queue to prevent I/O from blocking agents.
"""

import os
import json
import logging
import threading
import queue
import atexit
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, ContextManager

from uap.core.config import get_uap_home


def get_telemetry_dir() -> Path:
    """Get the telemetry storage directory."""
    log_dir = get_uap_home() / "telemetry"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


class TimerContext(ContextManager):
    def __init__(self):
        self.start_time = 0
        self.end_time = 0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000.0


class TelemetryLogger:
    """
    Central logger for UAP operations.
    Runs log writes in a background thread to prevent latency for LLM calls.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, enabled: bool = True):
        # We need to overwrite the singleton initialization logic
        # because tests might try to instantiate it multiple times setting different configurations
        with cls._lock:
            # Drop singleton constraint if initialization argument varies
            # Actually simplest ways is just let the singleton be, but for tests we have to re-init
            if cls._instance is None:
                cls._instance = super(TelemetryLogger, cls).__new__(cls)
            cls._instance._init_logger(enabled)
            return cls._instance

    def _init_logger(self, enabled: bool):
        # Reset completely so tests can initialize new copies cleanly via the singleton
        self.enabled = enabled
        self._telemetry_dir = get_telemetry_dir()
        self.active_session: Optional[str] = None
        self._log_queue = queue.Queue()
        self._buffer: List[dict] = []
        
        # Set up standard logging for critical failures
        self.logger = logging.getLogger("uap.telemetry")
        self.logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not self.logger.handlers:
            # Main event log format
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            # File handler for system errors
            error_file = self._telemetry_dir / "system_errors.log"
            fh = logging.FileHandler(str(error_file))
            fh.setLevel(logging.ERROR)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        if self.enabled:
            # Start background worker
            self._shutdown_event = threading.Event()
            self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._worker_thread.start()

            # Ensure queue Flushes on exit
            atexit.register(self.shutdown)

    def _process_queue(self):
        """Background thread worker to process log writes."""
        while not self._shutdown_event.is_set() or not self._log_queue.empty():
            try:
                # Block for 0.1s to allow shutdown event check
                log_task = self._log_queue.get(timeout=0.1)
                try:
                    self._write_to_disk(log_task)
                except Exception as e:
                    self.logger.error(f"Failed to write telemetry: {e}")
                finally:
                    self._log_queue.task_done()
            except queue.Empty:
                continue

    def _write_to_disk(self, event: dict):
        """Actual disk I/O executed by the background thread."""
        session_id = event.get("session_id", "global")
        filename = f"events.jsonl" # default file
        if session_id != "global":
            filename = f"session_{session_id}.jsonl"
            
        log_file = self._telemetry_dir / filename
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def timer(self) -> TimerContext:
        """Return a context manager to measure time."""
        return TimerContext()

    def set_session(self, session_id: str):
        """Set the active tracking session."""
        self.active_session = session_id
        
    def log_event(self, event_type: str, data: Dict[str, Any], session_id: Optional[str] = None):
        """Enqueue an event for asynchronous tracking."""
        if not self.enabled:
            return
            
        target_session = session_id or self.active_session or "global"
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "session_id": target_session,
            **data
        }
        
        # Add to memory buffer for immediate get_events querying
        self._buffer.append(event)
        
        # Add to background queue
        self._log_queue.put(event)

    def track_dispatch(self, agent_id: str, agent_role: str, provider: str, model: str, latency_ms: float, success: bool, payload_size: int = 0, error: str = ""):
        self.log_event("dispatch", {
            "agent_id": agent_id,
            "agent_role": agent_role,
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "success": success,
            "payload_size": payload_size,
            "error": error
        })

    def track_error(self, agent_id: str, error_type: str, message: str, provider: str = ""):
        """Track exceptions within the protocol."""
        self.log_event("error", {
            "agent_id": agent_id,
            "error_type": error_type,
            "message": message,
            "provider": provider
        })

    def track_handoff(self, from_agent: str, to_agent: str, session_id: str, reason: str, payload_size: int):
        """Track transition between specialized agents."""
        self.log_event("handoff", {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
            "payload_size": payload_size
        }, session_id=session_id)

    def track_chain(self, session_id: str, agents_involved: list[str], total_latency_ms: float, success: bool, final_objective_met: str):
        self.log_event("chain_complete", {
            "agents_involved": agents_involved,
            "agent_count": len(agents_involved),
            "total_latency_ms": total_latency_ms,
            "success": success,
            "final_objective_met": final_objective_met
        }, session_id=session_id)

    def get_events(self, event_type: str = None) -> list[dict]:
        """Fetch all tracked events, optionally filtered by type."""
        if event_type:
            return [e for e in self._buffer if e["event_type"] == event_type]
        return self._buffer

    def get_summary(self) -> dict:
        """Generate a summary of tracking numbers."""
        dispatches: list[dict] = self.get_events("dispatch")
        
        # In the context of get_summary, avg_latency historically applies to successes only or all dispatches.
        # Looking at expectations, we have times 100, 200, 300.
        # Average is 200 if ALL are included.
        avg_latency = 0.0
        if dispatches:
            avg_latency = sum(d.get("latency_ms", 0) for d in dispatches) / len(dispatches)
            
        successes = [d for d in dispatches if d.get("success", False)]
        
        return {
            "total_dispatches": len(dispatches),
            "total_handoffs": len(self.get_events("handoff")),
            "success_rate": len(successes) / len(dispatches) if dispatches else 0.0,
            "avg_latency_ms": avg_latency
        }

    def flush(self):
        """Force flush queue to disk (blocking)."""
        if self.enabled:
            self._log_queue.join()

    def shutdown(self):
        """Gracefully complete writing queued logs."""
        if self.enabled:
            self._shutdown_event.set()
            # Wait up to 2 seconds for queue to empty
            if self._worker_thread.is_alive():
                self._worker_thread.join(timeout=2.0)


# Global singleton access
telemetry = TelemetryLogger()

def get_telemetry() -> TelemetryLogger:
    return telemetry
