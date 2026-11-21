"""Minimal optional Google Gemini client. No router command execution."""
from __future__ import annotations
import json
import logging

LOG = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str, model: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, telemetry: dict) -> str:
        # Caller must pass already-redacted aggregate telemetry only.
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt + "\n\nSanitized router metrics:\n" +
                     json.dumps(telemetry, ensure_ascii=False, separators=(",", ":")),
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text.strip()
