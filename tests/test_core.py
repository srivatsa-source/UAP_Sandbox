import pytest
from uap.core.protocol import ACT, StateManager

def test_act_creation():
    act = ACT(session_id="123")
    act.current_objective = "Solve puzzle"
    assert act.session_id == "123"
    assert act.current_objective == "Solve puzzle"

def test_state_manager():
    sm = StateManager()
    act = sm.create_session("Build a small web app")
    assert act.session_id is not None
    assert act.current_objective == "Build a small web app"
    
    # Save & Get
    sm.save_session(act.session_id)
    act_recovered = sm.get_session(act.session_id)
    
    assert act_recovered is not None
    assert act_recovered.session_id == act.session_id
