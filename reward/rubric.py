
"""
reward/rubric.py — The Evaluator Module for Alfred.
Deterministic reward rubric for GRPO training.
ALFRED PROTOCOL: Personal well-being (TIER1) violations incur the heaviest penalties.
"""

from typing import Optional




TASK_TIERS = {
    "TIER1_PERSONAL": {
        "keywords": [
            "health", "doctor", "gym", "water", "sleep", "medicine",
            "family", "mom", "dad", "kids", "wife", "husband", "partner",
            "remind", "habit", "daily", "every day", "personal", "bhai", "didi",
            "birthday", "anniversary", "therapy", "workout", "mental health",
        ],
        "priority_score": 10,
        "description": "Master's wellbeing and relationships (Highest Priority)",
    },
    "TIER2_PROFESSIONAL": {
        "keywords": [
            "meeting", "meetings", "call", "email", "reply", "respond",
            "deadline", "project", "client", "report", "presentation",
            "standup", "sprint", "deliverable", "invoice", "contract", "viva",
        ],
        "priority_score": 5,
        "description": "Professional obligations",
    },
}


EXPECTED_AGENT_MAP = {
   
    "health": "habit_agent", "doctor": "habit_agent",
    "gym": "habit_agent", "workout": "habit_agent",
    "water": "habit_agent", "sleep": "habit_agent",
    "medicine": "habit_agent", "therapy": "habit_agent",
    "remind": "habit_agent", "habit": "habit_agent",
    "daily": "habit_agent", "every day": "habit_agent",
  
    "birthday": "knowledge_agent", "anniversary": "knowledge_agent",
    "family": "knowledge_agent", "bhai": "knowledge_agent", "didi": "knowledge_agent",

    "meeting": "meeting_agent", "meetings": "meeting_agent",
    "call": "meeting_agent", "standup": "meeting_agent", "viva": "meeting_agent",
  
    "email": "email_agent", "reply": "email_agent",
    "respond": "email_agent", "follow up": "email_agent",
}


class AlfredRubric:
    """
    Deterministic reward rubric for Alfred.
    Ensures the model prioritizes Master's health over Master's inbox.
    """

    WEIGHTS = {
        "priority_ordering":    0.30,  # Increased weight for Alfred's core mission
        "correct_routing":      0.20,
        "action_completeness":  0.20,
        "api_call_success":     0.15,
        "no_over_triggering":   0.15,
    }

    # ── Component 1: Priority Ordering (weight=0.30) ────────────────────────

    def priority_ordering(self, chosen_todo: dict, full_queue: list[dict]) -> float:
        """
        Penalty logic: Choosing TIER2 while TIER1 is pending yields 0.0.
        """
        if not chosen_todo or not full_queue:
            return 0.5

        chosen_tier = chosen_todo.get("tier", "UNCLASSIFIED")

      
        tier1_pending = [
            t for t in full_queue
            if t.get("tier") == "TIER1_PERSONAL"
            and t.get("status", "pending") == "pending"
        ]

        if not tier1_pending:
            return 0.8 

        if chosen_tier == "TIER1_PERSONAL":
            return 1.0  

        return 0.0  

    

    def correct_routing(self, todo_text: str, agent_used: str) -> float:
        if not todo_text: return 0.5
        text_lower = todo_text.lower()

        expected_agents = {agent for kw, agent in EXPECTED_AGENT_MAP.items() if kw in text_lower}

        if not expected_agents:
            return 0.8 if not agent_used or agent_used == "none" else 0.0

        return 1.0 if agent_used in expected_agents else 0.0

   

    def action_completeness(self, required_fields: list, provided_fields: dict) -> float:
        if not required_fields: return 1.0
        
        filled = sum(1 for f in required_fields if provided_fields.get(f) and str(provided_fields[f]).strip())
        return filled / len(required_fields)

    

    def api_call_success(self, tool_name: str, result: dict) -> float:
        api_tools = {"schedule_event", "send_email", "set_reminder"}
        if tool_name not in api_tools: return 0.5
        
        status = result.get("status", "error")
        return 1.0 if status == "success" else (0.5 if status == "partial" else 0.0)

   

    def no_over_triggering(self, todo_text: str, actions_taken: list) -> float:
        if not todo_text: return 0.5
        text_lower = todo_text.lower()
        
      
        has_keyword = any(kw in text_lower for tier in TASK_TIERS.values() for kw in tier["keywords"])
        has_actions = bool(actions_taken)

        return 1.0 if has_keyword == has_actions else 0.0


    def compute(self, episode: dict) -> tuple[float, dict]:
        """
        Calculates the final weighted reward for an episode.
        """
        scores = {
            "priority_ordering": self.priority_ordering(episode.get("chosen_todo", {}), episode.get("full_queue", [])),
            "correct_routing": self.correct_routing(episode.get("todo_text", ""), episode.get("agent_used", "")),
            "action_completeness": self.action_completeness(episode.get("required_fields", []), episode.get("provided_fields", {})),
            "api_call_success": self.api_call_success(episode.get("tool_name", ""), episode.get("api_result", {})),
            "no_over_triggering": self.no_over_triggering(episode.get("todo_text", ""), episode.get("actions_taken", []))
        }

        total = sum(scores[key] * self.WEIGHTS[key] for key in self.WEIGHTS)
        
        breakdown = {**scores, "total": round(total, 4), "priority_violation": scores["priority_ordering"] == 0.0}
        return total, breakdown