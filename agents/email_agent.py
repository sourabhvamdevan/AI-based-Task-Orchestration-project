

import logging
from typing import Any, Dict, List, Optional

from tools.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class EmailAgent:
    TIER = "TIER2_PROFESSIONAL"

    IMPORTANCE_KEYWORDS = [
        "urgent", "asap", "deadline", "invoice", "contract",
        "offer", "action required", "follow up", "overdue",
        "interview", "confirm", "approval", "sign", "meeting",
    ]

    def __init__(self, gmail_tool: Optional[Any] = None, kb_tool: Optional[Any] = None):
        self._gmail = gmail_tool
        self._kb = kb_tool

    def set_tools(self, gmail_tool: Optional[Any] = None, kb_tool: Optional[Any] = None) -> None:
        if gmail_tool is not None:
            self._gmail = gmail_tool
        if kb_tool is not None:
            self._kb = kb_tool

    def handle(self, todo: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, Any]:
        todo_id = todo.get("todo_id", "unknown")
        text = todo.get("text", "").lower()

        if any(k in text for k in ("reply", "respond", "follow up")):
            return self._handle_reply(todo_id, fields)

        return self._handle_send(todo_id, fields)

    def _handle_reply(self, todo_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        email_id = fields.get("email_id")
        if not email_id:
            return self._ask(todo_id, "email_id", "Which email should I reply to?")

        return {
            "tool": "draft_reply",
            "params": {
                "email_id": email_id,
                "tone": fields.get("tone", "professional"),
            },
            "agent": "email_agent",
            "status": "completed",
        }

    def _handle_send(self, todo_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        required = ("to", "subject", "body")
        for field in required:
            if not fields.get(field):
                return self._ask(todo_id, field, self._question(field))

        result = {"status": "success", "simulated": True}
        if self._gmail:
            result = self._gmail.send_email(
                to=fields["to"],
                subject=fields["subject"],
                body=fields["body"],
            )

        return {
            "tool": "send_email",
            "params": {
                "todo_id": todo_id,
                "to": fields["to"],
                "subject": fields["subject"],
                "body": fields["body"],
            },
            "agent": "email_agent",
            "status": "completed",
            "email_result": result,
        }

    def fetch_and_surface(self) -> List[Dict[str, Any]]:
        if not self._gmail:
            return []

        result = self._gmail.fetch_unread(max_results=50, days_back=7)
        if result.get("status") != "success":
            return []

        emails = result.get("emails", [])
        contacts = self._get_kb_contacts()

        for email in emails:
            email["score"] = self._score_email(email, contacts)

        return sorted(emails, key=lambda e: e["score"], reverse=True)[:10]

    def draft_reply(
        self,
        email: Dict[str, Any],
        user_context: Dict[str, Any],
        tone: str = "professional",
    ) -> str:
        user_name = user_context.get("name", "User")
        subject = email.get("subject", "")
        sender = email.get("sender", "")
        snippet = email.get("snippet", "")

        try:
            client = get_llm_client()
            if client and client.is_available:
                return self._generate_llm_reply(client, user_name, sender, subject, snippet, tone)

        except Exception as e:
            logger.error("LLM draft error: %s", str(e))

        return self._fallback(subject, sender, user_name, tone)

    def _generate_llm_reply(
        self,
        client: Any,
        user_name: str,
        sender: str,
        subject: str,
        snippet: str,
        tone: str,
    ) -> str:
        system_prompt = (
            f"You are Butler, a professional AI assistant. "
            f"Write a concise {tone} reply under 150 words for {user_name}. "
            f"Sign as '{user_name} (via Butler)'."
        )

        user_prompt = (
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Content: {snippet}\n\n"
            f"Reply:"
        )

        response = client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=200,
            temperature=0.7,
        )

        return response or self._fallback(subject, sender, user_name, tone)

    def _fallback(self, subject: str, sender: str, user_name: str, tone: str) -> str:
        if tone == "brief":
            return (
                f"Hi,\n\nThanks for your email regarding \"{subject}\". "
                f"I'll get back to you shortly.\n\nBest,\n{user_name} (via Butler)"
            )
        if tone == "casual":
            return (
                f"Hey,\n\nGot your message about \"{subject}\". "
                f"I'll follow up soon.\n\nCheers,\n{user_name} (via Butler)"
            )

        name = sender.split("<")[0].strip()
        return (
            f"Dear {name},\n\nThank you for your email regarding \"{subject}\". "
            f"I will review and respond shortly.\n\nBest regards,\n{user_name} (via Butler)"
        )

    def _score_email(self, email: Dict[str, Any], contacts: set) -> int:
        subject = email.get("subject", "").lower()
        snippet = email.get("snippet", "").lower()
        sender = email.get("sender", "").lower()

        score = sum(2 for k in self.IMPORTANCE_KEYWORDS if k in subject)
        score += sum(1 for k in self.IMPORTANCE_KEYWORDS if k in snippet)

        if any(c in sender for c in contacts):
            score += 3

        return score

    def _get_kb_contacts(self) -> set:
        if not self._kb:
            return set()

        entries = self._kb.get_entries_by_category("contact")
        return {e.get("content", "").lower() for e in entries}

    def _ask(self, todo_id: str, field: str, question: str) -> Dict[str, Any]:
        return {
            "tool": "ask_clarification",
            "params": {
                "todo_id": todo_id,
                "field": field,
                "question": question,
            },
            "agent": "email_agent",
            "status": "needs_info",
        }

    def _question(self, field: str) -> str:
        return {
            "to": "Who should I send this email to?",
            "subject": "What should the subject be?",
            "body": "What should the email say?",
        }.get(field, f"Please provide {field}.")