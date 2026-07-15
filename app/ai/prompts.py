"""
Prompt templates for every AI operation the bot performs.
Kept separate from engine logic so prompts can be tuned without
touching provider code.
"""

SYSTEM_PROMPT = (
    "You are an expert resume writer, career coach, and ATS (Applicant "
    "Tracking System) optimization specialist. You NEVER fabricate "
    "experience, skills, employers, dates, or qualifications that are not "
    "present in the source resume. You only rephrase, reorganize, "
    "emphasize, and optimize truthful content already provided. You always "
    "return clean, well-structured output in the exact format requested."
)

KEYWORD_EXTRACTION_PROMPT = """Extract the most important ATS keywords from the job description below.
Return ONLY valid JSON, no markdown fences, no preamble, in this exact schema:
{{
  "hard_skills": ["..."],
  "soft_skills": ["..."],
  "tools_technologies": ["..."],
  "certifications": ["..."],
  "job_title_variants": ["..."],
  "top_keywords": ["..."]
}}
// top_keywords should contain 15-25 highest priority keywords ranked by importance

JOB DESCRIPTION:
{jd_text}
"""

GAP_ANALYSIS_PROMPT = """Compare the RESUME against the JOB DESCRIPTION KEYWORDS below.
Return ONLY valid JSON, no markdown fences, in this exact schema:
{{
  "matched_keywords": ["..."],
  "missing_keywords": ["..."],
  "match_percentage": 0,
  "experience_match_notes": "short paragraph",
  "skills_gap_notes": "short paragraph"
}}

RESUME:
{resume_text}

JOB DESCRIPTION KEYWORDS:
{keywords_json}
"""

TAILOR_RESUME_PROMPT = """Rewrite and optimize the RESUME below to better match the JOB DESCRIPTION,
while following these strict rules:
1. NEVER invent employers, job titles, dates, degrees, or skills the candidate does not have.
2. You MAY rephrase, reorder, and emphasize existing bullet points to better align with the job description.
3. Naturally weave in relevant keywords from the job description ONLY where truthfully applicable.
4. Rewrite the professional summary to be tightly targeted at this specific role.
5. Optimize the skills section ordering to prioritize what the job description asks for (only skills already present).
6. Keep bullet points achievement-oriented, quantified where the original data allows it.
7. Preserve section structure: Summary, Skills, Experience, Projects, Education, Certifications (only include sections present in original).
8. Keep it concise enough to fit one to two pages.

Return ONLY valid JSON, no markdown fences, in this exact schema:
{{
  "full_name": "...",
  "contact_line": "...",
  "summary": "...",
  "skills": ["..."],
  "experience": [
    {{
      "title": "...",
      "company": "...",
      "location": "...",
      "dates": "...",
      "bullets": ["...", "..."]
    }}
  ],
  "projects": [
    {{"name": "...", "description": "...", "bullets": ["..."]}}
  ],
  "education": [
    {{"degree": "...", "institution": "...", "dates": "...", "details": "..."}}
  ],
  "certifications": ["..."]
}}

ORIGINAL RESUME:
{resume_text}

TARGET JOB DESCRIPTION:
{jd_text}

TARGET COMPANY: {company}
TARGET ROLE: {role}
"""

IMPROVE_SECTION_PROMPT = """Improve ONLY the "{section}" section of the resume below to be more
impactful, quantified, and ATS-friendly, without inventing any new facts.
Return ONLY valid JSON matching this schema for the section type "{section}":
{schema_hint}

CURRENT RESUME (for context, only modify the requested section):
{resume_text}

TARGET JOB DESCRIPTION (if relevant, for context):
{jd_text}
"""

COVER_LETTER_PROMPT = """Write a compelling, concise, one-page cover letter for the candidate
below, tailored to the job description. Use a {tone} tone. Do not fabricate
experience. Address it generically ("Dear Hiring Manager") unless a hiring
manager name is present in the job description.

Return ONLY valid JSON, no markdown fences, in this exact schema:
{{
  "greeting": "...",
  "opening_paragraph": "...",
  "body_paragraphs": ["...", "..."],
  "closing_paragraph": "...",
  "signoff": "..."
}}

CANDIDATE RESUME:
{resume_text}

TARGET JOB DESCRIPTION:
{jd_text}

TARGET COMPANY: {company}
TARGET ROLE: {role}
"""

ATS_REPORT_PROMPT = """Generate a detailed ATS compatibility report comparing the RESUME to the
JOB DESCRIPTION. Return ONLY valid JSON, no markdown fences, in this exact schema:
{{
  "overall_score": 0,
  "keyword_match_score": 0,
  "skills_match_score": 0,
  "experience_match_score": 0,
  "formatting_score": 0,
  "matched_keywords": ["..."],
  "missing_keywords": ["..."],
  "formatting_issues": ["..."],
  "grammar_suggestions": ["..."],
  "actionable_recommendations": ["..."]
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}
"""

JD_PARSE_PROMPT = """Extract structured data from the job posting text below.
Return ONLY valid JSON, no markdown fences, in this exact schema:
{{
  "company": "...",
  "role": "...",
  "location": "...",
  "employment_type": "...",
  "seniority_level": "...",
  "summary": "one paragraph summary of the role"
}}

JOB POSTING TEXT:
{jd_text}
"""
