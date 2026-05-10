

"""
tools/gmail_tool.py — The Communication Hub of Alfred's Ecosystem.
Handles Gmail operations including sending, fetching, and thread tracking.
ALFRED PROTOCOL: All communications are sent on behalf of the Master.
"""

import base64
import logging
import uuid
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class GmailTool:
    """Manages Gmail operations for Butler via Alfred's credentials."""

    def __init__(self, service=None):
        self._service = service
        self.tool_identity = "Alfred_Gmail_Tool"

    def set_service(self, service):
        """Inject the Gmail API service instance."""
        self._service = service

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        sender: str = "me",
    ) -> dict:
        """
        Sends an email using the Gmail API.
        Standardizes the output for Butler's Agents.
        """
        try:
            if not self._service:
                logger.warning("Gmail Service not active. Simulating email dispatch.")
                return self._simulate_send(to, subject, body)

            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            
            # Gmail API expects base64url encoded string
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = (
                self._service.users()
                .messages()
                .send(userId=sender, body={"raw": raw})
                .execute()
            )

            logger.info("Alfred has dispatched the email. ID: %s", result.get("id"))
            return {
                "status": "success",
                "message_id": result.get("id", ""),
                "thread_id": result.get("threadId", ""),
                "to": to,
                "subject": subject,
            }

        except Exception as e:
            logger.error("Alfred Gmail dispatch error: %s", str(e))
            return {"status": "error", "message": str(e)}

    def _simulate_send(self, to: str, subject: str, body: str) -> dict:
        """Fallback simulation for testing without active API tokens."""
        msg_id = f"alfred_msg_{uuid.uuid4().hex[:12]}"
        return {
            "status": "success",
            "message_id": msg_id,
            "thread_id": f"thread_{msg_id}",
            "to": to,
            "subject": subject,
            "simulated": True,
            "note": "Alfred is operating in offline dispatch mode."
        }

    def send_confirmation_email(
        self,
        attendee_email: str,
        attendee_name: str,
        user_name: str,
        title: str,
        start_time: str,
        duration_minutes: int,
    ) -> dict:
        """
        Automated meeting confirmation from Alfred.
        """
        subject = f"Scheduled: {title}"
        body = (
            f"Greetings {attendee_name},\n\n"
            f"I have successfully scheduled a meeting on behalf of {user_name}.\n\n"
            f"🔹 Subject: {title}\n"
            f"🔹 Scheduled Time: {start_time}\n"
            f"🔹 Expected Duration: {duration_minutes} minutes\n\n"
            f"I have added this to the calendar. Should you need to adjust this, "
            f"please respond to this thread.\n\n"
            f"Respectfully,\n"
            f"Alfred (Butler Orchestration System)"
        )
        return self.send_email(to=attendee_email, subject=subject, body=body)

    def fetch_unread(
        self,
        max_results: int = 20,
        days_back: int = 3,
    ) -> dict:
        """
        Fetches unread messages. Useful for the 'Email Agent' to scan for tasks.
        """
        try:
            if not self._service:
                return {"status": "success", "emails": [], "simulated": True}

            # Filter for recent unread messages
            after_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")
            query = f"is:unread after:{after_date}"

            result = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = result.get("messages", [])
            emails = []

            for msg_ref in messages:
                msg = (
                    self._service.users()
                    .messages()
                    .get(userId="me", id=msg_ref["id"], format="metadata",
                         metadataHeaders=["Subject", "From", "Date"])
                    .execute()
                )

                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

                emails.append({
                    "email_id": msg["id"],
                    "thread_id": msg.get("threadId", ""),
                    "subject": headers.get("Subject", "No Subject"),
                    "sender": headers.get("From", "Unknown Sender"),
                    "snippet": msg.get("snippet", ""),
                    "received_at": headers.get("Date", ""),
                })

            return {"status": "success", "emails": emails}

        except Exception as e:
            logger.error("Alfred Gmail fetch error: %s", str(e))
            return {"status": "error", "message": str(e)}

    def check_for_reply(self, thread_id: str) -> dict:
        """ Checks if an attendee has replied to a scheduled thread. """
        try:
            if not self._service:
                return {"status": "success", "has_reply": False, "simulated": True}

            thread = self._service.users().threads().get(userId="me", id=thread_id).execute()
            messages = thread.get("messages", [])
            
            # If more than 1 message exists, someone has replied to Alfred's original mail
            return {
                "status": "success",
                "has_reply": len(messages) > 1,
                "message_count": len(messages),
                "thread_id": thread_id,
            }

        except Exception as e:
            logger.error("Alfred Gmail thread tracking error: %s", str(e))
            return {"status": "error", "message": str(e)}