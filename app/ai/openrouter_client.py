"""
Thin async wrapper around the OpenRouter API (OpenAI-compatible schema),
used as the automatic fallback (or primary, if Gemini key is absent).
Tries the configured primary free model first, then walks through any
configured fallback models on failure/rate-limit.
"""
from __future__ import annotations

import httpx

from app.ai.prompts import SYSTEM_PROMPT
from app.config import settings
from app.logger import logger

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.openrouter_api_key)
        self.models = [settings.openrouter_model] + [
            m for m in settings.openrouter_fallback_models if m and m != settings.openrouter_model
        ]

    async def generate(self, prompt: str, temperature: float = 0.4, max_tokens: int = 4096) -> str:
        if not self.enabled:
            raise RuntimeError("OpenRouter client is not configured (missing OPENROUTER_API_KEY).")

        last_error: Exception | None = None
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "AI Resume Tailor Bot",
        }

        async with httpx.AsyncClient(timeout=90) as client:
            for model in self.models:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                try:
                    resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        logger.warning(
                            "OpenRouter model {} returned status {}: {}",
                            model, resp.status_code, resp.text[:300],
                        )
                        last_error = RuntimeError(f"OpenRouter {model} status {resp.status_code}")
                except Exception as e:
                    logger.warning("OpenRouter model {} failed: {}", model, e)
                    last_error = e

        raise last_error or RuntimeError("All OpenRouter models failed.")
