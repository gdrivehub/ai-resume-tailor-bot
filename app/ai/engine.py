"""
AI Engine — the single entry point the rest of the bot uses to talk to AI.

Priority logic (as required):
- If GEMINI_API_KEY is set (non-empty)  -> Gemini is PRIMARY, OpenRouter is fallback.
- If GEMINI_API_KEY is blank/missing    -> OpenRouter is used automatically as PRIMARY.
- If a provider fails or hits a rate limit, the engine automatically falls
  back to whichever provider is left, with retry/backoff via tenacity.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.ai.gemini_client import GeminiClient
from app.ai.openrouter_client import OpenRouterClient
from app.config import settings
from app.logger import logger


class AIEngineError(Exception):
    pass


class NoProviderConfiguredError(AIEngineError):
    pass


class AIEngine:
    def __init__(self) -> None:
        self.gemini = GeminiClient()
        self.openrouter = OpenRouterClient()

        if not self.gemini.enabled and not self.openrouter.enabled:
            logger.error("No AI provider configured! Set GEMINI_API_KEY or OPENROUTER_API_KEY.")

        self.primary = "gemini" if self.gemini.enabled else ("openrouter" if self.openrouter.enabled else None)
        logger.info(
            "AI Engine initialized. Primary provider: {} | Gemini enabled: {} | OpenRouter enabled: {}",
            self.primary, self.gemini.enabled, self.openrouter.enabled,
        )

    async def _call_provider(self, provider: str, prompt: str, temperature: float, max_tokens: int) -> str:
        if provider == "gemini":
            return await self.gemini.generate(prompt, temperature, max_tokens)
        elif provider == "openrouter":
            return await self.openrouter.generate(prompt, temperature, max_tokens)
        raise AIEngineError(f"Unknown provider: {provider}")

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=6),
        retry=retry_if_exception_type(Exception),
    )
    async def _call_with_retry(self, provider: str, prompt: str, temperature: float, max_tokens: int) -> str:
        return await self._call_provider(provider, prompt, temperature, max_tokens)

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generates raw text using the primary provider, automatically
        falling back to the secondary provider on any failure.
        """
        if not self.primary:
            raise NoProviderConfiguredError(
                "No AI provider is configured. Please set GEMINI_API_KEY or "
                "OPENROUTER_API_KEY in your .env file."
            )

        order = [self.primary]
        secondary = "openrouter" if self.primary == "gemini" else "gemini"
        if getattr(self, secondary).enabled:
            order.append(secondary)

        last_error: Optional[Exception] = None
        for provider in order:
            try:
                logger.debug("Attempting AI generation via provider={}", provider)
                return await self._call_with_retry(provider, prompt, temperature, max_tokens)
            except Exception as e:
                logger.warning("Provider {} failed after retries: {}", provider, e)
                last_error = e
                continue

        raise AIEngineError(f"All AI providers failed. Last error: {last_error}")

    async def generate_json(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """
        Generates a response and parses it as JSON, stripping markdown
        fences and other common formatting artifacts models add despite
        instructions.
        """
        raw = await self.generate_text(prompt, temperature=temperature, max_tokens=max_tokens)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        # Strip ```json ... ``` or ``` ... ``` fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract the largest {...} block as a fallback
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                logger.error("Failed to parse AI JSON response even after extraction: {}", e)
                raise AIEngineError(f"AI returned invalid JSON: {e}") from e

        raise AIEngineError("AI response did not contain valid JSON.")


# Singleton instance used across the app
ai_engine = AIEngine()
