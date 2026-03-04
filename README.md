# psychotest bot

Telegram bot on `aiogram 3` with 2-round personality test, inline-only flow, payment webhook + manual admin fallback.

## Run locally

1. Create `.env` from `.env.example`.
2. Install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

3. Start Postgres and bot via Docker Compose:

```bash
docker compose up --build
```

Bot process starts polling and webhook server on `:8081`.

## Media files

Expected files in `bot/media/`:
- `start_cover.png`
- `masterclass_cover.png`
- `type_a.png ... type_f.png`
- `masterclass_promo.mp4` (optional in current implementation)

## Webhook endpoint

`POST /prodamus/webhook`

Payload must include `telegram_user_id` (or `user_id`) and success status (`paid/success/confirmed/succeeded`).
