"""
ATS Analyzer: combines AI-generated scoring with lightweight local
formatting checks (things a rules engine catches more reliably than
an LLM, e.g. presence of tables/images that break real ATS parsers).
"""
from __future__ import annotations

import re

from app.ai.engine import ai_engine
from app.ai.prompts import ATS_REPORT_PROMPT


def local_formatting_checks(resume_text: str) -> list[str]:
    issues = []
    if len(resume_text) < 400:
        issues.append("Resume content seems very short — ATS systems may not find enough context.")
    if not re.search(r"@[\w\.-]+\.\w+", resume_text):
        issues.append("No email address detected — make sure your contact email is in plain text.")
    if not re.search(r"\d{3}[\s\-\)]*\d{3}[\s\-]*\d{4}", resume_text) and not re.search(r"\+\d{1,3}[\s\-]?\d{6,12}", resume_text):
        issues.append("No phone number detected in a standard format.")
    if resume_text.count("\t") > 40:
        issues.append("Heavy use of tabs detected — some ATS parsers mis-read tab-based layouts.")
    return issues


async def run_ats_analysis(resume_text: str, jd_text: str) -> dict:
    prompt = ATS_REPORT_PROMPT.format(resume_text=resume_text[:12000], jd_text=jd_text[:8000])
    report = await ai_engine.generate_json(prompt, temperature=0.2, max_tokens=2000)

    local_issues = local_formatting_checks(resume_text)
    existing = report.get("formatting_issues") or []
    report["formatting_issues"] = list(dict.fromkeys(existing + local_issues))  # dedupe, preserve order

    # Clamp scores defensively
    for key in (
        "overall_score", "keyword_match_score", "skills_match_score",
        "experience_match_score", "formatting_score",
    ):
        val = report.get(key)
        if isinstance(val, (int, float)):
            report[key] = max(0, min(100, int(val)))
        else:
            report[key] = 0

    return report
