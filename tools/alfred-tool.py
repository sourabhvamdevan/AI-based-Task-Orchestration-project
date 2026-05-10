

"""
tools/kb_tool.py — The Archivist Module for Alfred.

Manages alfred_kb.json — the core file-based knowledge store.
ALFRED PROTOCOL: Never records information without Master's explicit consent.
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Renamed to stay consistent with Alfred's memory ecosystem
DEFAULT_KB_PATH = "alfred_kb.json"

VALID_CATEGORIES = {
    "meeting", "email", "preference",
    "contact", "user_profile", "habit",
}


class KBTool:
    """
    Manages the Knowledge Base for the Alfred ecosystem.
    Acts as the long-term memory for all Butler agents.
    """

    def __init__(self, kb_path: str = None):
        self.kb_path = kb_path or os.environ.get(
            "ALFRED_KB_PATH", DEFAULT_KB_PATH
        )
        self.tool_name = "Alfred_Archivist"
        self._ensure_kb_exists()

    def _ensure_kb_exists(self):
        """Initializes the memory file if it's the first time running."""
        if not os.path.exists(self.kb_path):
            self._write_kb({"entries": [], "user_profile": {}})

    def _read_kb(self) -> dict:
        """Reads Alfred's memory bank from disk."""
        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"entries": [], "user_profile": {}}

    def _write_kb(self, data: dict):
        """Commits memory updates to disk."""
        with open(self.kb_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_entry(
        self,
        content: str,
        category: str,
        source: str = "Alfred_Internal",
        user_consented: bool = False,
    ) -> dict:
        """
        Records a new memory.
        CRITICAL: Consent-gated write operation.
        """
        if not user_consented:
            return {
                "status": "error",
                "message": "Master, I require your consent before recording this information.",
            }

        if category not in VALID_CATEGORIES:
            return {
                "status": "error",
                "message": f"Invalid memory category: '{category}'.",
            }

        try:
            kb = self._read_kb()
            entry = {
                "id": uuid.uuid4().hex[:12],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "category": category,
                "source": source,
                "content": content,
            }
            kb["entries"].append(entry)
            self._write_kb(kb)

            logger.info("Alfred recorded new memory: %s", entry["id"])
            return {
                "status": "success",
                "entry_id": entry["id"],
                "category": category,
            }

        except Exception as e:
            logger.error("Alfred memory write error: %s", str(e))
            return {"status": "error", "message": str(e)}

    def query(self, question: str, top_k: int = 5) -> list[dict]:
        """
        Recalls information using keyword overlap scoring.
        """
        try:
            kb = self._read_kb()
            entries = kb.get("entries", [])

            if not entries:
                return []

            # Stopwords to filter out noise from the query
            stopwords = {
                "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", 
                "in", "for", "on", "with", "at", "by", "what", "who", "where"
            }
            q_tokens = set(
                w for w in question.lower().split()
                if w not in stopwords and len(w) > 1
            )

            if not q_tokens:
                return entries[:top_k]

            # Relevance scoring
            scored = []
            for entry in entries:
                content_lower = entry.get("content", "").lower()
                category_lower = entry.get("category", "").lower()
                score = sum(
                    1 for token in q_tokens
                    if token in content_lower or token in category_lower
                )
                if score > 0:
                    scored.append((score, entry))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [entry for _, entry in scored[:top_k]]

        except Exception as e:
            logger.error("Alfred memory recall error: %s", str(e))
            return []

    def get_user_profile(self) -> dict:
        """Retrieves the Master's profile."""
        kb = self._read_kb()
        return kb.get("user_profile", {})

    def save_user_profile(
        self,
        profile: dict,
        user_consented: bool = False,
    ) -> dict:
        """Saves Master's profile details to long-term memory."""
        if not user_consented:
            return {
                "status": "error",
                "message": "Consent required to update profile.",
            }

        try:
            kb = self._read_kb()
            kb["user_profile"] = profile
            self._write_kb(kb)
            return {"status": "success", "profile": profile}

        except Exception as e:
            logger.error("Alfred profile update error: %s", str(e))
            return {"status": "error", "message": str(e)}

    def get_entries_by_category(self, category: str) -> list[dict]:
        """Filters memories by category (e.g., all habits)."""
        kb = self._read_kb()
        return [
            e for e in kb.get("entries", [])
            if e.get("category") == category
        ]

    def get_all_entries(self) -> list[dict]:
        """Retrieves all stored records."""
        kb = self._read_kb()
        return kb.get("entries", [])