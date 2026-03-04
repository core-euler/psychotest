# psychotest bot

Telegram bot on `aiogram 3` with inline-only flow, payment webhook + manual admin fallback.

Test logic:
- 8 questions
- each question answered 2 times
- first selected option is removed before second pick
- final result = leading + secondary type from total scores

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

Current post-test sequence in code:
1. Result image + summary.
2. Two inline buttons with Telegra.ph links (leading and secondary types).
3. Placeholder message: `ТУТ БУДЕТ ВИДЕО`.
4. Timer 2 minutes.
5. Payment offer message.
6. Reminder in 1 hour if unpaid.

## Webhook endpoint

`POST /prodamus/webhook`

Payload must include `telegram_user_id` (or `user_id`) and success status (`paid/success/confirmed/succeeded`).
