

"""
agents/habit_agent.py — Manages habits, reminders, and wellness tracking.
ALFRED PROTOCOL: TIER1_PERSONAL — health and habits are the highest priority.
"""

import logging
import uuid
import re
from typing import Optional

logger = logging.getLogger(__name__)


class HabitAgent:
    """
    Handles habit and reminder todos.
    In the Butler ecosystem, TIER1_PERSONAL tasks (health/family) override professional ones.

    Responsibilities:
    - Create recurring habits/reminders
    - Track habit completions and streaks
    - Generate weekly wellness summaries
    - Send reminder notifications via Alfred's systems
    """

    TIER = "TIER1_PERSONAL"
    CATEGORIES = ["health", "family", "work", "personal"]

    def __init__(self, kb_tool=None, gmail_tool=None, reminder_tool=None):
        self._kb = kb_tool
        self._gmail = gmail_tool
        self._reminder = reminder_tool
        self.agent_name = "Alfred_Habit_Agent"

    def set_tools(self, kb_tool=None, gmail_tool=None, reminder_tool=None):
        """Set dependent tools for the agent."""
        if kb_tool:
            self._kb = kb_tool
        if gmail_tool:
            self._gmail = gmail_tool
        if reminder_tool:
            self._reminder = reminder_tool

    def handle(self, todo: dict, collected_fields: dict) -> dict:
        """
        Handle a habit/reminder todo.
        """
        todo_id = todo.get("todo_id", "unknown")
        todo_text = todo.get("text", "")

        # Extract or use collected fields
        label = collected_fields.get("label", self._extract_label(todo_text))
        frequency = collected_fields.get(
            "frequency", self._infer_frequency(todo_text)
        )
        time_of_day = collected_fields.get(
            "time_of_day", self._extract_time(todo_text)
        )
        category = collected_fields.get(
            "category", self._infer_category(todo_text)
        )

        # Check for missing critical info
        if not time_of_day:
            return {
                "tool": "ask_clarification",
                "params": {
                    "todo_id": todo_id,
                    "field": "time_of_day",
                    "question": (
                        "At what time should I set this reminder for you? "
                        "Please provide it in HH:MM format (e.g., 08:00)."
                    ),
                },
                "agent": "habit_agent",
                "status": "needs_info",
                "persona": "Alfred"
            }

        # Create the habit
        result = self.create_habit(
            label=label,
            frequency=frequency,
            time_of_day=time_of_day,
            category=category,
            user_email=collected_fields.get("user_email"),
            user_name=collected_fields.get("user_name", "User"),
        )

        return {
            "tool": "set_reminder",
            "params": {
                "todo_id": todo_id,
                "label": label,
                "frequency": frequency,
                "time_of_day": time_of_day,
            },
            "agent": "habit_agent",
            "status": "completed",
            "habit_result": result,
        }

    def create_habit(
        self,
        label: str,
        frequency: str,
        time_of_day: str,
        category: str = "personal",
        user_email: str = None,
        user_name: str = "User",
    ) -> dict:
        """
        Create a recurring habit.
        1. Save to Knowledge Base
        2. Integrate with Reminder Tool
        """
        if self._reminder:
            return self._reminder.create_reminder(
                label=label,
                frequency=frequency,
                time_of_day=time_of_day,
                category=category,
                user_email=user_email,
                user_name=user_name,
            )

        # Fallback: save to KB directly
        habit_id = f"habit_{uuid.uuid4().hex[:10]}"

        if self._kb:
            self._kb.add_entry(
                content=f"Habit: {label} ({frequency} at {time_of_day})",
                category="habit",
                source="habit_agent",
                user_consented=True,
            )

        return {
            "status": "success",
            "habit_id": habit_id,
            "label": label,
            "frequency": frequency,
            "time_of_day": time_of_day,
        }

    def mark_complete(self, habit_id: str) -> dict:
        """Mark a habit as completed and update the streak."""
        if self._reminder:
            return self._reminder.mark_complete(habit_id)

        return {
            "status": "success",
            "habit_id": habit_id,
            "message": f"Habit {habit_id} marked complete by Alfred.",
        }

    def weekly_summary(
        self,
        user_email: str = None,
        user_name: str = "User",
    ) -> dict:
        """Generate and send weekly wellness summary."""
        habits = []
        if self._kb:
            habit_entries = self._kb.get_entries_by_category("habit")
            for entry in habit_entries:
                habits.append({
                    "label": entry.get("content", "Unknown habit"),
                    "frequency": "daily",
                    "completions": [],
                    "streak": 0,
                })

        if self._reminder and user_email:
            return self._reminder.send_weekly_summary(
                habits=habits,
                user_email=user_email,
                user_name=user_name,
            )

        return {
            "status": "success",
            "summary": f"Alfred's Summary: {len(habits)} habits tracked.",
            "habit_count": len(habits),
        }

    def _extract_label(self, todo_text: str) -> str:
        """Extract a clean habit label from the user's request."""
        text = todo_text
        prefixes = [
            "remind me to", "set a daily habit to",
            "set a habit to", "set up a daily",
            "daily reminder to", "remind me about",
            "i need to", "i want to",
        ]
        text_lower = text.lower()
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        # Remove trailing time context
        text = re.sub(
            r"\s*(at|every|before|after)\s+\d{1,2}[:\d]*\s*(am|pm|AM|PM)?.*$",
            "",
            text,
        ).strip()
        return text if text else todo_text[:50]

    def _infer_frequency(self, todo_text: str) -> str:
        """Determine if the habit is daily, weekly, or specific days."""
        text_lower = todo_text.lower()
        if "every day" in text_lower or "daily" in text_lower:
            return "daily"
        if "weekly" in text_lower or "every week" in text_lower:
            return "weekly"
        if "weekday" in text_lower or "weekdays" in text_lower:
            return "weekdays"
        
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if any(day in text_lower for day in days):
            return "weekly"

        return "daily"

    def _extract_time(self, todo_text: str) -> Optional[str]:
        """Convert natural language time to HH:MM (24hr)."""
        patterns = [
            r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)",
            r"(\d{1,2})\s*(AM|PM|am|pm)",
            r"(\d{1,2}):(\d{2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, todo_text)
            if match:
                groups = match.groups()
                if len(groups) == 3 and groups[2]:
                    h, m, p = int(groups[0]), int(groups[1]), groups[2].upper()
                    if p == "PM" and h != 12: h += 12
                    elif p == "AM" and h == 12: h = 0
                    return f"{h:02d}:{m:02d}"
                elif len(groups) == 2 and groups[1] in ("AM", "PM", "am", "pm"):
                    h, p = int(groups[0]), groups[1].upper()
                    if p == "PM" and h != 12: h += 12
                    elif p == "AM" and h == 12: h = 0
                    return f"{h:02d}:00"
                elif len(groups) == 2:
                    h, m = int(groups[0]), int(groups[1])
                    if 0 <= h <= 23 and 0 <= m <= 59:
                        return f"{h:02d}:{m:02d}"

        # Default time slots
        t_lower = todo_text.lower()
        if "morning" in t_lower: return "08:00"
        if "evening" in t_lower: return "18:00"
        if "night" in t_lower or "before bed" in t_lower: return "22:00"
        if "afternoon" in t_lower: return "14:00"

        return None

    def _infer_category(self, todo_text: str) -> str:
        """Categorize the habit for better reporting."""
        t_lower = todo_text.lower()
        mapping = {
            "health": ["gym", "workout", "exercise", "water", "medicine", "vitamins", "sleep", "meditate", "therapy"],
            "family": ["mom", "dad", "family", "kids", "wife", "call", "birthday"],
            "work": ["meeting", "email", "project", "deadline", "report"]
        }
        for cat, keywords in mapping.items():
            if any(kw in t_lower for kw in keywords):
                return cat
        return "personal"