# 🤖 AI Resume Tailor Bot

A free, AI-powered Telegram bot that tailors your resume to any job description, generates ATS compatibility reports, writes cover letters, and keeps version history — all stored using MongoDB (metadata) + a private Telegram channel (files), so it costs **$0** to run within free API/hosting limits.

Built with **Pyrogram**, **MongoDB**, **Google Gemini** (primary AI) with automatic **OpenRouter** fallback, and deployable via **Docker** to any VPS, **Koyeb**, or **Render**.

---

## ✨ Features

- 📄 Upload resume (PDF / DOCX / TXT) → parsed and stored
- 📋 Paste any job description → auto-extracts company, role, keywords
- 🎯 `/tailor` — AI rewrites your resume to match the JD (never fabricates experience)
- 📊 `/ats` — full ATS compatibility scoring report (keyword match, formatting issues, recommendations)
- 🔑 `/keywords` — extract top ATS keywords from a JD
- 🧩 `/analyze` — gap analysis between your resume and the JD
- ✍️ `/coverletter` — AI-generated, tailored cover letter
- 🛠 `/improve` — improve one section at a time (summary, experience, skills, projects, education)
- 🕘 `/history` — every tailored resume is versioned and retrievable, never overwritten
- ♻️ Duplicate detection — identical resume+JD combos are served from cache instantly (no wasted AI calls)
- ⚙️ `/settings` — choose tone (professional/confident/friendly) and output format (DOCX/PDF/both)
- 👑 Admin dashboard — `/stats`, `/broadcast`, `/users`, `/ban`, `/logs`
- 🔁 **Automatic AI provider fallback**: uses Gemini if `GEMINI_API_KEY` is set, otherwise automatically uses OpenRouter — and if Gemini fails mid-request (rate limit, downtime), it falls back to OpenRouter automatically, and vice versa.
- 🐳 Production-grade multi-stage Docker image, optimized for low memory/CPU use on free-tier hosts.

---

## 🧱 Architecture

```
Telegram User
      │
      ▼
Pyrogram Bot (Client)
      │
      ├── Rate Limiter / Auth
      ├── Command Handlers (start, resume, jd, tailor, ats, coverletter, improve, history, admin)
      ├── Resume Parser (pdfplumber / PyMuPDF / python-docx)
      ├── JD Parser (AI-assisted structured extraction)
      ├── AI Engine (Gemini primary → OpenRouter fallback, with retries)
      ├── ATS Analyzer (AI scoring + local formatting checks)
      ├── DOCX / PDF Generator (python-docx / ReportLab)
      └── Dump Channel Manager (stores files in a private Telegram channel)

Storage
  ├── MongoDB — metadata, hashes, history, settings, analytics
  └── Private Telegram Channel — actual resume/cover-letter/report files
```

Full original architecture notes are in [`AI_Resume_Tailor_Bot_Architecture_Report.md`](./AI_Resume_Tailor_Bot_Architecture_Report.md) (kept in the repo for reference).

---

## 📁 Project Structure

```
resume_tailor_bot/
├── app/
│   ├── config.py            # Loads & validates all environment variables
│   ├── logger.py            # Centralized loguru logging
│   ├── bot.py                # Builds Pyrogram Client, startup checks
│   ├── health_server.py      # aiohttp health endpoint for Koyeb/Render
│   ├── database/
│   │   ├── mongo.py          # MongoDB connection + indexes
│   │   └── models.py         # All DB read/write functions
│   ├── ai/
│   │   ├── engine.py         # Provider routing, retries, JSON parsing
│   │   ├── gemini_client.py
│   │   ├── openrouter_client.py
│   │   └── prompts.py        # All prompt templates
│   ├── parsers/
│   │   ├── resume_parser.py  # PDF/DOCX/TXT text extraction
│   │   └── jd_parser.py
│   ├── generators/
│   │   ├── docx_generator.py # Resume / cover letter / ATS report DOCX
│   │   └── pdf_generator.py  # Resume PDF (ReportLab)
│   ├── ats/
│   │   └── analyzer.py
│   ├── storage/
│   │   └── dump_channel.py   # Telegram-channel-as-storage manager
│   ├── handlers/              # One file per command group
│   └── utils/                 # Hashing, rate limiting, validation, state
├── main.py                    # Entry point
├── requirements.txt
├── Dockerfile                 # Multi-stage, optimized, non-root
├── docker-compose.yml
├── Procfile                   # For Render/Koyeb worker deployment
├── render.yaml                # Render Blueprint (optional one-click)
├── .env.example
└── README.md
```

---

## 🚀 Installation Guide

### Prerequisites

You will need, all free:

1. **Telegram API credentials** — `API_ID` and `API_HASH` from https://my.telegram.org
2. **A Telegram Bot Token** — from [@BotFather](https://t.me/BotFather) (`/newbot`)
3. **A private Telegram channel** for file storage (the "dump channel")
4. **MongoDB Atlas free cluster** — https://www.mongodb.com/cloud/atlas/register
5. **At least one AI API key** (both are free-tier):
   - Google Gemini: https://aistudio.google.com/app/apikey
   - OpenRouter: https://openrouter.ai/keys
6. Python 3.12+ (only if running without Docker) or Docker + Docker Compose

---

### Step 1 — Get Telegram credentials

1. Go to https://my.telegram.org → log in → **API Development Tools** → create an app.
   Copy your **`API_ID`** and **`API_HASH`**.
2. Open Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot`, follow the prompts.
   Copy the **bot token** it gives you (looks like `123456789:AAExxxxx...`).
3. Message [@userinfobot](https://t.me/userinfobot) to get your own numeric Telegram user ID — you'll use this as an admin ID.

### Step 2 — Create the private dump channel

1. In Telegram, create a **new private channel** (any name, e.g. "Resume Bot Storage").
2. Add your bot as an **Administrator** of that channel, with at least **"Post Messages"** permission.
3. You need the channel's numeric ID (looks like `-1001234567890`). Easiest way:
   - Deploy the bot first with a placeholder `DUMP_CHANNEL_ID=-1001234567890` and start it (steps below).
   - Message the bot in DM, forward any message from the dump channel to it, and run `/getchannelid` (admin-only) — it will reply with the real ID.
   - Put that ID into `.env` as `DUMP_CHANNEL_ID` and restart the bot.
   - *(Alternative: use any "get channel id" Telegram bot such as @JsonDumpBot on a forwarded message.)*

### Step 3 — Set up MongoDB Atlas (free)

1. Create a free cluster at https://www.mongodb.com/cloud/atlas/register.
2. Under **Database Access**, create a user with a password.
3. Under **Network Access**, add `0.0.0.0/0` (allow from anywhere) — required for VPS/Koyeb/Render deployments with dynamic IPs.
4. Click **Connect → Drivers**, copy the connection string, and use it as `MONGO_URI`.

### Step 4 — Get your AI API key(s)

- **Gemini (recommended primary):** https://aistudio.google.com/app/apikey → "Create API Key". Free tier is generous and has the best writing quality.
- **OpenRouter (fallback or primary):** https://openrouter.ai/keys → create a key. Free models like `deepseek/deepseek-chat-v3-0324:free` work well.

You only need **one** of these — but having both gives you automatic failover.

> **Priority logic:** if `GEMINI_API_KEY` is set, Gemini is used first and OpenRouter is only used as a fallback if Gemini fails or hits a rate limit. If `GEMINI_API_KEY` is left blank, the bot automatically uses OpenRouter as the primary provider — no code changes needed.

### Step 5 — Clone and configure the repo

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
cp .env.example .env
```

Now open `.env` in an editor and fill in every value described above:

```env
API_ID=123456
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ADMINS=111111111
DUMP_CHANNEL_ID=-1001234567890
MONGO_URI=mongodb+srv://user:pass@cluster0.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=resume_tailor_bot
GEMINI_API_KEY=your_gemini_key_or_leave_blank
OPENROUTER_API_KEY=your_openrouter_key_or_leave_blank
```

---

## 🐳 Option A — Run with Docker (recommended, any VPS)

```bash
docker compose up -d --build
```

- Logs: `docker compose logs -f`
- Stop: `docker compose down`
- Update after pulling new code: `docker compose up -d --build`

The container runs as a non-root user, has a built-in health check, and is memory/CPU capped in `docker-compose.yml` (edit the `deploy.resources.limits` block to match your VPS specs).

### Run with plain `docker run` (no compose)

```bash
docker build -t ai-resume-tailor-bot .
docker run -d --name resume-bot --env-file .env -p 8080:8080 --restart unless-stopped ai-resume-tailor-bot
```

---

## 🖥️ Option B — Run directly with Python (VPS without Docker)

```bash
python3.12 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

For a persistent VPS process, use `pm2`, `systemd`, or `screen`/`tmux`. Example systemd unit:

```ini
# /etc/systemd/system/resume-bot.service
[Unit]
Description=AI Resume Tailor Bot
After=network.target

[Service]
WorkingDirectory=/opt/resume_tailor_bot
ExecStart=/opt/resume_tailor_bot/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=/opt/resume_tailor_bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now resume-bot
sudo systemctl status resume-bot
```

---

## ☁️ Option C — Deploy to Koyeb

1. Push this repo to your own GitHub account.
2. On Koyeb → **Create Service** → **GitHub** → select your repo.
3. Builder: choose **Dockerfile**.
4. Service type: choose **Worker** (no public port needed) — or **Web Service** if you want the `/health` endpoint reachable, exposing port `8080`.
5. Add every variable from `.env.example` under **Environment Variables** (do NOT commit your real `.env`).
6. Deploy. Check the build logs — the bot logs "AI Resume Tailor Bot is now running." once healthy.

---

## ☁️ Option D — Deploy to Render

1. Push this repo to GitHub.
2. On Render → **New → Blueprint**, point it at your repo (it will pick up `render.yaml` automatically), **or** manually create a **Background Worker** service:
   - Environment: **Docker**
   - Dockerfile path: `./Dockerfile`
3. Fill in the environment variables listed in `render.yaml` / `.env.example` in the Render dashboard.
4. Deploy — Render will build the Docker image and start the worker.

> Render's free background workers can spin down on inactivity on some plans; if you need 24/7 uptime, use a paid worker plan or an always-on VPS instead.

---

## 🎮 Using the Bot

Once running, open your bot in Telegram and send:

```
/start
/setresume        → upload your PDF/DOCX resume
/setjd             → paste the job description
/tailor            → get your AI-tailored resume
/ats               → get a full ATS compatibility report
/coverletter       → generate a matching cover letter
/improve           → improve one section at a time
/history           → view/download past tailored versions
/settings          → change tone & output format
/help              → full command list
```

---

## 🔐 Security Notes

- The dump channel is **private** — the bot only forwards/copies files to the requesting user, never exposing the channel itself.
- User-supplied resume/JD text is sanitized to strip common prompt-injection patterns before being sent to the AI (`app/utils/validators.py`).
- Per-user rate limiting prevents abuse and controls free-tier API usage (`RATE_LIMIT_COUNT` / `RATE_LIMIT_WINDOW` in `.env`).
- File uploads are validated by extension and size (`MAX_FILE_SIZE_MB`).
- Admin-only commands are gated by numeric Telegram user ID (`ADMINS` in `.env`).

---

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| Bot doesn't start, "CONFIG ERROR" in logs | Check every required field in `.env` is filled — the bot validates config on startup and tells you exactly what's missing. |
| "Cannot access dump channel" | Make sure the bot account is an **Administrator** of the channel and `DUMP_CHANNEL_ID` is correct (must start with `-100...`). |
| AI calls failing / empty responses | Verify your `GEMINI_API_KEY` or `OPENROUTER_API_KEY` is valid and has remaining free-tier quota. Check `logs/` for the specific provider error. |
| MongoDB connection timeout | Confirm Network Access in Atlas allows `0.0.0.0/0`, and the password in `MONGO_URI` doesn't contain unescaped special characters. |
| PDF text extraction returns empty | The PDF is likely scanned images with no embedded text layer — OCR is not currently included; upload a text-based PDF or DOCX instead. |
| Koyeb/Render marks the service unhealthy | Ensure `ENABLE_HEALTH_SERVER=true` and the service's configured port matches `HEALTH_SERVER_PORT` (default `8080`). |

---

## 📦 Tech Stack

Python 3.12 · Pyrogram · TgCrypto · Motor (MongoDB async) · Google Generative AI SDK · httpx (OpenRouter) · pdfplumber · PyMuPDF · python-docx · docx2txt · ReportLab · aiohttp · loguru · tenacity · Docker

---

## 📄 License

MIT — see [`LICENSE`](./LICENSE).
