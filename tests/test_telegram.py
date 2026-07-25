import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.config.config import settings
from telegram.client import send_telegram_message


@pytest.mark.asyncio
async def test_send_telegram_message_success() -> None:
    """
    Verifies that send_telegram_message calls the Telegram API with the correct payload and returns True on success.
    """
    # Force mock settings variables
    settings.TELEGRAM_BOT_TOKEN = "mock_bot_token"
    settings.TELEGRAM_CHAT_ID = "mock_chat_id"

    mock_response = MagicMock(status_code=200)

    # Patch the HTTP client post request
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as patch_post:
        patch_post.return_value = mock_response

        status = await send_telegram_message("Test message alert")
        assert status is True

        # Verify arguments passed to POST call
        called_args, called_kwargs = patch_post.call_args
        assert called_args[0] == "https://api.telegram.org/botmock_bot_token/sendMessage"
        assert called_kwargs["json"]["chat_id"] == "mock_chat_id"
        assert called_kwargs["json"]["text"] == "Test message alert"
        assert called_kwargs["json"]["parse_mode"] == "Markdown"


@pytest.mark.asyncio
async def test_send_telegram_message_missing_config() -> None:
    """
    Verifies that send_telegram_message fails safe and returns False when configurations are missing.
    """
    settings.TELEGRAM_BOT_TOKEN = None
    settings.TELEGRAM_CHAT_ID = None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as patch_post:
        status = await send_telegram_message("Test message alert")
        assert status is False
        assert patch_post.call_count == 0


@pytest.mark.asyncio
async def test_send_telegram_message_api_failure() -> None:
    """
    Verifies that send_telegram_message returns False when the Telegram API returns a non-200 response.
    """
    settings.TELEGRAM_BOT_TOKEN = "mock_bot_token"
    settings.TELEGRAM_CHAT_ID = "mock_chat_id"

    mock_response = MagicMock(status_code=400, text="Bad Request")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as patch_post:
        patch_post.return_value = mock_response

        status = await send_telegram_message("Test message alert")
        assert status is False
        assert patch_post.call_count == 1
