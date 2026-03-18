import json
import logging

from aiohttp import web
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import Settings
from bot.models import User
from bot.services.messaging import send_access_message
from bot.services.notifications import notify_admins
from bot.services.payment import upsert_payment
from bot.services.users import mark_paid
from bot.services.yookassa import fetch_payment

logger = logging.getLogger(__name__)


def build_webhook_app(settings: Settings, session_maker: async_sessionmaker, bot) -> web.Application:
    app = web.Application()

    async def webhook_handler(request: web.Request) -> web.Response:
        raw = await request.read()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)

        event = payload.get("event")
        if event != "payment.succeeded":
            return web.json_response({"ok": True})

        payment_obj = payload.get("object", {})
        payment_id = payment_obj.get("id")
        metadata = payment_obj.get("metadata", {})
        user_id_raw = metadata.get("telegram_user_id")

        if not payment_id or not user_id_raw:
            logger.warning("YooKassa webhook missing payment_id or user_id")
            return web.json_response({"error": "missing data"}, status=400)

        # Verify payment status via API (don't trust webhook blindly).
        verified = await fetch_payment(settings.yookassa_shop_id, settings.yookassa_secret_key, payment_id)
        if not verified or verified.get("status") != "succeeded":
            logger.warning("YooKassa payment %s not verified", payment_id)
            return web.json_response({"error": "payment not confirmed"}, status=400)

        user_id = int(user_id_raw)

        async with session_maker() as session:
            payment = await upsert_payment(
                session,
                user_id=user_id,
                provider_payment_id=payment_id,
                status="confirmed",
                payload=payload,
                provider="yookassa",
            )

            changed = await mark_paid(session, user_id, payment.provider_payment_id or payment_id)
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
                        "Оплата подтверждена (YooKassa)\n"
                        f"user_id: {user_id}\n"
                        f"username: @{user.username if user and user.username else '-'}\n"
                        f"payment_id: {payment_id}"
                    ),
                )

        return web.json_response({"ok": True})

    app.router.add_post("/yookassa/webhook", webhook_handler)
    return app
