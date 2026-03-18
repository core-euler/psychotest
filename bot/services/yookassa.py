import logging
import uuid

import aiohttp

logger = logging.getLogger(__name__)

YOOKASSA_API_URL = "https://api.yookassa.ru/v3/payments"

# Polling: check every 15 seconds for 30 minutes.
POLL_INTERVAL = 15
POLL_TIMEOUT = 1800


async def create_payment_link(
    shop_id: str,
    secret_key: str,
    amount: str,
    user_id: int,
    return_url: str,
    description: str = "Мастер-класс",
) -> tuple[str, str]:
    """Create a YooKassa payment. Returns (payment_id, confirmation_url)."""
    payload = {
        "amount": {"value": amount, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": description,
        "metadata": {"telegram_user_id": str(user_id)},
    }

    auth = aiohttp.BasicAuth(shop_id, secret_key)
    headers = {
        "Idempotence-Key": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(YOOKASSA_API_URL, json=payload, auth=auth, headers=headers) as resp:
            data = await resp.json()
            if resp.status != 200:
                logger.error("YooKassa payment creation failed: %s %s", resp.status, data)
                raise RuntimeError(f"YooKassa error {resp.status}: {data}")
            payment_id = data["id"]
            confirmation_url = data["confirmation"]["confirmation_url"]
            logger.info("YooKassa payment created: %s for user %s", payment_id, user_id)
            return payment_id, confirmation_url


async def fetch_payment(shop_id: str, secret_key: str, payment_id: str) -> dict | None:
    """Fetch payment from YooKassa API to check status."""
    auth = aiohttp.BasicAuth(shop_id, secret_key)
    url = f"{YOOKASSA_API_URL}/{payment_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, auth=auth) as resp:
            if resp.status == 200:
                return await resp.json()
            logger.warning("YooKassa fetch payment %s failed: %s", payment_id, resp.status)
            return None


async def poll_payment_status(
    shop_id: str,
    secret_key: str,
    payment_id: str,
    interval: int = POLL_INTERVAL,
    timeout: int = POLL_TIMEOUT,
) -> str | None:
    """Poll YooKassa until payment succeeds, is canceled, or timeout.

    Returns final status: 'succeeded', 'canceled', or None on timeout.
    """
    import asyncio

    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval

        data = await fetch_payment(shop_id, secret_key, payment_id)
        if not data:
            continue

        status = data.get("status")
        logger.debug("YooKassa poll payment %s: status=%s (elapsed %ds)", payment_id, status, elapsed)

        if status in ("succeeded", "canceled"):
            return status

    logger.info("YooKassa poll timeout for payment %s after %ds", payment_id, timeout)
    return None
