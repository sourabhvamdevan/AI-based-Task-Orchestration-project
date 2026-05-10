

"""
tools/reminder_tool.py — Reminder and habit tracking tool for Butler.

Manages recurring reminders stored in the KB and sends notifications via Gmail.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ReminderTool:
    """Manages reminders and habit tracking for Butler."""

    def __init__(self, kb_tool=None, gmail_tool=None):
        self._kb = kb_tool
        self._gmail = gmail_tool

    def set_tools(self, kb_tool=None, gmail_tool=None):
        """Set dependent tools."""
        if kb_tool:
            self._kb = kb_tool
        if gmail_tool:
            self._gmail = gmail_tool

    def create_reminder(
        self,
        label: str,
        frequency: str,
        time_of_day: str,
        category: str = "personal",
        user_email: str = None,
        user_name: str = "User",
    ) -> dict:
        """
        Create a recurring reminder/habit.

        Args:
            label: Reminder text.
            frequency: "daily" | "weekly" | "weekdays"
            time_of_day: "HH:MM" 24hr format.
            category: "health" | "family" | "work" | "personal"
            user_email: Email for notifications.
            user_name: User's name.

        Returns:
            {"status": "success"|"error", "habit_id": str, ...}
        """
        try:
            habit_id = f"habit_{uuid.uuid4().hex[:10]}"

            habit_data = {
                "habit_id": habit_id,
                "label": label,
                "frequency": frequency,
                "time_of_day": time_of_day,
                "category": category,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "streak": 0,
                "completions": [],
                "active": True,
            }

            # Save to KB
            if self._kb:
                self._kb.add_entry(
                    content=f"Habit: {label} ({frequency} at {time_of_day})",
                    category="habit",
                    source="habit_agent",
                    user_consented=True,
                )

            # Send initial confirmation email
            if self._gmail and user_email:
                self._gmail.send_email(
                    to=user_email,
                    subject=f"Butler Reminder Set: {label}",
                    body=(
                        f"Hey {user_name},\n\n"
                        f"Your {frequency} reminder has been set:\n"
                        f"📌 {label}\n"
                        f"⏰ {time_of_day}\n\n"
                        f"You've got this!\n— Butler"
                    ),
                )

            logger.info("Reminder created: %s (%s)", habit_id, label)
            return {
                "status": "success",
                "habit_id": habit_id,
                "label": label,
                "frequency": frequency,
                "time_of_day": time_of_day,
            }

        except Exception as e:
            logger.error("Reminder create error: %s", str(e))
            return {"status": "error", "message": str(e)}

    def send_reminder(
        self,
        label: str,
        frequency: str,
        user_email: str,
        user_name: str = "User",
    ) -> dict:
        """
        Send a reminder notification email.

        Returns:
            Email send result dict.
        """
        if not self._gmail:
            return {
                "status": "success",
                "simulated": True,
                "message": "No Gmail service — reminder simulated.",
            }

        return self._gmail.send_email(
            to=user_email,
            subject=f"Butler Reminder: {label}",
            body=(
                f"Hey {user_name}, your {frequency} reminder:\n\n"
                f"📌 {label}\n\n"
                f"You've got this. — Butler"
            ),
        )

    def mark_complete(self, habit_id: str) -> dict:
        """
        Mark a habit as completed for today.

        Returns:
            {"status": "success"|"error", ...}
        """
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # In a full implementation, this would update the KB entry
            # For now, return success with updated streak info
            return {
                "status": "success",
                "habit_id": habit_id,
                "completed_date": today,
                "message": f"Habit {habit_id} marked complete for {today}.",
            }

        except Exception as e:
            logger.error("Reminder mark_complete error: %s", str(e))
            return {"status": "error", "message": str(e)}

    def get_weekly_summary(self, habits: list[dict]) -> str:
        """
        Generate a weekly summary string for habits.

        Args:
            habits: List of habit dicts with completions.

        Returns:
            Formatted summary string.
        """
        lines = [
            "📊 Weekly Habit Summary",
            "=" * 40,
            f"{'Habit':<25} {'Target':>7} {'Done':>5} {'Streak':>7}",
            "-" * 40,
        ]

        for habit in habits:
            label = habit.get("label", "Unknown")[:24]
            freq = habit.get("frequency", "daily")
            target = {"daily": 7, "weekly": 1, "weekdays": 5}.get(freq, 7)
            done = len(habit.get("completions", []))
            streak = habit.get("streak", 0)
            lines.append(f"{label:<25} {target:>7} {done:>5} {streak:>7}")

        lines.append("-" * 40)
        return "\n".join(lines)

    def send_weekly_summary(
        self,
        habits: list[dict],
        user_email: str,
        user_name: str = "User",
    ) -> dict:
        """
        Send the weekly habit summary via email.

        Returns:
            Email send result dict.
        """
        summary = self.get_weekly_summary(habits)

        if not self._gmail:
            return {
                "status": "success",
                "simulated": True,
                "summary": summary,
            }

        return self._gmail.send_email(
            to=user_email,
            subject="Butler — Your Weekly Habit Summary",
            body=(
                f"Hi {user_name},\n\n"
                f"Here's your weekly habit report:\n\n"
                f"{summary}\n\n"
                f"Keep up the great work! — Butler"
            ),
        )