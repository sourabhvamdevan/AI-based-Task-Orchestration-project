

"""
env/observation.py — The Sensory Module for Alfred.
Formats environment state into structured prompts for Alfred's Neural Cortex.
ALFRED PROTOCOL: Priority visualization ensures the model sees TIER1 tasks first.
"""



SYSTEM_PROMPT = """You are Alfred, a loyal and efficient AI Personal Task Orchestrator.
Your primary directive is to manage the Master's life with absolute priority on well-being.

CRITICAL PROTOCOL:
- TIER1_PERSONAL tasks (health, family, habits, wellness) MUST be handled BEFORE any TIER2_PROFESSIONAL tasks.
- You must maintain the Master's schedule (Calendar) and communications (Gmail/Email).
- If a task requires missing information, you must use 'ask_clarification'.
- Every response must be a valid, single JSON action.

Available tools: route_to_agent, ask_clarification, schedule_event, send_email, draft_reply, add_to_kb, set_reminder
Authorized Agents: meeting_agent, email_agent, knowledge_agent, habit_agent

Output Format:
{"tool": "<tool_name>", "params": {<params>}}
"""

TIER_LABELS = {
    "TIER1_PERSONAL": "[🔴 TIER 1 - WELLNESS PRIORITY]",
    "TIER2_PROFESSIONAL": "[🔵 TIER 2 - PROFESSIONAL]",
    "UNCLASSIFIED": "[⚪ UNCLASSIFIED]",
}



def build_observation_prompt(obs: dict) -> str:
    """
    Transforms the environment state into a structured report for Alfred.
    """
    lines = []

  
    lines.append("=== ALFRED'S DISPATCH QUEUE ===")
    queue = obs.get("queue", [])
    if not queue:
        lines.append("(The queue is currently clear, Master.)")
    else:
        for i, todo in enumerate(queue, 1):
            tier = todo.get("tier", "UNCLASSIFIED")
            label = TIER_LABELS.get(tier, "[UNCLASSIFIED]")
            text = todo.get("text", "")
            todo_id = todo.get("todo_id", "???")
            priority = todo.get("priority_score", 0)
            status = todo.get("status", "pending")

            status_marker = "● [PENDING]" if status == "pending" else "◌ [COMPLETED]"
            lines.append(
                f" {i}. {label:32s} | ID: {todo_id[:8]} | Prio: {priority} | {status_marker}\n    Task: {text}"
            )

    lines.append("-" * 40)

   
    lines.append("=== CURRENT FOCUS ===")
    current = obs.get("current_todo")
    if current:
        tier = current.get("tier", "UNCLASSIFIED")
        lines.append(f"Master, we are addressing: {current.get('text', '')}")
        lines.append(f"Contextual ID: {current.get('todo_id', '?')}")
        lines.append(f"Tier Classification: {tier}")
    else:
        lines.append("(No active task at this moment.)")

    lines.append("-" * 40)


    lines.append("=== MASTER'S PROFILE ===")
    ctx = obs.get("user_context", {})
    name = ctx.get("name", "Master")
    tz = ctx.get("timezone", "Asia/Kolkata")
    style = ctx.get("communication_style", "formal")
    role = ctx.get("role", "Engineer")
    lines.append(f"User: {name} | Identity: {role} | Timezone: {tz} | Style: {style}")

    lines.append("-" * 40)


    step = obs.get("step", 0)
    max_steps = obs.get("max_steps", 10)
    lines.append(f"Orchestration Step: {step}/{max_steps}")
    lines.append("\nAlfred, what is your next action for the Master?")
    lines.append("Response must be in JSON format:")

    return "\n".join(lines)


def format_episode_prompt(obs: dict) -> str:
    """
    Constructs the full prompt wrapper for Inference and Training.
    """
    user_prompt = build_observation_prompt(obs)
    return (
        f"<|system|>\n{SYSTEM_PROMPT}\n"
        f"<|user|>\n{user_prompt}\n"
        f"<|assistant|>\n"
    )