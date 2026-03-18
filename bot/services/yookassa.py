import logging
import uuid

import aiohttp

logger = logging.getLogger(__name__)

YOOKASSA_API_URL = "https://api.yookassa.ru/v3/payments"


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
    """Fetch payment from YooKassa API to verify status."""
    auth = aiohttp.BasicAuth(shop_id, secret_key)
    url = f"{YOOKASSA_API_URL}/{payment_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, auth=auth) as resp:
            if resp.status == 200:
                return await resp.json()
            logger.warning("YooKassa fetch failed: %s", resp.status)
            return None
