# Math Helper

A small FastAPI math-helper website with a safe arithmetic calculator and optional AI math tutor powered by Groq. Guest requests to each API endpoint are limited to **20 per hour per IP**.

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `GROQ_API_KEY` to a valid Groq API key. The key is only read by the server; do not put it in frontend code or commit `.env`.

```bash
set -a && source .env && set +a  # Windows PowerShell: use $env:GROQ_API_KEY = "..."
uvicorn main:app --reload
```

Open http://127.0.0.1:8000. Without an API key the calculator still works; AI help returns a configuration message.

## Deploy on Render

1. Push this repository to GitHub and create a **Web Service** on Render connected to it. The included `render.yaml` supplies the build/start commands and asks for `GROQ_API_KEY` when you create the service, or use the manual setup below.
2. In Render, open your service → **Environment** → **Add Environment Variable**. Add `GROQ_API_KEY` as the key and your newly generated Groq API key as the value. Optionally add `GROQ_MODEL` (defaults to `llama-3.3-70b-versatile`). Save; Render will redeploy.
3. Do not upload `.env` or paste a key into source code. Render injects environment variables at runtime; there is no need to create or upload a `.env` file on Render.

Manual Render settings if needed:
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`

## Guest rate limits

The calculator and AI tutor each allow 20 requests per hour per visitor IP. The current SlowAPI limiter uses in-process memory, which is suitable for a simple single-instance deployment, but counters reset on restart and do not synchronize across multiple Render instances. For a scaled or higher-assurance deployment, configure a shared Redis-backed rate-limit store and review trusted proxy/IP settings.

## API

- `GET /health` — health check.
- `POST /api/calculate` with `{"expression":"(18 + 6) / 3"}` — safe basic arithmetic only.
- `POST /api/ask` with `{"question":"How do I solve 2x + 5 = 17?"}` — AI tutor.
