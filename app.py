

import json
import os
import gradio as gr
import uuid
from datetime import datetime, timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_alfred_orchestrator = None
_alfred_env = None

def _get_orchestrator():
    global _alfred_orchestrator
    if _alfred_orchestrator is None:
        from agents.orchestrator import Orchestrator
        _alfred_orchestrator = Orchestrator()
    return _alfred_orchestrator

def _get_env():
    global _alfred_env
    if _alfred_env is None:
        from env.butler_env import ButlerEnvironment
        _alfred_env = ButlerEnvironment()
    return _alfred_env

def process_todo(todo_text: str, user_name: str = "Master") -> tuple[str, str, str]:
    if not todo_text or not todo_text.strip():
        return "No input", "No agent", "Master, please provide a task."

    orch = _get_orchestrator()
    tier, priority_score = orch.classify_tier(todo_text)

    tier_labels = {
        "TIER1_PERSONAL": f"PERSONAL - TIER 1 (Priority: {priority_score})",
        "TIER2_PROFESSIONAL": f"PROFESSIONAL - TIER 2 (Priority: {priority_score})",
        "UNCLASSIFIED": f"UNCLASSIFIED (Priority: {priority_score})",
    }
    tier_label = tier_labels.get(tier, f"Tier: {tier}")

    agents = orch.scan_keywords(todo_text)
    agent_label = ", ".join(f"Agent: {a}" for a in agents) if agents else "Alert: No agent matched."

    try:
        env = _get_env()
        todo = {
            "todo_id": uuid.uuid4().hex[:12],
            "text": todo_text,
            "tier": tier,
            "priority_score": priority_score,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        env.reset(episode_queue=[todo])
        route_actions = orch.route(todo_text, todo["todo_id"])

        action_lines = []
        for ra in route_actions:
            if ra.get("routed"):
                agent_name = ra["params"]["agent_name"]
                expected_tool = orch.get_expected_tool(agent_name)
                action_lines.append(
                    f"Success: Alfred Protocol - Routed to {agent_name}\n"
                    f"   Authorized Tool: {expected_tool or 'N/A'}\n"
                    f"   Classification: {ra['params']['tier']}"
                )
            else:
                action_lines.append("Info: Master, this task does not trigger my specific agents. It remains unclassified.")

        action_text = "\n\n".join(action_lines)
    except Exception as e:
        action_text = f"System Error: {str(e)}"

    return tier_label, agent_label, action_text

def process_queue(queue_text: str, user_name: str = "Master") -> str:
    if not queue_text or not queue_text.strip():
        return "Master, please enter tasks separated by semicolons."

    orch = _get_orchestrator()
    texts = [t.strip() for t in queue_text.split(";") if t.strip()]

    todos = []
    for i, text in enumerate(texts):
        tier, score = orch.classify_tier(text)
        todos.append({
            "todo_id": uuid.uuid4().hex[:12],
            "text": text,
            "tier": tier,
            "priority_score": score,
            "submitted_at": (datetime.now(timezone.utc) - timedelta(seconds=len(texts) - i)).isoformat(),
            "status": "pending",
        })

    sorted_todos = orch.sort_queue(todos)
    lines = ["Priority-Sorted Dispatch Queue:\n"]
    
    for i, todo in enumerate(sorted_todos, 1):
        tier_tag = f"[{todo['tier']}]"
        agents = orch.scan_keywords(todo["text"])
        lines.append(f"{i}. {tier_tag} Prio: {todo['priority_score']}\n   Task: {todo['text']}\n   Agent: {', '.join(agents) if agents else 'None'}")

    if any(t["tier"] == "TIER1_PERSONAL" for t in sorted_todos):
        lines.append("\nPriority Rule Active: Personal well-being takes precedence.")

    return "\n\n".join(lines)

def generate_synthetic_demo() -> str:
    from data.synthetic_todos import generate_episode_queue
    queue = generate_episode_queue(min_tier1=2, min_tier2=2, total=5)
    orch = _get_orchestrator()
    sorted_q = orch.sort_queue(queue)

    lines = ["Simulated Training Queue:\n"]

    for i, todo in enumerate(sorted_q, 1):
        lines.append(f"{i}. [{todo['tier']}] Prio: {todo['priority_score']}\n   {todo['text']}")

    return "\n\n".join(lines)

def build_gradio_app():
    css = ".gradio-container { max-width: 1100px !important; margin: auto !important; }"
    
    with gr.Blocks(title="Butler - AI Task Orchestrator") as demo:
        gr.HTML('<h1 style="text-align: center;">Butler: Alfred AI</h1><p style="text-align: center;">Personal Task Orchestrator</p>')
        
        with gr.Tabs():
            with gr.Tab("Single Dispatch"):
                with gr.Row():
                    with gr.Column(scale=2):
                        todo_input = gr.Textbox(placeholder="e.g. Call Mom; Schedule meeting", label="Master's Input", lines=2)
                        user_name = gr.Textbox(value="Master", label="Name")
                        submit_btn = gr.Button("Execute Protocol", variant="primary")
                    with gr.Column(scale=3):
                        tier_out = gr.Textbox(label="Classification", interactive=False)
                        agent_out = gr.Textbox(label="Agent Assigned", interactive=False)
                        action_out = gr.Textbox(label="Alfred's Action", lines=6, interactive=False)
                submit_btn.click(fn=process_todo, inputs=[todo_input, user_name], outputs=[tier_out, agent_out, action_out])

            with gr.Tab("Queue Logic"):
                queue_input = gr.Textbox(placeholder="Task 1; Task 2; Task 3", label="Semicolon-separated Queue", lines=3)
                queue_btn = gr.Button("Analyze Priority", variant="primary")
                queue_out = gr.Markdown()
                queue_btn.click(fn=process_queue, inputs=[queue_input], outputs=[queue_out])

            with gr.Tab("RL Training View"):
                gen_btn = gr.Button("Generate Episode", variant="secondary")
                gen_out = gr.Markdown()
                gen_btn.click(fn=generate_synthetic_demo, outputs=[gen_out])

    return demo

if __name__ == "__main__":
    app = build_gradio_app()
    app.launch(server_name="0.0.0.0", server_port=7860, share=True)