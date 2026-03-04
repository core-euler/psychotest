import hashlib
import hmac
import json
from typing import Any

from aiohttp import web
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import Settings
from bot.models import User
from bot.services.messaging import send_access_message
from bot.services.notifications import notify_admins
from bot.services.payment import upsert_payment
from bot.services.users import mark_paid


def _verify_signature(raw: bytes, secret: str, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def build_webhook_app(settings: Settings, session_maker: async_sessionmaker, bot) -> web.Application:
    app = web.Application()

    async def webhook_handler(request: web.Request) -> web.Response:
        raw = await request.read()
        signature = request.headers.get("X-Signature") or request.headers.get("X-Prodamus-Signature")

        if settings.prodamus_webhook_secret:
            if not _verify_signature(raw, settings.prodamus_webhook_secret, signature):
                return web.json_response({"ok": False, "error": "bad signature"}, status=400)
        elif not settings.payment_stub_mode:
            return web.json_response({"ok": False, "error": "missing secret"}, status=400)

        try:
            payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except Exception:
            return web.json_response({"ok": False, "error": "invalid json"}, status=400)

        status = str(payload.get("status", "")).lower()
        provider_payment_id = str(payload.get("payment_id") or payload.get("order_id") or "")
        user_id_raw = payload.get("telegram_user_id") or payload.get("user_id")
        if not user_id_raw:
            return web.json_response({"ok": False, "error": "missing user id"}, status=400)

        user_id = int(user_id_raw)
        is_success = status in {"paid", "success", "confirmed", "succeeded"}

        async with session_maker() as session:
            payment = await upsert_payment(
                session,
                user_id=user_id,
                provider_payment_id=provider_payment_id or f"stub-{user_id}",
                status="confirmed" if is_success else status or "pending",
                payload=payload,
            )

            if is_success:
                changed = await mark_paid(session, user_id, payment.provider_payment_id or f"id-{payment.id}")
                if changed:
                    await send_access_message(
                        bot,
                        user_id,
                        settings.masterclass_link,
                        settings.channel_invite_link,
                    )
                    user = await session.get(User, user_id)
                    await notify_admins(
                        bot,
                        settings.admin_ids,
                        (
                            "Оплата подтверждена webhook\n"
                            f"user_id: {user_id}\n"
                            f"username: @{user.username if user and user.username else '-'}\n"
                            f"payment_id: {payment.provider_payment_id}"
                        ),
                    )

        return web.json_response({"ok": True})

    app.router.add_post("/prodamus/webhook", webhook_handler)
    return app
