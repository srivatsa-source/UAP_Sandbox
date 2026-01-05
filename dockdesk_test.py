"""
DockDesk UAP Test - Remote Programming Handoff Scenario
Simulates a realistic remote programming request flowing through:
  Analyzer → Implementer → QA
Without any user re-prompting between agents.
"""

import os
import json

# Set API key from environment or config
# Run: uap config set groq_api_key <your-key>
if not os.getenv("GROQ_API_KEY"):
    print("Warning: GROQ_API_KEY not set. Run: uap config set groq_api_key <key>")

from dispatcher import Dispatcher
from agents import get_dockdesk_agents, DOCKDESK_ANALYZER, DOCKDESK_IMPLEMENTER, DOCKDESK_QA


def run_dockdesk_test():
    """
    Simulates a DockDesk remote programming workflow:
    
    User Request → Analyzer → Implementer → QA → Complete
    
    The key validation: each agent works from ACT alone, no re-prompting.
    """
    print("=" * 70)
    print("DOCKDESK REMOTE PROGRAMMING TEST")
    print("Scenario: User requests a REST API endpoint via DockDesk")
    print("=" * 70)
    
    # Initialize dispatcher with DockDesk agents
    dispatcher = Dispatcher()
    for agent in get_dockdesk_agents():
        dispatcher.register_agent(agent)
    
    # =========================================================================
    # SIMULATED USER REQUEST (as if submitted through DockDesk platform)
    # =========================================================================
    user_request = """
    DockDesk Request #4521
    From: startup_dev_team
    Project: inventory-api (Python/FastAPI)
    
    REQUEST:
    We need a new API endpoint to search products by multiple criteria.
    
    Requirements:
    - Endpoint: GET /api/v1/products/search
    - Query params: name (partial match), category, min_price, max_price, in_stock (bool)
    - Return paginated results (limit/offset)
    - Include total count in response
    - Return 400 for invalid price range (min > max)
    
    Existing code context:
    - We use FastAPI with Pydantic models
    - Database is PostgreSQL with SQLAlchemy ORM
    - Existing Product model has: id, name, category, price, stock_quantity
    - Auth is already handled by middleware (no auth code needed)
    
    Please implement this endpoint following our existing patterns.
    """
    
    # =========================================================================
    # STEP 1: Analyzer receives and breaks down the request
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: DockDesk Analyzer - Breaking down request")
    print("=" * 70)
    
    result_1 = dispatcher.dispatch(
        agent_id="dockdesk_analyzer",
        task=user_request
    )
    
    session_id = result_1["session_id"]
    print(f"\nSession ID: {session_id}")
    print(f"\n--- Analyzer Output ---")
    print(result_1["response"][:800] + "..." if len(result_1["response"]) > 800 else result_1["response"])
    
    if "handoff_info" in result_1:
        print(f"\n[Handoff] → {result_1['handoff_info'].get('next_agent_hint', 'next agent')}")
    
    # =========================================================================
    # STEP 2: Implementer codes the solution (ACT only, no user prompt)
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: DockDesk Implementer - Writing code from ACT")
    print("=" * 70)
    
    result_2 = dispatcher.handoff(
        session_id=session_id,
        to_agent_id="dockdesk_implementer"
    )
    
    print(f"\n--- Implementer Output ---")
    print(result_2["response"][:1200] + "..." if len(result_2["response"]) > 1200 else result_2["response"])
    
    if "handoff_info" in result_2:
        print(f"\n[Handoff] → {result_2['handoff_info'].get('next_agent_hint', 'next agent')}")
    
    # =========================================================================
    # STEP 3: QA reviews the implementation (ACT only, no user prompt)
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: DockDesk QA - Reviewing implementation from ACT")
    print("=" * 70)
    
    result_3 = dispatcher.handoff(
        session_id=session_id,
        to_agent_id="dockdesk_qa"
    )
    
    print(f"\n--- QA Output ---")
    print(result_3["response"][:800] + "..." if len(result_3["response"]) > 800 else result_3["response"])
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("HANDSHAKE VALIDATION")
    print("=" * 70)
    
    validation = dispatcher.validate_handshake(session_id)
    print(json.dumps(validation, indent=2))
    
    # =========================================================================
    # FINAL ACT STATE - What got captured
    # =========================================================================
    print("\n" + "=" * 70)
    print("FINAL ACT - Task Chain")
    print("=" * 70)
    
    act = result_3["act"]
    for i, task in enumerate(act["task_chain"], 1):
        print(f"\n{i}. Agent: {task['agent']}")
        print(f"   Task: {task['task'][:80]}..." if len(task.get('task', '')) > 80 else f"   Task: {task.get('task', 'N/A')}")
        print(f"   Result: {task.get('result_summary', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("ARTIFACTS COLLECTED")
    print("=" * 70)
    
    artifacts = act.get("artifacts", {})
    
    if artifacts.get("code_snippets"):
        print(f"\nCode Snippets: {len(artifacts['code_snippets'])} captured")
        for i, snippet in enumerate(artifacts["code_snippets"][:2], 1):
            preview = snippet[:200] + "..." if len(snippet) > 200 else snippet
            print(f"\n  [{i}] {preview}")
    
    if artifacts.get("decisions"):
        print(f"\nDecisions Made: {len(artifacts['decisions'])}")
        for d in artifacts["decisions"][:5]:
            print(f"  • {d[:80]}..." if len(d) > 80 else f"  • {d}")
    
    if artifacts.get("files_modified"):
        print(f"\nFiles to Modify: {artifacts['files_modified']}")
    
    # =========================================================================
    # HANDSHAKE LOG - Proof of multi-agent flow
    # =========================================================================
    print("\n" + "=" * 70)
    print("HANDSHAKE LOG (Proof of Agent Chain)")
    print("=" * 70)
    
    for log in act["handshake_log"]:
        print(f"\n  [{log['timestamp']}]")
        print(f"    Agent: {log['agent']}")
        print(f"    Action: {log['action']}")
        print(f"    Updated: {', '.join(log['updates_applied'])}")
    
    return validation["valid"]


def run_debug_scenario():
    """
    Bonus test: Simulates a debugging request with handoff to debugger.
    """
    print("\n" + "=" * 70)
    print("DOCKDESK DEBUG SCENARIO")
    print("=" * 70)
    
    from agents import DEBUGGER_AGENT, CODER_AGENT
    
    dispatcher = Dispatcher()
    dispatcher.register_agent(DOCKDESK_ANALYZER)
    dispatcher.register_agent(DEBUGGER_AGENT)
    dispatcher.register_agent(CODER_AGENT)
    
    debug_request = """
    DockDesk Request #4522
    From: startup_dev_team
    Project: inventory-api
    Type: BUG FIX
    
    BUG REPORT:
    Our /api/v1/products endpoint is returning 500 errors intermittently.
    
    Error log:
    ```
    sqlalchemy.exc.OperationalError: connection already closed
    File "app/routes/products.py", line 45, in get_products
        products = db.query(Product).all()
    ```
    
    This happens under high load (50+ concurrent requests).
    We suspect it's a connection pool issue but not sure how to fix it.
    
    Current DB setup (app/database.py):
    ```python
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    ```
    
    Please diagnose and fix this issue.
    """
    
    # Analyzer → Debugger flow
    result_1 = dispatcher.dispatch(agent_id="dockdesk_analyzer", task=debug_request)
    session_id = result_1["session_id"]
    
    print(f"\nSession: {session_id}")
    print(f"Analyzer identified issue and handing to debugger...")
    
    result_2 = dispatcher.handoff(session_id=session_id, to_agent_id="debugger_agent")
    
    print(f"\n--- Debugger Analysis ---")
    print(result_2["response"][:1000] + "..." if len(result_2["response"]) > 1000 else result_2["response"])
    
    validation = dispatcher.validate_handshake(session_id)
    return validation["valid"]


if __name__ == "__main__":
    try:
        print("\n" + "🚀 " * 20)
        print("STARTING DOCKDESK UAP TESTS")
        print("🚀 " * 20)
        
        # Main test: 3-agent handoff chain
        success_main = run_dockdesk_test()
        
        print("\n" + "=" * 70)
        result_main = "✓ PASSED" if success_main else "✗ FAILED"
        print(f"MAIN TEST: {result_main}")
        print("=" * 70)
        
        # Bonus: Debug scenario
        # Uncomment to run:
        # success_debug = run_debug_scenario()
        # print(f"DEBUG TEST: {'✓ PASSED' if success_debug else '✗ FAILED'}")
        
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
