"""
UAP Live Handshake Test - Real LLM Agents via Groq
Validates that Agent B can execute using ONLY the ACT from Agent A.
"""

import os
import json

# Set API key from environment or config
# Run: uap config set groq_api_key <your-key>
if not os.getenv("GROQ_API_KEY"):
    print("Warning: GROQ_API_KEY not set. Run: uap config set groq_api_key <key>")

from dispatcher import Dispatcher, AgentConfig


def run_live_handshake_test():
    """
    Live test: Designer Agent → Coder Agent handoff via Groq.
    Proves Agent B works from ACT alone, no user re-prompting.
    """
    print("=" * 70)
    print("UAP LIVE HANDSHAKE TEST - GROQ")
    print("=" * 70)
    
    # Initialize dispatcher
    dispatcher = Dispatcher()
    
    # Register Agent A: Designer
    designer = AgentConfig(
        agent_id="designer_agent",
        agent_type="designer",
        system_prompt="""You are a pixel art designer for retro games.
You create visual designs and specifications for game assets.
Keep designs simple and focused on 16x16 or 32x32 sprites.
Always specify exact colors using hex codes.""",
        model="llama-3.1-8b-instant",
        backend="groq"
    )
    dispatcher.register_agent(designer)
    
    # Register Agent B: Coder
    coder = AgentConfig(
        agent_id="coder_agent",
        agent_type="coder",
        system_prompt="""You are a Python game developer.
You implement game mechanics and sprite handling code.
Write clean, functional code based on design specifications.
Use Pygame conventions for sprite classes.""",
        model="llama-3.1-8b-instant",
        backend="groq"
    )
    dispatcher.register_agent(coder)
    
    # =========================================================================
    # STEP 1: Agent A (Designer) receives initial task
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: Designer Agent receives task from user")
    print("=" * 70)
    
    task = "Design a samurai character for a pixel art fighting game called One-Hit Samurai"
    
    result_a = dispatcher.dispatch(
        agent_id="designer_agent",
        task=task
    )
    
    session_id = result_a["session_id"]
    print(f"\nSession ID: {session_id}")
    print(f"\n--- Designer Response ---")
    print(result_a["response"][:500] + "..." if len(result_a["response"]) > 500 else result_a["response"])
    
    # Check if handoff requested
    if "handoff_info" in result_a:
        print(f"\n[Handoff Requested] Reason: {result_a['handoff_info']['reason']}")
        print(f"[Handoff Requested] Next: {result_a['handoff_info']['next_agent_hint']}")
    
    # =========================================================================
    # STEP 2: Handoff to Agent B (Coder) - NO USER RE-PROMPTING
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: Handoff to Coder Agent (using ACT only, NO user re-prompt)")
    print("=" * 70)
    
    # This is the critical test: Agent B gets NO new task, only the ACT
    result_b = dispatcher.handoff(
        session_id=session_id,
        to_agent_id="coder_agent"
    )
    
    print(f"\n--- Coder Response ---")
    print(result_b["response"][:500] + "..." if len(result_b["response"]) > 500 else result_b["response"])
    
    # =========================================================================
    # STEP 3: Validate the handshake
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: Validate ACT Handshake")
    print("=" * 70)
    
    validation = dispatcher.validate_handshake(session_id)
    print(json.dumps(validation, indent=2))
    
    # =========================================================================
    # FINAL: Show ACT state
    # =========================================================================
    print("\n" + "=" * 70)
    print("FINAL ACT STATE")
    print("=" * 70)
    print(json.dumps(result_b["act"], indent=2))
    
    return validation["valid"]


if __name__ == "__main__":
    try:
        success = run_live_handshake_test()
        print("\n" + "=" * 70)
        print(f"{'✓ LIVE HANDSHAKE VALID' if success else '✗ HANDSHAKE FAILED'}")
        print("=" * 70)
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        print("\nIf you see import errors, run: pip install groq")
