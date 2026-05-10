

"""
env/action_space.py — The Action Engine for the Alfred Ecosystem.
Defines valid tools, parameter schemas, and LLM output parsing logic.
ALFRED PROTOCOL: Strict validation ensures zero-error tool execution.
"""

import json
import re
from typing import Optional




TOOLS = {
    "route_to_agent": {
        "description": "Route a task to a specialized Alfred sub-agent.",
        "required_params": ["todo_id", "agent_name"],
        "param_types": {"todo_id": "str", "agent_name": "str"},
        "valid_agents": [
            "meeting_agent", "email_agent",
            "knowledge_agent", "habit_agent"
        ],
    },
    "ask_clarification": {
        "description": "Request missing details from the Master before proceeding.",
        "required_params": ["todo_id", "field", "question"],
        "param_types": {"todo_id": "str", "field": "str", "question": "str"},
    },
    "schedule_event": {
        "description": "Create a formal entry in the Master's Google Calendar.",
        "required_params": [
            "todo_id", "attendee_email", "start_time",
            "duration_minutes", "title"
        ],
        "param_types": {
            "todo_id": "str",
            "attendee_email": "str",
            "start_time": "str",        # ISO8601 Format
            "duration_minutes": "int",
            "title": "str",
        },
    },
    "send_email": {
        "description": "Dispatch a formal communication via Gmail.",
        "required_params": ["todo_id", "to", "subject", "body"],
        "param_types": {
            "todo_id": "str",
            "to": "str",
            "subject": "str",
            "body": "str",
        },
    },
    "draft_reply": {
        "description": "Generate a proposed response for an incoming message.",
        "required_params": ["email_id", "tone"],
        "param_types": {
            "email_id": "str",
            "tone": "str",  # "professional" | "casual" | "brief"
        },
    },
    "add_to_kb": {
        "description": "Commit personal facts to Alfred's long-term memory.",
        "required_params": ["todo_id", "content", "category"],
        "param_types": {
            "todo_id": "str",
            "content": "str",
            "category": "str",
        },
    },
    "set_reminder": {
        "description": "Establish a recurring well-being habit or task.",
        "required_params": ["todo_id", "label", "frequency", "time_of_day"],
        "param_types": {
            "todo_id": "str",
            "label": "str",
            "frequency": "str",     # "daily" | "weekly" | "weekdays"
            "time_of_day": "str",   # "HH:MM" (24hr format)
        },
    },
}


VALID_TONES = {"professional", "casual", "brief"}
VALID_FREQUENCIES = {"daily", "weekly", "weekdays"}
VALID_KB_CATEGORIES = {"meeting", "email", "preference", "contact", "user_profile", "habit"}




def validate_action(action: dict) -> tuple[bool, str]:
    """
    Validates an LLM-generated action against the defined schemas.
    Returns: (is_valid, error_message)
    """
    if not isinstance(action, dict):
        return False, "Action must be a valid dictionary."

    tool_name = action.get("tool")
    if not tool_name:
        return False, "Action is missing the mandatory 'tool' key."

    if tool_name not in TOOLS:
        return False, f"Unknown tool '{tool_name}'. Authorized: {list(TOOLS.keys())}"

    schema = TOOLS[tool_name]
    params = action.get("params", {})

    if not isinstance(params, dict):
        return False, f"Parameters for '{tool_name}' must be a dictionary."

   
    for field in schema["required_params"]:
        if field not in params:
            return False, f"Missing required parameter '{field}' for tool '{tool_name}'"
        
        val = params[field]
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, f"Parameter '{field}' cannot be empty or null."


    for field, expected_type in schema["param_types"].items():
        if field in params:
            val = params[field]
            if expected_type == "int" and not isinstance(val, int):
                try:
                    params[field] = int(val)
                except (ValueError, TypeError):
                    return False, f"Parameter '{field}' must be an integer."

  
    if tool_name == "route_to_agent" and params.get("agent_name") not in schema["valid_agents"]:
        return False, f"Invalid agent name. Authorized: {schema['valid_agents']}"

    if tool_name == "set_reminder":
        if params.get("frequency") not in VALID_FREQUENCIES:
            return False, f"Invalid frequency. Authorized: {list(VALID_FREQUENCIES)}"
        if not re.match(r"^\d{1,2}:\d{2}$", params.get("time_of_day", "")):
            return False, "Parameter 'time_of_day' must follow HH:MM format."

    if tool_name == "add_to_kb" and params.get("category") not in VALID_KB_CATEGORIES:
        return False, f"Invalid memory category. Authorized: {list(VALID_KB_CATEGORIES)}"

    return True, ""




def parse_llm_output(raw_output: str) -> Optional[dict]:
    """
    Advanced parsing to extract JSON actions from noisy LLM text.
    """
    if not raw_output or not isinstance(raw_output, str):
        return None

    raw_output = raw_output.strip()

   
    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, dict) and "tool" in parsed:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

  

