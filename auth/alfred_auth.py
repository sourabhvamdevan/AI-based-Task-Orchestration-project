

"""
auth/alfred_auth.py — The Auth-Gate for Butler's Google Ecosystem.
Handles the keys to the mansion (Calendar + Gmail).
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# Scopes required for Calendar and Gmail
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"


class AlfredAuthManager:
    """
    Manages Google OAuth 2.0 credentials for Butler.

    All Google API calls are wrapped in try/except and return
    {"status": "error", "message": str(e)} on failure.
    """

    def __init__(self):
        self._credentials = None
        self._calendar_service = None
        self._gmail_service = None

    def get_credentials(self):
        """
        Load or refresh OAuth credentials.

        Flow:
        1. Try loading from token.json
        2. If expired, refresh
        3. If no token, initiate auth flow

        Returns:
            Credentials object or None.
        """
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request

            creds = None

            # Load existing token
            if os.path.exists(TOKEN_PATH):
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

            # Refresh or re-auth
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    logger.info(
                        "Token refreshed via Alfred. Type: OAuth2, Expiry: %s",
                        creds.expiry.isoformat() if creds.expiry else "unknown"
                    )
                else:
                    if not os.path.exists(CREDENTIALS_PATH):
                        logger.warning(
                            "No credentials.json found. Alfred cannot access Google APIs."
                        )
                        return None

                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_PATH, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info(
                        "New token obtained by Alfred. Type: OAuth2, Expiry: %s",
                        creds.expiry.isoformat() if creds.expiry else "unknown"
                    )

                # Save token (never log the token itself)
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())

            self._credentials = creds
            return creds

        except Exception as e:
            logger.error("Alfred OAuth credential error: %s", str(e))
            return None

    def get_calendar_service(self):
        """
        Build and return Google Calendar API service.

        Returns:
            Calendar service object or None.
        """
        try:
            from googleapiclient.discovery import build

            creds = self.get_credentials()
            if not creds:
                return None

            self._calendar_service = build("calendar", "v3", credentials=creds)
            return self._calendar_service

        except Exception as e:
            logger.error("Alfred Calendar service build error: %s", str(e))
            return None

    def get_gmail_service(self):
        """
        Build and return Gmail API service.

        Returns:
            Gmail service object or None.
        """
        try:
            from googleapiclient.discovery import build

            creds = self.get_credentials()
            if not creds:
                return None

            self._gmail_service = build("gmail", "v1", credentials=creds)
            return self._gmail_service

        except Exception as e:
            logger.error("Alfred Gmail service build error: %s", str(e))
            return None

    def is_authenticated(self) -> bool:
        """Check if Alfred has valid credentials."""
        creds = self.get_credentials()
        return creds is not None and creds.valid

    def get_auth_status(self) -> dict:
        """
        Return auth status info (never includes tokens).

        Returns:
            {"authenticated": bool, "expiry": str or None}
        """
        creds = self.get_credentials()
        if creds and creds.valid:
            return {
                "authenticated": True,
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            }
        return {"authenticated": False, "expiry": None}


# Module-level singleton
_alfred_manager: Optional[AlfredAuthManager] = None


def get_alfred_manager() -> AlfredAuthManager:
    """Get or create the singleton Alfred manager."""
    global _alfred_manager
    if _alfred_manager is None:
        _alfred_manager = AlfredAuthManager()
    return _alfred_manager
