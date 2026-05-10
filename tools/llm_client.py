

"""
tools/llm_client.py — The Core Intelligence Module for Alfred.

Handles inference via:
1. HuggingFace Inference API (Primary)
2. Cursor API (Fallback)

ALFRED PROTOCOL: All logic and decision-making are grounded in this centralized brain.
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)



DEFAULT_HF_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_CURSOR_MODEL = "gpt-4o-mini"
MAX_NEW_TOKENS = 256


class LLMClient:
    """
    Unified Intelligence client for the Alfred ecosystem.

    Priority order:
    1. HuggingFace (hf_token required)
    2. Cursor (cursor_api_key required)
    3. Null Fallback
    """

    def __init__(self):
        self._hf_token = os.environ.get("HF_TOKEN")
        self._cursor_key = os.environ.get("CURSOR_API_KEY")
        self._hf_model = os.environ.get("HF_INFERENCE_MODEL", DEFAULT_HF_MODEL)
        self._cursor_model = os.environ.get("CURSOR_MODEL", DEFAULT_CURSOR_MODEL)
        self._hf_client = None
        self._provider = self._detect_provider()
        self.identity = "Alfred_Cortex"

    def _detect_provider(self) -> str:
        """Determines which neural pathway is active."""
        if self._hf_token and self._hf_token.startswith("hf_"):
            logger.info("Alfred Intelligence: HuggingFace Active (%s)", self._hf_model)
            return "huggingface"
        if self._cursor_key:
            logger.info("Alfred Intelligence: Cursor Active (%s)", self._cursor_model)
            return "cursor"
        logger.warning("No Intelligence API keys found. Alfred is operating in limited mode.")
        return "fallback"

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def is_available(self) -> bool:
        return self._provider != "fallback"

    def reload_intelligence(self):
        """Reloads API keys if environmental variables are updated."""
        self._hf_token = os.environ.get("HF_TOKEN")
        self._cursor_key = os.environ.get("CURSOR_API_KEY")
        self._hf_model = os.environ.get("HF_INFERENCE_MODEL", DEFAULT_HF_MODEL)
        self._cursor_model = os.environ.get("CURSOR_MODEL", DEFAULT_CURSOR_MODEL)
        self._hf_client = None
        self._provider = self._detect_provider()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = MAX_NEW_TOKENS,
        temperature: float = 0.7,
    ) -> str:
        """
        Processes a thought request through the active intelligence provider.
        """
        if self._provider == "huggingface":
            return self._generate_hf(system_prompt, user_prompt, max_tokens, temperature)
        elif self._provider == "cursor":
            return self._generate_cursor(system_prompt, user_prompt, max_tokens, temperature)
        else:
            return ""

    def _generate_hf(
        self, system_prompt: str, user_prompt: str,
        max_tokens: int, temperature: float
    ) -> str:
        """Neural processing via HuggingFace Hub."""
        try:
            from huggingface_hub import InferenceClient

            if self._hf_client is None:
                self._hf_client = InferenceClient(token=self._hf_token)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self._hf_client.chat_completion(
                model=self._hf_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content
            return content.strip()

        except Exception as e:
            logger.error("Alfred Neural (HF) Error: %s", str(e))
            if self._cursor_key:
                return self._generate_cursor(system_prompt, user_prompt, max_tokens, temperature)
            return ""

    def _generate_cursor(
        self, system_prompt: str, user_prompt: str,
        max_tokens: int, temperature: float
    ) -> str:
        """Neural processing via Cursor (OpenAI-compatible)."""
        try:
            import urllib.request
            url = "https://api.cursor.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self._cursor_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self._cursor_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error("Alfred Neural (Cursor) Error: %s", str(e))
            return ""

    def get_status(self) -> dict:
        """Returns the current state of Alfred's intelligence module."""
        return {
            "identity": self.identity,
            "provider": self._provider,
            "is_active": self.is_available,
        }


_alfred_intelligence: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Access Alfred's centralized cortex."""
    global _alfred_intelligence
    if _alfred_intelligence is None:
        _alfred_intelligence = LLMClient()
    return _alfred_intelligence