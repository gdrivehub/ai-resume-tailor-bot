# AI Resume Tailor Telegram Bot - Final Architecture & Development Report

## Overview

A public Telegram bot that helps users tailor resumes for specific job
descriptions using free AI providers. The bot stores generated files in
a private Telegram dump channel while MongoDB stores metadata and
retrieval indexes.

## Goals

-   100% free to operate (within free API limits)
-   Fast resume tailoring
-   ATS optimization
-   Resume version history
-   Cover letter generation
-   Multi-user support
-   Docker deployable
-   Oracle Cloud Always Free compatible

------------------------------------------------------------------------

# High-Level Architecture

``` text
Telegram User
      │
      ▼
Pyrogram Bot
      │
      ├── Authentication / Rate Limiter
      ├── Command Handler
      ├── Resume Parser
      ├── JD Parser
      ├── AI Engine
      ├── ATS Analyzer
      ├── DOCX/PDF Generator
      ├── Dump Channel Manager
      └── MongoDB Manager

AI Engine
├── Primary: Google Gemini API
└── Fallback: OpenRouter (DeepSeek/Qwen/Gemma free)

Storage
├── MongoDB (metadata)
└── Private Telegram Dump Channel (files)
```

# AI Strategy

Primary: - Google Gemini API

Fallback: - OpenRouter free models

Reasons: - Better writing quality - Long context support - Reliable free
tier - Automatic fallback if unavailable

------------------------------------------------------------------------

# Telegram Dump Channel

Store: - Original Resume - Tailored Resume - Cover Letter - ATS Report -
Analysis Report

MongoDB stores: - user_id - resume_id - resume_hash - jd_hash -
telegram_file_id - company - role - ats_score - timestamps - version

------------------------------------------------------------------------

# MongoDB Collections

users resumes job_descriptions history settings cover_letters
ats_reports analytics

------------------------------------------------------------------------

# Development Phases

## Phase 1

Project setup - Pyrogram - Docker - MongoDB - Logging - Configuration -
Admin system

## Phase 2

Resume engine - Upload resume - Parse PDF/DOCX - Store metadata - Store
original file

## Phase 3

Job description engine - /setjd - Parse JD - Keyword extraction - Save
reusable JD

## Phase 4

AI engine - Gemini integration - OpenRouter fallback - Retry logic -
Prompt templates

## Phase 5

Resume generation - Tailor summary - Rewrite experience - Optimize
skills - Preserve formatting - Generate DOCX/PDF

## Phase 6

ATS engine - Keyword match - Missing skills - Improvement suggestions -
Score calculation

## Phase 7

Cover letter engine

## Phase 8

History & retrieval

## Phase 9

Admin dashboard

## Phase 10

Optimization - Caching - Duplicate detection - Rate limiting - Queueing

------------------------------------------------------------------------

# User Flow

1.  /start
2.  /setresume
3.  Upload resume
4.  /setjd
5.  Paste JD
6.  /tailor
7.  AI processing
8.  ATS report
9.  Tailored resume generated
10. Files uploaded to dump channel
11. Metadata saved
12. Resume returned

------------------------------------------------------------------------

# Commands

## Core

/start /help /settings /profile

## Resume

/setresume /setjd /tailor /improve /history /resumes /delete

## Analysis

/ats /keywords /analyze

## Documents

/coverletter

## Admin

/stats /broadcast /users /logs

------------------------------------------------------------------------

# Improve Options

/improve summary /improve experience /improve skills /improve projects
/improve education

------------------------------------------------------------------------

# ATS Report

Include: - Overall ATS score - Keyword match - Missing keywords - Skills
match - Experience match - Formatting checks - Grammar suggestions -
Actionable recommendations

------------------------------------------------------------------------

# Version History

Each generated resume becomes a new version.

Resume V1 Resume V2 Resume V3

Never overwrite.

------------------------------------------------------------------------

# Duplicate Detection

Hash: SHA256(resume)+SHA256(JD)

If identical combination exists: Return cached file from dump channel
instead of calling AI.

------------------------------------------------------------------------

# Recommended Prompt Pipeline

1.  Parse resume
2.  Parse JD
3.  Extract keywords
4.  Analyze gaps
5.  Rewrite summary
6.  Rewrite experience
7.  Optimize skills
8.  Maintain truthful content (no fabricated experience)
9.  Produce ATS report
10. Generate DOCX/PDF
11. Generate cover letter (optional)

------------------------------------------------------------------------

# Security

-   Private dump channel
-   MongoDB indexes
-   Per-user access control
-   Rate limiting
-   Prompt sanitization
-   File validation
-   Logging

------------------------------------------------------------------------

# Recommended Tech Stack

Python 3.12+ Pyrogram MongoDB Docker python-docx PyMuPDF pdfplumber
Jinja2 Google Gemini API OpenRouter API

Hosting: Oracle Cloud Always Free VPS

------------------------------------------------------------------------

# Future Features

-   Multi-language resumes
-   LinkedIn profile optimizer
-   Interview question generator
-   Resume scoring against multiple JDs
-   Recruiter feedback simulation
-   Portfolio review
-   Job recommendation engine
-   AI interview coach
-   Email application generator

------------------------------------------------------------------------

# Final Recommendation

Use Google Gemini as the primary model with OpenRouter as an automatic
fallback. Store all generated artifacts in a private Telegram dump
channel and only metadata in MongoDB. Implement caching, duplicate
detection, version history, and reusable resumes/JDs to minimize AI
calls and improve speed.

This architecture is scalable, cost-efficient, and suitable for a public
multi-user Telegram bot while remaining compatible with free-tier
infrastructure.
