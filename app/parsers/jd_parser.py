"""
Job description text normalization + structured extraction (via AI).
"""
from __future__ import annotations

from app.ai.engine import ai_engine
from app.ai.prompts import JD_PARSE_PROMPT


def clean_jd_text(raw: str) -> str:
    text = raw.strip()
    # Collapse excessive blank lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


async def parse_jd_structured(jd_text: str) -> dict:
    """
    Uses the AI engine to pull out company / role / location etc.
    Falls back to generic placeholders if AI parsing fails so the
    pipeline never blocks on this optional metadata.
    """
    try:
        prompt = JD_PARSE_PROMPT.format(jd_text=jd_text[:6000])
        data = await ai_engine.generate_json(prompt, temperature=0.1, max_tokens=800)
        return {
            "company": data.get("company") or "Unknown Company",
            "role": data.get("role") or "Unknown Role",
            "location": data.get("location") or "",
            "employment_type": data.get("employment_type") or "",
            "seniority_level": data.get("seniority_level") or "",
            "summary": data.get("summary") or "",
        }
    except Exception:
        return {
            "company": "Unknown Company",
            "role": "Unknown Role",
            "location": "",
            "employment_type": "",
            "seniority_level": "",
            "summary": "",
        }
