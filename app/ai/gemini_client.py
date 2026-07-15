"""
Thin async wrapper around Google Gemini API using the current
`google-genai` SDK (the legacy `google-generativeai` package is
deprecated and is intentionally not used here).
"""
from __future__ import annotations

from google import genai
from google.genai import types

from app.ai.prompts import SYSTEM_PROMPT
from app.config import settings
from app.logger import logger


class GeminiClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.gemini_api_key)
        self.client = genai.Client(api_key=settings.gemini_api_key) if self.enabled else None
        self.model_name = settings.gemini_model

    async def generate(self, prompt: str, temperature: float = 0.4, max_tokens: int = 4096) -> str:
        if not self.enabled or self.client is None:
            raise RuntimeError("Gemini client is not configured (missing GEMINI_API_KEY).")

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            text = response.text
            if not text:
                raise RuntimeError("Gemini returned an empty response.")
            return text
        except Exception as e:
            logger.warning("Gemini generation failed: {}", e)
            raise
