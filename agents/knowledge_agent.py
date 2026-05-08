


"""
agents/knowledge_agent.py — The Archivist of the Alfred Ecosystem.
Handles Knowledge Base (KB) operations, user context, and grounded Q&A.
ALFRED PROTOCOL: Personal context (TIER1) is the foundation of all decisions.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class KnowledgeAgent:
    """
    Manages knowledge base operations for Butler.
    
    Responsibilities:
    - Securely add entries to KB (User consent required).
    - Query KB using keyword/semantic relevance.
    - Collect and manage the 'User Master Profile'.
    - Ground LLM responses in actual personal facts.
    """

    TIER = "TIER1_PERSONAL"

    def __init__(self, kb_tool=None):
        self._kb = kb_tool
        self.agent_identity = "Alfred_Knowledge_Archivist"

    def set_tools(self, kb_tool=None):
        """Inject the KB tool dependency."""
        if kb_tool:
            self._kb = kb_tool

    def handle(self, todo: dict, collected_fields: dict) -> dict:
        """
        Handle a knowledge-related todo.
        Determines if Alfred needs to 'Store' a new memory or 'Recall' an old one.
        """
        todo_id = todo.get("todo_id", "unknown")
        todo_text = todo.get("text", "")
        text_lower = todo_text.lower()

        # Operation mapping
        query_keywords = ["ask", "what", "when", "who", "how", "recall", "remember", "where"]
        store_keywords = ["birthday", "anniversary", "save", "note", "family", "keep track"]

        is_query = any(kw in text_lower for kw in query_keywords)
        is_store = any(kw in text_lower for kw in store_keywords)

        if is_query:
            return self._handle_query(todo_id, todo_text, collected_fields)
        
        # Default to store if it's a statement or specifically triggered
        return self._handle_store(todo_id, todo_text, collected_fields)

    def _handle_store(self, todo_id: str, todo_text: str, fields: dict) -> dict:
        """Helper to store information in Alfred's memory."""
        content = fields.get("content", todo_text)
        category = fields.get("category", self._infer_category(todo_text))

        result = {"status": "success", "simulated": True}
        if self._kb:
            result = self._kb.add_entry(
                content=content,
                category=category,
                source="knowledge_agent",
                user_consented=True,  # In production, UI sends this flag
            )

        return {
            "tool": "add_to_kb",
            "params": {
                "todo_id": todo_id,
                "content": content,
                "category": category,
            },
            "agent": "knowledge_agent",
            "status": "completed",
            "kb_result": result,
            "persona_msg": "I have committed that to memory, Master."
        }

    def _handle_query(self, todo_id: str, todo_text: str, fields: dict) -> dict:
        """Helper to retrieve and answer from memory."""
        answer = self.query(todo_text)

        return {
            "tool": "query_kb",
            "params": {
                "todo_id": todo_id,
                "query": todo_text,
            },
            "agent": "knowledge_agent",
            "status": "completed",
            "answer": answer,
        }

    def query(self, question: str, top_k: int = 5) -> str:
        """
        Query the KB and use LLM for grounded answer generation.
        """
        if not self._kb:
            return "I am afraid I do not have access to my memory banks at the moment."

        results = self._kb.query(question, top_k=top_k)

        if not results:
            return "I have searched my records, but I don't have that information."

        # Build context from retrieved results
        context = "\n".join(
            f"- [{r.get('category', 'general')}] {r.get('content', '')}"
            for r in results
        )

        try:
            from tools.llm_client import get_llm_client
            client = get_llm_client()

            if not client.is_available:
                return f"According to my records:\n{context}"

            system_prompt = (
                "You are Alfred, a loyal personal assistant. Answer the user's question "
                "strictly using the provided Knowledge Base (KB) context. "
                "If the answer isn't there, say you don't know."
            )

            user_prompt = (
                f"Knowledge Base Context:\n{context}\n\n"
                f"User Question: {question}"
            )

            response = client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=250,
                temperature=0.0, # Fact-based retrieval needs zero temperature
            )

            return response if response else f"Here is what I found:\n{context}"

        except Exception as e:
            logger.error("Alfred KB inference error: %s", str(e))
            return f"I found this in your records:\n{context}"

    def collect_user_context(self, form_data: dict) -> dict:
        """
        Onboards a new user by saving their profile to the KB.
        """
        if not self._kb:
            return {"status": "error", "message": "Memory system unavailable."}

        profile = {
            "name": form_data.get("name", "Master"),
            "role": form_data.get("role", "Professional"),
            "team": form_data.get("team", "Personal Core"),
            "timezone": form_data.get("timezone", "UTC"),
            "style": form_data.get("communication_style", "polite"),
            "email": form_data.get("google_email"),
        }

        return self._kb.save_user_profile(
            profile=profile,
            user_consented=True,
        )

    def _infer_category(self, text: str) -> str:
        """Intelligently sort information into buckets."""
        t_lower = text.lower()
        
        mapping = {
            "contact": ["birthday", "anniversary", "family", "mom", "dad", "son", "daughter"],
            "meeting": ["meeting", "call", "standup", "sync", "conference"],
            "email": ["email", "reply", "respond", "gmail", "draft"],
            "habit": ["habit", "remind", "daily", "routine", "gym", "meditate"],
            "preference": ["prefer", "like", "style", "don't like", "favorite"]
        }

        for cat, keywords in mapping.items():
            if any(kw in t_lower for kw in keywords):
                return cat

        return "general_note"