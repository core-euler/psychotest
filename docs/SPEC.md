# SPEC: Telegram Personality Test Bot (Inline-Only)

## 1) Product Goal

Telegram bot that:
1. Runs a personality test for content creators.
2. Determines two personality types:
- Leading type (highest total score)
- Secondary type (second highest total score)
3. Delivers result as:
- PNG image for the leading type
- Link to Telegra.ph article for the leading type
4. Sends masterclass promo video and payment CTA.
5. Verifies payment automatically (webhook), with admin fallback if webhook fails.
6. After payment confirmation, sends access links in one message:
- Masterclass link
- Buyer Telegram channel invite link

Important UX constraint: bot uses inline buttons for all navigation/actions (no text commands required for user flow except `/start`; admin entry via `/admin_panel`).

---

## 2) Confirmed Business Rules (From Client)

1. Test has 8 base questions.
2. Test has 8 questions, each question requires 2 answers from user.
3. First selected option is removed from keyboard before second answer in the same question.
4. Both answers add +1 by mapped personality code `A..F`.
5. Result delivery: Telegra.ph article link + matching `.png` image.
6. Payment mode:
- Final target: automatic webhook verification.
- Current stage: payment URL may be placeholder/stub.
- If webhook did not confirm payment and user presses `Я оплатил`, create admin confirmation request.
7. Access after payment confirmation: send both links in one message (if eventually same link, still one message format remains).
8. Retake is not allowed.
9. Admin access via `/admin_panel`, allowed only for IDs in `ADMIN_IDS`.
10. Interface is inline-button-first across all user flows.

---

## 3) Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Telegram framework | aiogram 3.x |
| Update mode | Long polling |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x async |
| Migrations | Alembic |
| Config | pydantic-settings + `.env` |
| Deployment | Docker + Docker Compose |

Architecture decision for v1:
- No separate FastAPI service required.
- Bot process (aiogram) works directly with PostgreSQL.
- Lightweight webhook HTTP endpoint runs in the same process (aiohttp).

---

## 4) Project Structure

```
project/
  bot/
    handlers/
      start.py
      test.py
      payment.py
      admin.py
    keyboards/
      test.py
      payment.py
      admin.py
    services/
      test_data.py
      scoring.py
      messaging.py
      payment.py
      admin_stats.py
      notifications.py
      users.py
    models/
      user.py
      payment.py
      manual_review.py
    data/
      test.json
    media/
      start_cover.png
      masterclass_cover.png
      type_a.png
      type_b.png
      type_c.png
      type_d.png
      type_e.png
      type_f.png
      masterclass_promo.mp4
    webhooks/
      prodamus.py
    config.py
    main.py
  migrations/
  docker-compose.yml
  Dockerfile
  .env.example
  docs/
    SPEC.md
```

Note:
- `test.json` = canonical mapping/options/question texts and score mapping.
- Media mapping:
  - `start_cover.png` <- `source/ChatGPT Image 18 февр. 2026 г., 00_13_38.png`
  - `masterclass_cover.png` <- `source/ChatGPT Image 17 февр. 2026 г., 11_53_24.png`

---

## 5) Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | Yes | Telegram bot token |
| `POSTGRES_DSN` | Yes | Async PostgreSQL DSN |
| `ADMIN_IDS` | Yes | Comma-separated Telegram IDs for admin access |
| `MASTERCLASS_LINK` | Yes | URL to masterclass (post-payment) |
| `CHANNEL_INVITE_LINK` | Yes | Buyer-only Telegram channel invite |
| `PRODAMUS_PAYMENT_URL` | Yes (can be stub placeholder) | Payment page URL |
| `PRODAMUS_WEBHOOK_SECRET` | Optional in stub, required for prod | HMAC secret for webhook verification |
| `PRODAMUS_KEY` | Optional in stub, required for prod | Prodamus API key if needed |
| `LOG_LEVEL` | No | Default `INFO` |
| `PAYMENT_STUB_MODE` | No | `true/false`, default `true` in v1 setup |

Startup policy:
- Bot must fail fast if required variables are missing.

---

## 6) Database Schema

### Table: `users`

| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT PK | Telegram user ID |
| `username` | TEXT NULL | Telegram username |
| `first_name` | TEXT | Telegram first name |
| `registered_at` | TIMESTAMPTZ | default now() |
| `test_completed` | BOOLEAN | default false |
| `leading_type` | TEXT NULL | `A..F`, highest total score |
| `secondary_type` | TEXT NULL | `A..F`, second highest total score |
| `completed_at` | TIMESTAMPTZ NULL | when all 8 questions completed |
| `paid` | BOOLEAN | default false |
| `paid_at` | TIMESTAMPTZ NULL | payment confirmation timestamp |
| `payment_id` | TEXT NULL | provider transaction ID |
| `payment_status` | TEXT NULL | `pending/confirmed/failed/manual_review` |
| `last_result_sent_at` | TIMESTAMPTZ NULL | last result resend time |

### Table: `payments`

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | internal payment row |
| `user_id` | BIGINT FK -> users.id | payer |
| `provider` | TEXT | `prodamus` |
| `provider_payment_id` | TEXT NULL | provider transaction ID |
| `status` | TEXT | `created/pending/confirmed/failed/manual_review` |
| `amount` | NUMERIC NULL | optional |
| `currency` | TEXT NULL | optional |
| `payload` | JSONB NULL | raw provider payload |
| `created_at` | TIMESTAMPTZ | default now() |
| `updated_at` | TIMESTAMPTZ | default now() |

### Table: `payment_manual_reviews`

Created when user presses `Я оплатил`, but webhook confirmation not found.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `user_id` | BIGINT FK -> users.id | requester |
| `payment_id` | INT FK -> payments.id NULL | optional linkage |
| `status` | TEXT | `open/approved/rejected` |
| `created_at` | TIMESTAMPTZ | default now() |
| `resolved_at` | TIMESTAMPTZ NULL | |
| `resolved_by` | BIGINT NULL | admin telegram ID |
| `admin_comment` | TEXT NULL | optional note |

---

## 7) Test Data Model

### 7.1 Canonical type mapping

- `A` -> Педант
- `B` -> Эстет
- `C` -> Креативщик
- `D` -> Приятель
- `E` -> Артист
- `F` -> Невидимка

### 7.2 Files

- `bot/data/test.json` (prepared):
- type metadata
- 8 questions
- option-to-type score mapping

### 7.3 Scoring rules

Per question:
- User gives first answer from 6 options.
- Selected option is removed from the keyboard.
- User gives second answer from remaining 5 options.
- Both answers increment corresponding type by +1.

Totals:
- 16 answers in total (2 per question x 8 questions).
- Leading type = max total score.
- Secondary type = max score among types excluding leading type.
- Tie rule: deterministic by fixed order `A,B,C,D,E,F`.

Final result:
- Persist both fields: `leading_type`, `secondary_type`.
- Display result content by leading type.

---

## 8) User Flow

### 8.1 `/start`

1. Upsert user row (`id`, name, username).
2. If `test_completed=true`:
- resend stored result (leading type image + article link), then payment block.
3. Else:
- send `bot/media/start_cover.png` (intro image with 6 psychotypes)
- send welcome text as photo caption + inline button `Начать тест` in the same message.

### 8.2 Test Flow (2 answers per question)

- For each of 8 questions:
- message text includes progress (`Вопрос N/8`)
- first answer step: show A..F (6 inline buttons)
- second answer step: hide first selected option and show remaining 5 buttons
- on callback: validate current state + question ID + step, store score, continue
- stale callbacks: silently acknowledge and ignore

After Q8:
- calculate and store `leading_type` and `secondary_type` from total scores
- set `test_completed=true`, `completed_at=now()`
- clear FSM
- go to Result Delivery

### 8.3 Result Delivery

1. Send leading-type PNG from `bot/media/type_{code}.png`.
2. Caption includes:
- leading type name
- short text
- secondary type name in short form
3. Send message with two inline URL buttons to Telegra.ph:
- button #1: leading type name -> leading type article
- button #2: secondary type name -> secondary type article
4. Send separate message: `ТУТ БУДЕТ ВИДЕО` (video placeholder in current implementation).
5. Start timer: 2 minutes.
6. After timer: send payment offer message with `bot/media/masterclass_cover.png` and payment buttons:
- `Оплатить мастер-класс` (URL)
- `Я оплатил` (callback)
7. If still unpaid: start reminder timer 1 hour and send payment reminder message.

### 8.4 Payment

Default target behavior:
- User opens `PRODAMUS_PAYMENT_URL`.
- Provider sends webhook to `/prodamus/webhook`.
- Signature verification required.
- On valid confirmation:
- mark `users.paid=true`, store `paid_at`, `payment_id`, `payment_status=confirmed`
- update/create payment row status `confirmed`
- send access message with both links in one message
- notify admins

Stub-phase behavior:
- Payment URL can be placeholder.
- Webhook infra still implemented and active.

Manual fallback:
- If user presses `Я оплатил` and no confirmed payment exists:
- create/open `payment_manual_reviews` request
- send admin alert to check requests in `/admin_panel`
- notify user that request is sent for manual check

Admin manual decision:
- `Подтвердить` by clicking request ID in `/admin_panel`: mark paid and send access links (placeholder text for now)

### 8.6 Access message format (single message)

Contains:
- masterclass URL (`MASTERCLASS_LINK`)
- channel invite URL (`CHANNEL_INVITE_LINK`)

If business later uses one URL for both, this message still stays one block.

---

## 9) Admin Panel

Entry point:
- `/admin_panel`
- allowed only for `ADMIN_IDS`

Inline admin menu:
- `Статистика`
- `Заявки "Я оплатил"`
- `Последние оплаты`

### 9.1 Statistics block

Show:
- total users
- completed tests
- paid users
- conversion: paid/completed
- leading type distribution
- secondary type distribution

### 9.2 Manual review queue

For each open request:
- user info
- timestamps
- request id button for confirmation
- max 10 items per page + pagination

### 9.3 Security rule

Any non-admin trying `/admin_panel` receives no response.

---

## 10) Inline-Only UX Rules

1. Core flow navigation must be via inline buttons only.
2. Free text from user during flow:
- ignored or gentle reminder: `Используй кнопки ниже`.
3. Stale callbacks:
- always `answer_callback_query`
- no state mutation

---

## 11) Repeat Usage Rules

1. Retake is disabled.
2. Completed user on `/start` receives stored result + payment/access block.
3. Paid user never pays again:
- pressing payment-related actions returns access message directly.

---

## 12) Webhook Contract (Prodamus)

Endpoint:
- `POST /prodamus/webhook`

Handler requirements:
1. Validate signature (`PRODAMUS_WEBHOOK_SECRET`).
2. Parse payment status and user identity linkage metadata.
3. Idempotency: repeated webhook for same transaction must not duplicate side effects.
4. On invalid signature:
- HTTP 400
- log warning
- no DB mutation

Metadata requirement:
- payment link/webhook payload must include `telegram_user_id` or internal `user_id` to map transaction.

---

## 13) Logging

- Structured logs to stdout.
- Include `user_id`, action, handler, state where relevant.
- For payment/webhook include `payment_id`, status, verification result.
- `LOG_LEVEL=INFO` default, `DEBUG` for local troubleshooting.

---

## 14) Error Handling Matrix

| Scenario | Behavior |
|---|---|
| Free text during test | Reminder + keep current inline state |
| Stale callback | Ack silently, ignore |
| Bot restart mid-test | User restarts from `/start`, clean state |
| Webhook bad signature | 400 + warning log |
| Webhook duplicate event | Idempotent no-op after first success |
| `Я оплатил` without webhook confirmation | Create manual review + notify admins |
| Admin notification failed | Log error, continue user flow |
| DB unavailable on startup | Fail fast, container restart policy handles |

---

## 15) Source Materials Status

### Available and parsed

- Questionnaire PDF: `source/Тест на личности (1).pdf`
- Type descriptions:
- `source/A &mdash; ПЕДАНТ.pdf`
- `source/Эстет.pdf`
- `source/КРЕАТИВЩИК.pdf`
- `source/Приятель.pdf`
- `source/Невидимка.pdf`
- `source/f) АРТИСТ (АКТЁР).docx`
- Start image: `source/ChatGPT Image 18 февр. 2026 г., 00_13_38.png`
- Masterclass offer image: `source/ChatGPT Image 17 февр. 2026 г., 11_53_24.png`

### Content links

- https://telegra.ph/Pedant-03-04-3
- https://telegra.ph/EHstet-03-04
- https://telegra.ph/Priyatel-03-04
- https://telegra.ph/Nevidimka-03-04
- https://telegra.ph/Kreativshchik-03-04
- https://telegra.ph/Artist-akter-03-04

### Still needed for production launch

- Final payment URL + provider secrets
- Final masterclass link
- Final buyer channel invite link
- Final normalized PNG assets under `bot/media/`

---

## 16) Implementation Priority

1. Data layer + migrations (`users`, `payments`, `payment_manual_reviews`).
2. Inline FSM for 8 questions with 2 answers per question.
3. Result delivery (PNG + article link).
4. Payment CTA + webhook endpoint + idempotency.
5. `Я оплатил` fallback with admin actions.
6. `/admin_panel` with inline menu and stats.
7. Docker startup wiring and health checks.
