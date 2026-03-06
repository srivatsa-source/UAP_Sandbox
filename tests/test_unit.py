"""UAP v0.4.0 Unit Tests
Validates all core modules without requiring API keys.
"""

import json
import tempfile
import shutil
from pathlib import Path

import pytest


# ============================================================================
# Protocol Tests
# ============================================================================

class TestACT:
    def test_create_act(self):
        from uap.protocol import ACT
        act = ACT()
        assert act.session_id
        assert act.created_at
        assert act.task_chain == []
        assert act.artifacts["code_snippets"] == []

    def test_act_roundtrip(self):
        from uap.protocol import ACT
        act = ACT()
        act.current_objective = "Test objective"
        act.context_summary = "Some context"
        act.task_chain.append({"task": "t1", "agent": "a1"})
        
        d = act.to_dict()
        act2 = ACT.from_dict(d)
        assert act2.session_id == act.session_id
        assert act2.current_objective == "Test objective"
        assert len(act2.task_chain) == 1


class TestStateManager:
    def setup_method(self):
        self.tmp = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_create_and_get_session(self):
        from uap.protocol import StateManager
        mgr = StateManager(storage_dir=self.tmp)
        act = mgr.create_session("objective")
        assert act.current_objective == "objective"
        retrieved = mgr.get_session(act.session_id)
        assert retrieved.session_id == act.session_id

    def test_save_and_load_session(self):
        from uap.protocol import StateManager
        mgr = StateManager(storage_dir=self.tmp)
        act = mgr.create_session("save test")
        act.context_summary = "ctx"
        mgr.save_session(act.session_id)
        
        mgr2 = StateManager(storage_dir=self.tmp)
        loaded = mgr2.load_session(act.session_id)
        assert loaded is not None
        assert loaded.context_summary == "ctx"

    def test_delete_session(self):
        from uap.protocol import StateManager
        mgr = StateManager(storage_dir=self.tmp)
        act = mgr.create_session("delete test")
        mgr.save_session(act.session_id)
        assert mgr.delete_session(act.session_id)
        assert mgr.get_session(act.session_id) is None

    def test_list_sessions(self):
        from uap.protocol import StateManager
        mgr = StateManager(storage_dir=self.tmp)
        mgr.create_session("s1")
        mgr.create_session("s2")
        for sid in list(mgr.active_sessions):
            mgr.save_session(sid)
        sessions = mgr.list_sessions()
        assert len(sessions) == 2

    def test_apply_state_updates(self):
        from uap.protocol import StateManager
        mgr = StateManager(storage_dir=self.tmp)
        act = mgr.create_session("update test")
        mgr.apply_state_updates(act.session_id, {
            "current_objective": "new obj",
            "context_summary": "new ctx",
            "task_completed": "task1",
            "result_summary": "done",
            "artifacts": {"code_snippets": ["print('hi')"]}
        }, "test_agent")
        assert act.current_objective == "new obj"
        assert len(act.task_chain) == 1
        assert "print('hi')" in act.artifacts["code_snippets"]
        assert len(act.handshake_log) == 1

    def test_validate_handshake_needs_2_agents(self):
        from uap.protocol import StateManager
        mgr = StateManager(storage_dir=self.tmp)
        act = mgr.create_session("validate test")
        mgr.apply_state_updates(act.session_id, {"task_completed": "t1"}, "agent_a")
        mgr.apply_state_updates(act.session_id, {"task_completed": "t2"}, "agent_b")
        result = mgr.validate_handshake(act.session_id)
        assert result["checks"]["multi_agent"]["passed"]

    def test_prepare_handoff(self):
        from uap.protocol import StateManager
        mgr = StateManager(storage_dir=self.tmp)
        act = mgr.create_session("handoff test")
        act.origin_agent = "from_agent"
        act.handoff_reason = "needs code"
        data = mgr.prepare_handoff(act.session_id)
        assert data["handoff_context"]["from_agent"] == "from_agent"


# ============================================================================
# Agent Registry Tests
# ============================================================================

class TestAgents:
    def test_get_all_agents(self):
        from uap.agents import get_all_agents
        agents = get_all_agents()
        assert len(agents) == 9

    def test_get_core_agents(self):
        from uap.agents import get_core_agents
        assert len(get_core_agents()) == 6

    def test_get_dockdesk_agents(self):
        from uap.agents import get_dockdesk_agents
        assert len(get_dockdesk_agents()) == 3

    def test_agent_config_fields(self):
        from uap.agents import PLANNER_AGENT
        assert PLANNER_AGENT.agent_id == "planner_agent"
        assert PLANNER_AGENT.agent_type == "planner"
        assert PLANNER_AGENT.backend == "groq"
        assert "planner" in PLANNER_AGENT.system_prompt.lower()

    def test_all_agents_have_required_fields(self):
        from uap.agents import get_all_agents
        for agent in get_all_agents():
            assert agent.agent_id
            assert agent.agent_type
            assert agent.system_prompt
            assert agent.model
            assert agent.backend


# ============================================================================
# Dispatcher Tests (no API calls)
# ============================================================================

class TestDispatcher:
    def test_register_and_list_agents(self):
        from uap.dispatcher import Dispatcher, AgentConfig
        d = Dispatcher()
        a = AgentConfig(
            agent_id="test_agent", agent_type="tester",
            system_prompt="test", model="test-model", backend="groq"
        )
        d.register_agent(a)
        agents = d.list_agents()
        assert any(getattr(ag, "agent_id", None) == "test_agent" for ag in agents)

    def test_unregister_agent(self):
        from uap.dispatcher import Dispatcher, AgentConfig
        d = Dispatcher()
        a = AgentConfig(
            agent_id="temp_agent", agent_type="temp",
            system_prompt="temp", model="m", backend="groq"
        )
        d.register_agent(a)
        assert d.unregister_agent("temp_agent")
        assert not d.unregister_agent("temp_agent")

    def test_dispatch_unknown_agent_raises(self):
        from uap.dispatcher import Dispatcher
        d = Dispatcher()
        with pytest.raises(ValueError, match="not registered"):
            d.dispatch(agent_id="nonexistent", task="hello")


# ============================================================================
# Telemetry Tests
# ============================================================================

class TestTelemetry:
    def setup_method(self):
        self.tmp = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_collector(self):
        from uap.telemetry import TelemetryCollector
        t = TelemetryCollector()
        t._telemetry_dir = self.tmp
        return t

    def test_track_dispatch_and_flush(self):
        t = self._make_collector()
        t.track_dispatch("a1", "planner", "groq", "llama", 100.5, True, 200)
        t.flush()
        events = t.get_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "dispatch"
        assert events[0]["latency_ms"] == 100.5

    def test_track_handoff(self):
        t = self._make_collector()
        t.track_handoff("a1", "a2", "sess1", "needs code", 1024)
        t.flush()
        events = t.get_events(event_type="handoff")
        assert len(events) == 1
        assert events[0]["from_agent"] == "a1"

    def test_track_chain(self):
        t = self._make_collector()
        t.track_chain("sess1", ["a1", "a2"], 5000.0, True, "build api")
        t.flush()
        events = t.get_events(event_type="chain_complete")
        assert len(events) == 1
        assert events[0]["agent_count"] == 2

    def test_track_error(self):
        t = self._make_collector()
        t.track_error("a1", "ValueError", "bad input", "groq")
        t.flush()
        events = t.get_events(event_type="error")
        assert len(events) == 1

    def test_get_summary(self):
        t = self._make_collector()
        t.track_dispatch("a1", "planner", "groq", "m", 100, True, 100)
        t.track_dispatch("a2", "coder", "groq", "m", 200, True, 200)
        t.track_dispatch("a3", "coder", "groq", "m", 300, False, 0, "error")
        t.track_handoff("a1", "a2", "s1", "reason", 512)
        t.flush()
        s = t.get_summary()
        assert s["total_dispatches"] == 3
        assert s["total_handoffs"] == 1
        assert s["success_rate"] == pytest.approx(2 / 3)
        assert s["avg_latency_ms"] == pytest.approx(200.0)

    def test_timer(self):
        from uap.telemetry import TelemetryCollector
        t = TelemetryCollector()
        timer = t.timer()
        with timer:
            _ = sum(range(1000))
        assert timer.elapsed_ms > 0

    def test_disabled_collector(self):
        from uap.telemetry import TelemetryCollector
        t = TelemetryCollector(enabled=False)
        t._telemetry_dir = self.tmp
        t.track_dispatch("a1", "planner", "groq", "m", 100, True)
        t.flush()
        assert t.get_events() == []

    def test_singleton(self):
        from uap.telemetry import get_telemetry
        t1 = get_telemetry()
        t2 = get_telemetry()
        assert t1 is t2


# ============================================================================
# Vault Tests (Fernet)
# ============================================================================

class TestVault:
    def setup_method(self):
        self.tmp = Path(tempfile.mkdtemp())
        # Monkey-patch vault path
        import uap.vault as vault_mod
        self._orig_get_vault = vault_mod.get_vault_path
        vault_mod.get_vault_path = lambda: self.tmp

    def teardown_method(self):
        import uap.vault as vault_mod
        vault_mod.get_vault_path = self._orig_get_vault
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_store_and_retrieve(self):
        from uap.vault import store_credential, get_credential
        assert store_credential("test@gmail.com", "openai", "sk-test-key-123")
        retrieved = get_credential("test@gmail.com", "openai")
        assert retrieved == "sk-test-key-123"

    def test_retrieve_nonexistent(self):
        from uap.vault import get_credential
        assert get_credential("nobody@gmail.com", "openai") is None

    def test_unlink_agent(self):
        from uap.vault import store_credential, get_credential, unlink_agent
        store_credential("test@gmail.com", "mistral", "key-abc")
        assert unlink_agent("test@gmail.com", "mistral")
        assert get_credential("test@gmail.com", "mistral") is None

    def test_fernet_encryption_format(self):
        from uap.vault import store_credential, _get_user_vault_path
        store_credential("test@gmail.com", "anthropic", "sk-ant-test")
        cred_file = _get_user_vault_path("test@gmail.com") / "anthropic.json"
        data = json.loads(cred_file.read_text())
        # Fernet format stores dict with salt + ciphertext
        assert isinstance(data["encrypted_key"], dict)
        assert "salt" in data["encrypted_key"]
        assert "ciphertext" in data["encrypted_key"]
        assert data["vault_version"] == 2


# ============================================================================
# Handoff Trace Tests
# ============================================================================

class TestHandoffTrace:
    def _make_act(self):
        return {
            "session_id": "test123",
            "current_objective": "test",
            "handshake_log": [
                {"agent": "planner", "timestamp": "2025-01-01T10:00:00", "action": "state_update", "updates_applied": ["obj"]},
                {"agent": "coder", "timestamp": "2025-01-01T10:00:05", "action": "state_update", "updates_applied": ["code"]},
            ]
        }

    def test_ascii_trace(self):
        from uap.dashboard.components.handoff_trace import render_handoff_ascii
        result = render_handoff_ascii(self._make_act())
        assert "planner" in result
        assert "coder" in result
        assert "test123" in result

    def test_ascii_empty(self):
        from uap.dashboard.components.handoff_trace import render_handoff_ascii
        result = render_handoff_ascii({"handshake_log": []})
        assert "no handoffs" in result

    def test_dag_available_if_graphviz(self):
        from uap.dashboard.components.handoff_trace import render_handoff_dag, HAS_GRAPHVIZ
        result = render_handoff_dag(self._make_act())
        if HAS_GRAPHVIZ:
            assert result is not None
            assert "planner" in result
        else:
            assert result is None


# ============================================================================
# MCP Server Tests (tool routing, no actual MCP transport)
# ============================================================================

class TestMCPServer:
    def test_execute_tool_create_session(self):
        from uap.mcp_server import _execute_tool
        from uap.dispatcher import Dispatcher
        from uap.agents import get_all_agents
        d = Dispatcher()
        for a in get_all_agents():
            d.register_agent(a)
        result = _execute_tool(d, "create_session", {"objective": "test mcp"})
        assert "session_id" in result
        assert result["act"]["current_objective"] == "test mcp"

    def test_execute_tool_list_agents(self):
        from uap.mcp_server import _execute_tool
        from uap.dispatcher import Dispatcher
        from uap.agents import get_all_agents
        d = Dispatcher()
        for a in get_all_agents():
            d.register_agent(a)
        result = _execute_tool(d, "list_agents", {})
        assert len(result) == 9

    def test_execute_tool_get_session_not_found(self):
        from uap.mcp_server import _execute_tool
        from uap.dispatcher import Dispatcher
        d = Dispatcher()
        result = _execute_tool(d, "get_session", {"session_id": "nonexistent"})
        assert "error" in result

    def test_execute_tool_unknown(self):
        from uap.mcp_server import _execute_tool
        from uap.dispatcher import Dispatcher
        d = Dispatcher()
        result = _execute_tool(d, "bogus_tool", {})
        assert "error" in result


# ============================================================================
# Package-level Tests
# ============================================================================

class TestPackage:
    def test_version(self):
        from uap import __version__
        assert __version__ == "0.4.0"

    def test_exports(self):
        from uap import (
            ACT, StateManager, Dispatcher, AgentConfig,
            AgentRegistry, TelemetryCollector, get_telemetry,
            get_all_agents, get_core_agents, get_dockdesk_agents,
            LocalModelManager,
        )
        assert ACT is not None
        assert LocalModelManager is not None

    def test_dashboard_imports(self):
        from uap.dashboard.models.state_packet import StatePacket
        sp = StatePacket()
        sp.update("key", "value")
        assert sp.get("key") == "value"

    def test_packet_handler(self):
        from uap.dashboard.utils.packet_handler import (
            serialize_packet, deserialize_packet, validate_packet
        )
        d = {"session_id": "x", "task_chain": [], "current_objective": "y"}
        assert deserialize_packet(serialize_packet(d)) == d
        assert validate_packet(d)
        assert not validate_packet({"foo": "bar"})


# ============================================================================
# Local Model Manager Tests
# ============================================================================

class TestLocalModelManager:
    def test_backends_defined(self):
        from uap.local_models import BACKENDS
        assert "ollama" in BACKENDS
        assert "lmstudio" in BACKENDS
        assert "llamacpp" in BACKENDS
        assert "vllm" in BACKENDS

    def test_backend_status_dataclass(self):
        from uap.local_models import BackendStatus
        st = BackendStatus(backend="ollama", name="Ollama", url="http://localhost:11434")
        assert st.online is False
        assert st.models == []
        assert st.error is None

    def test_unknown_backend_health(self):
        from uap.local_models import LocalModelManager
        mgr = LocalModelManager()
        st = mgr.health_check("nonexistent")
        assert not st.online
        assert "Unknown backend" in st.error

    def test_unknown_backend_models(self):
        from uap.local_models import LocalModelManager
        mgr = LocalModelManager()
        assert mgr.list_models("nonexistent") == []

    def test_offline_health_check(self):
        """Probing a backend that is not running returns offline status."""
        from uap.local_models import LocalModelManager
        mgr = LocalModelManager()
        # Use a port that almost certainly has no server
        mgr._config["ollama_url"] = "http://127.0.0.1:59999"
        st = mgr.health_check("ollama")
        assert not st.online
        assert st.error is not None

    def test_discover_returns_all_backends(self):
        from uap.local_models import LocalModelManager, BACKENDS
        mgr = LocalModelManager()
        results = mgr.discover()
        assert len(results) == len(BACKENDS)

    def test_get_status_structure(self):
        from uap.local_models import LocalModelManager
        mgr = LocalModelManager()
        info = mgr.get_status()
        assert "backends" in info
        assert "online_count" in info
        assert "total_models" in info
        assert isinstance(info["backends"], dict)

    def test_monitor_alias(self):
        from uap.local_models import LocalModelManager
        mgr = LocalModelManager()
        result = mgr.monitor()
        assert "backends" in result
        assert "online_count" in result
        assert "total_models" in result
