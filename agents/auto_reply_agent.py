


import logging
from typing import Any, Dict, List, Optional

from tools.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class AutoReplyAgent:
    TIER = "TIER2_PROFESSIONAL"

    def __init__(self, gmail_tool: Optional[Any] = None, kb_tool: Optional[Any] = None):
        self._gmail = gmail_tool
        self._kb = kb_tool

    def set_tools(self, gmail_tool: Optional[Any] = None, kb_tool: Optional[Any] = None) -> None:
        if gmail_tool is not None:
            self._gmail = gmail_tool
        if kb_tool is not None:
            self._kb = kb_tool

    def run_automation_cycle(self, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logs: List[Dict[str, Any]] = []
        user_name = user_context.get("name", "User")

        if not self._gmail:
            return [{"status": "error", "message": "Gmail tool not configured."}]

        fetch_result = self._gmail.fetch_unread(max_results=3, days_back=1)
        if fetch_result.get("status") != "success":
            return [{"status": "error", "message": "Failed to fetch inbox."}]

        emails = fetch_result.get("emails", [])
        if not emails:
            return [{"status": "info", "message": "Inbox zero."}]

        client = get_llm_client()
        if not client or not client.is_available:
            return [{"status": "error", "message": "LLM client unavailable."}]

        for email in emails:
            log = self._process_email(email, client, user_name)
            logs.append(log)

        return logs

    def _process_email(self, email: Dict[str, Any], client: Any, user_name: str) -> Dict[str, Any]:
        subject = email.get("subject", "No Subject")
        sender = email.get("sender", "Unknown")
        snippet = email.get("snippet", "")

        kb_context = self._build_kb_context(subject, snippet)

        draft = self._generate_reply(client, user_name, sender, subject, snippet, kb_context)
        if not draft:
            return {"status": "error", "message": f"Draft generation failed for {sender}."}

        send_result = self._gmail.send_email(
            to=sender,
            subject=f"Re: {subject}",
            body=draft
        )

        if send_result.get("status") == "success":
            return {
                "status": "success",
                "message": f"Auto-replied to {sender}.",
                "draft": draft
            }

        return {"status": "error", "message": f"Failed to send email to {sender}."}

    def _build_kb_context(self, subject: str, snippet: str) -> str:
        if not self._kb:
            return ""

        results = self._kb.query(f"{snippet} {subject}", top_k=3)
        if not results:
            return ""

        return "\n".join(
            f"- [{r.get('category', '?')}] {r.get('content', '')}"
            for r in results
        )

    def _generate_reply(
        self,
        client: Any,
        user_name: str,
        sender: str,
        subject: str,
        snippet: str,
        kb_context: str
    ) -> Optional[str]:
        system_prompt = (
            f"You are Butler, an autonomous AI assistant for {user_name}. "
            "Write a concise, professional reply to an email. "
            "Use the provided knowledge base context if relevant. "
            "If unsure, state that the query will be escalated for human review. "
            "Sign as 'Butler (AI Assistant)'."
        )

        user_prompt = (
            f"Knowledge Base Context:\n{kb_context}\n\n"
            f"Incoming Email:\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Snippet: {snippet}\n\n"
            "Reply:"
        )

        return client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=250,
            temperature=0.3
        )