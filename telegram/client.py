import logging
import httpx
from app.config.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(message: str) -> bool:
    """
    Sends a formatted Markdown alert message to the configured Telegram chat/channel.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning(
            "Telegram credentials (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID) are not configured. "
            "Skipping Telegram notification dispatch."
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully.")
                return True
            else:
                logger.warning(
                    f"Failed to send Telegram notification. Status Code: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return False
    except Exception as e:
        logger.error(f"Error executing Telegram API call: {e}", exc_info=True)
        return False
