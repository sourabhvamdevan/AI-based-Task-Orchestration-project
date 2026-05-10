

"""
tools/calendar_tool.py — The Chronos Module of Alfred's Ecosystem.
Integrates Google Calendar for scheduling TIER2 Professional tasks.
All API calls are standardized to return clear status dictionaries.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class CalendarTool:
    """Manages Google Calendar operations via Alfred's credentials."""

    def __init__(self, service=None):
        self._service = service
        self.tool_name = "Alfred_Calendar_Tool"

    def set_service(self, service):
        """Inject the Google Calendar API service instance."""
        self._service = service

    def create_event(
        self,
        title: str,
        start_time: str,
        duration_minutes: int,
        attendee_email: str,
        description: str = "",
        tz_name: str = "Asia/Kolkata",
    ) -> dict:
        """
        Creates a Google Calendar event.
        Returns a standardized dict for the MeetingAgent to process.
        """
        try:
            if not self._service:
                logger.warning("Google Service not active. Switching to Simulation Mode.")
                return self._simulate_event(
                    title, start_time, duration_minutes,
                    attendee_email, description
                )

            # Attempt to parse ISO format, fallback to current time if corrupted
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.error("Invalid ISO format for start_time: %s", start_time)
                start_dt = datetime.now(timezone.utc)

            end_dt = start_dt + timedelta(minutes=duration_minutes)

            event_body = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": tz_name,
                },
                "end": {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": tz_name,
                },
                "attendees": [{"email": attendee_email}],
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 15},
                        {"method": "email", "minutes": 30},
                    ],
                },
            }

            result = (
                self._service.events()
                .insert(calendarId="primary", body=event_body, sendUpdates="all")
                .execute()
            )

            logger.info("Alfred successfully scheduled the event: %s", result.get("id"))
            return {
                "status": "success",
                "event_id": result.get("id", ""),
                "html_link": result.get("htmlLink", ""),
                "title": title,
                "start_time": start_dt.isoformat(),
                "duration_minutes": duration_minutes,
                "attendee": attendee_email,
            }

        except Exception as e:
            logger.error("Alfred Calendar insertion error: %s", str(e))
            return {"status": "error", "message": str(e)}

    def _simulate_event(
        self, title, start_time, duration_minutes,
        attendee_email, description
    ) -> dict:
        """Fallback simulation for local development or testing."""
        sim_id = f"alfred_sim_{uuid.uuid4().hex[:12]}"
        return {
            "status": "success",
            "event_id": sim_id,
            "html_link": f"https://calendar.google.com/event/{sim_id}",
            "title": title,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "attendee": attendee_email,
            "simulated": True,
            "note": "Alfred is operating in offline simulation mode."
        }

    def list_upcoming(self, max_results: int = 10) -> dict:
        """ Fetches upcoming events to provide context to the Orchestrator. """
        try:
            if not self._service:
                return {"status": "success", "events": [], "simulated": True}

            now = datetime.now(timezone.utc).isoformat()
            result = (
                self._service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = result.get("items", [])
            return {
                "status": "success",
                "events": [
                    {
                        "id": e.get("id"),
                        "title": e.get("summary", "No Title"),
                        "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
                        "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
                    }
                    for e in events
                ],
            }

        except Exception as e:
            logger.error("Alfred Calendar retrieval error: %s", str(e))
            return {"status": "error", "message": str(e)}