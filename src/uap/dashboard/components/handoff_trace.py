"""
UAP Handoff Trace - Real-time Handoff Visualizer
Generates Graphviz DAGs and Plotly timelines from ACT handshake logs.
"""

import json
from datetime import datetime
from typing import Optional

try:
    import graphviz
    HAS_GRAPHVIZ = True
except ImportError:
    HAS_GRAPHVIZ = False

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def render_handoff_dag(act: dict, output_format: str = "svg") -> Optional[str]:
    """
    Render a directed acyclic graph of agent handoffs from an ACT.
    
    Args:
        act: ACT dictionary (from act.to_dict())
        output_format: "svg", "png", or "dot"
    
    Returns:
        Rendered graph as string (SVG/DOT) or None if graphviz unavailable
    """
    if not HAS_GRAPHVIZ:
        return None
    
    dot = graphviz.Digraph(
        "handoff_trace",
        format=output_format,
        graph_attr={
            "bgcolor": "#0a0a0a",
            "fontcolor": "#cccccc",
            "rankdir": "LR",
            "fontname": "Consolas",
            "pad": "0.5",
        },
        node_attr={
            "style": "filled",
            "fillcolor": "#1a1a1a",
            "fontcolor": "#e0e0e0",
            "color": "#444444",
            "fontname": "Consolas",
            "fontsize": "11",
            "shape": "box",
            "margin": "0.15,0.08",
        },
        edge_attr={
            "color": "#58a6ff",
            "fontcolor": "#888888",
            "fontname": "Consolas",
            "fontsize": "9",
            "arrowsize": "0.7",
        },
    )
    
    handshake_log = act.get("handshake_log", [])
    if not handshake_log:
        return None
    
    # Build nodes and edges from handshake log
    agents_seen = set()
    edges = []
    prev_agent = None
    
    for i, entry in enumerate(handshake_log):
        agent = entry.get("agent", f"agent_{i}")
        action = entry.get("action", "")
        timestamp = entry.get("timestamp", "")
        
        if agent not in agents_seen:
            # Color first and last agents differently
            fill = "#1a2a1a" if i == 0 else "#1a1a2a" if i == len(handshake_log) - 1 else "#1a1a1a"
            border = "#8f8" if i == 0 else "#88f" if i == len(handshake_log) - 1 else "#444"
            
            time_short = timestamp.split("T")[1][:8] if "T" in timestamp else ""
            label = f"{agent}\\n{time_short}"
            
            dot.node(agent, label=label, fillcolor=fill, color=border)
            agents_seen.add(agent)
        
        if prev_agent and prev_agent != agent:
            edges.append((prev_agent, agent, action))
        
        prev_agent = agent
    
    for src, dst, label in edges:
        dot.edge(src, dst, label=label)
    
    # Add session info
    session_id = act.get("session_id", "unknown")
    objective = act.get("current_objective", "")[:60]
    dot.attr(label=f"\\nSession: {session_id} | {objective}", fontsize="10")
    
    if output_format == "dot":
        return dot.source
    
    return dot.pipe(encoding="utf-8")


def render_handoff_timeline(act: dict) -> Optional[object]:
    """
    Render a Plotly timeline of agent activity from an ACT.
    
    Args:
        act: ACT dictionary
    
    Returns:
        Plotly Figure object or None if plotly unavailable
    """
    if not HAS_PLOTLY:
        return None
    
    handshake_log = act.get("handshake_log", [])
    if not handshake_log:
        return None
    
    agents = []
    starts = []
    ends = []
    actions = []
    colors = []
    
    color_map = {}
    palette = ["#58a6ff", "#8f8", "#f88", "#ff8", "#88f", "#f8f", "#8ff", "#fa8"]
    
    for i, entry in enumerate(handshake_log):
        agent = entry.get("agent", f"agent_{i}")
        timestamp = entry.get("timestamp", "")
        action = entry.get("action", "unknown")
        
        if agent not in color_map:
            color_map[agent] = palette[len(color_map) % len(palette)]
        
        try:
            start_dt = datetime.fromisoformat(timestamp)
        except (ValueError, TypeError):
            continue
        
        # Estimate end time from next entry or add small duration
        if i + 1 < len(handshake_log):
            next_ts = handshake_log[i + 1].get("timestamp", "")
            try:
                end_dt = datetime.fromisoformat(next_ts)
            except (ValueError, TypeError):
                end_dt = start_dt
        else:
            end_dt = start_dt
        
        # Ensure minimum visible width
        if end_dt == start_dt:
            from datetime import timedelta
            end_dt = start_dt + timedelta(seconds=1)
        
        agents.append(agent)
        starts.append(start_dt)
        ends.append(end_dt)
        actions.append(action)
        colors.append(color_map[agent])
    
    if not agents:
        return None
    
    fig = go.Figure()
    
    for i in range(len(agents)):
        fig.add_trace(go.Bar(
            x=[(ends[i] - starts[i]).total_seconds()],
            y=[agents[i]],
            base=[starts[i]],
            orientation="h",
            marker=dict(color=colors[i], line=dict(color="#333", width=1)),
            text=actions[i],
            textposition="inside",
            hovertemplate=f"<b>{agents[i]}</b><br>Action: {actions[i]}<br>Start: {starts[i]}<br>End: {ends[i]}<extra></extra>",
            showlegend=False,
        ))
    
    session_id = act.get("session_id", "unknown")
    fig.update_layout(
        title=dict(text=f"Handoff Timeline — Session {session_id}", font=dict(color="#ccc", family="Consolas")),
        xaxis=dict(title="Time", gridcolor="#222", color="#888"),
        yaxis=dict(title="Agent", gridcolor="#222", color="#888", autorange="reversed"),
        plot_bgcolor="#0a0a0a",
        paper_bgcolor="#0a0a0a",
        font=dict(color="#ccc", family="Consolas"),
        barmode="overlay",
        height=max(200, len(set(agents)) * 60 + 100),
    )
    
    return fig


def render_handoff_ascii(act: dict) -> str:
    """
    Render a simple ASCII representation of the handoff chain.
    Always available (no external deps).
    """
    handshake_log = act.get("handshake_log", [])
    if not handshake_log:
        return "  (no handoffs recorded)"
    
    lines = []
    prev_agent = None
    
    for entry in handshake_log:
        agent = entry.get("agent", "?")
        action = entry.get("action", "")
        ts = entry.get("timestamp", "")
        time_short = ts.split("T")[1][:8] if "T" in ts else ts[:8]
        
        if prev_agent and prev_agent != agent:
            lines.append(f"    |")
            lines.append(f"    +--[{action}]-->")
            lines.append(f"    |")
        
        lines.append(f"  [{time_short}] {agent}: {action}")
        prev_agent = agent
    
    session_id = act.get("session_id", "?")
    header = f"  Handoff Trace — Session {session_id}"
    separator = "  " + "-" * (len(header) - 2)
    
    return "\n".join([header, separator] + lines)
