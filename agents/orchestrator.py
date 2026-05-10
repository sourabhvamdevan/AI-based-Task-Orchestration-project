

"""
agents/orchestrator.py — The Grand Controller of the Alfred Ecosystem.
Handles keyword scanning, tier classification, and priority routing.
ALFRED PROTOCOL: Personal well-being (TIER1) always supersedes professional tasks.
"""

from typing import Optional, List, Tuple, Dict


#yeh apne task definations hai

TASK_TIERS = {
    "TIER1_PERSONAL": {
        "keywords": [
            "health", "doctor", "gym", "water", "sleep", "medicine",
            "family", "mom", "dad", "kids", "wife", "husband", "partner",
            "remind", "habit", "daily", "every day", "personal", "bhai", "didi",
            "birthday", "anniversary", "therapy", "workout", "mental health",
        ],
        "priority_score": 10,
        "description": "Master's wellbeing and core relationships",
    },
    "TIER2_PROFESSIONAL": {
        "keywords": [
            "meeting", "meetings", "call", "email", "reply", "respond",
            "deadline", "project", "client", "report", "presentation",
            "standup", "sprint", "deliverable", "invoice", "contract", "viva",
        ],
        "priority_score": 5,
        "description": "Professional obligations and work tasks",
    },
}




KEYWORD_MAP = {
    #tier 1 personals ke liye
    "health": "habit_agent", "doctor": "habit_agent", "gym": "habit_agent",
    "workout": "habit_agent", "water": "habit_agent", "sleep": "habit_agent",
    "medicine": "habit_agent", "therapy": "habit_agent", "mental health": "habit_agent",
    "remind": "habit_agent", "habit": "habit_agent", "daily": "habit_agent",
    "every day": "habit_agent",
  
    "birthday": "knowledge_agent", "anniversary": "knowledge_agent",
    "family": "knowledge_agent", "bhai": "knowledge_agent", "didi": "knowledge_agent",
   
    "meeting": "meeting_agent", "meetings": "meeting_agent", "call": "meeting_agent",
    "standup": "meeting_agent", "viva": "meeting_agent",
   
    "email": "email_agent", "reply": "email_agent", "respond": "email_agent",
    "follow up": "email_agent",
   
    "ask": "knowledge_agent", "know": "knowledge_agent", "recall": "knowledge_agent",
    "remember": "knowledge_agent",
}


NON_TRIGGER_BLOCKLIST = [
    "buy", "grocery", "shopping", "watch", "movie", "cook", "dinner",
    "clean", "laundry", "pay bill", "fix", "repair", "travel",
]


class Orchestrator:
    """
    Central routing layer for Alfred.
    Ensures logical flow from task ingestion to agent execution.
    """

    def classify_tier(self, todo_text: str) -> Tuple[str, int]:
        """
        Classifies a todo based on Alfred's priority protocol.
        TIER1 always wins in case of conflict.
        """
        if not todo_text:
            return ("UNCLASSIFIED", 0)

        text_lower = todo_text.lower()
        matches_t1 = any(kw in text_lower for kw in TASK_TIERS["TIER1_PERSONAL"]["keywords"])
        matches_t2 = any(kw in text_lower for kw in TASK_TIERS["TIER2_PROFESSIONAL"]["keywords"])

        if matches_t1:
            return ("TIER1_PERSONAL", TASK_TIERS["TIER1_PERSONAL"]["priority_score"])
        if matches_t2:
            return ("TIER2_PROFESSIONAL", TASK_TIERS["TIER2_PROFESSIONAL"]["priority_score"])

        return ("UNCLASSIFIED", 0)

    def scan_keywords(self, todo_text: str) -> List[str]:
        """
        Matches task text to specific sub-agents.
        """
        if not todo_text:
            return []

        text_lower = todo_text.lower()
        matched_agents = {agent for kw, agent in KEYWORD_MAP.items() if kw in text_lower}

        # If no agents found, verify if it's in the blocklist
        if not matched_agents:
            if any(blocked in text_lower for blocked in NON_TRIGGER_BLOCKLIST):
                return []

        return list(matched_agents)

    def route(self, todo_text: str, todo_id: str) -> List[dict]:
        """
        Generates routing actions for the Neural Cortex (LLM).
        """
        tier, priority = self.classify_tier(todo_text)
        agents = self.scan_keywords(todo_text)

        if not agents:
            return [{
                "tool": "route_to_agent",
                "params": {
                    "todo_id": todo_id,
                    "agent_name": "none",
                    "tier": tier,
                    "priority_score": priority,
                },
                "routed": False,
            }]

        return [{
            "tool": "route_to_agent",
            "params": {
                "todo_id": todo_id,
                "agent_name": agent,
                "tier": tier,
                "priority_score": priority,
            },
            "routed": True,
        } for agent in agents]

    def sort_queue(self, queue: List[dict]) -> List[dict]:
        """
        Sorts the Master's queue:
        1. Priority Score (Tier) Descending
        2. Submission Time Ascending (FIFO)
        """
        return sorted(queue, key=lambda t: (-t.get("priority_score", 0), t.get("submitted_at", "9999")))

    def check_priority_violation(self, chosen_todo_id: str, queue: List[dict]) -> bool:
        """
        ALFRED CRITICAL CHECK:
        Returns True if a professional task is chosen while a personal task is pending.
        """
        chosen_todo = next((t for t in queue if t.get("todo_id") == chosen_todo_id), None)
        if not chosen_todo or chosen_todo.get("tier") == "TIER1_PERSONAL":
            return False

        # If we reach here, a non-TIER1 was chosen. Check if any TIER1 is still pending.
        return any(
            t.get("tier") == "TIER1_PERSONAL" and t.get("status") == "pending" 
            for t in queue if t.get("todo_id") != chosen_todo_id
        )

    def get_expected_agent(self, todo_text: str) -> Optional[str]:
        agents = self.scan_keywords(todo_text)
        return agents[0] if agents else None

    def get_expected_tool(self, agent_name: str) -> Optional[str]:
        return {
            "meeting_agent": "schedule_event",
            "email_agent": "send_email",
            "knowledge_agent": "add_to_kb",
            "habit_agent": "set_reminder",
        }.get(agent_name)