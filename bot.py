import logging
import os

from telegram import Update
from telegram.ext import Application, ChatJoinRequestHandler

import config.settings as cfg
from handlers import (
    get_start_handlers,
    handle_join_request,
    get_channel_handlers,
    get_admin_handlers,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting bot...")

    app = Application.builder().token(cfg.BOT_TOKEN).build()

    # Register all handlers
    for h in get_start_handlers():
        app.add_handler(h)
    for h in get_channel_handlers():
        app.add_handler(h)
    for h in get_admin_handlers():
        app.add_handler(h)
    app.add_handler(ChatJoinRequestHandler(handle_join_request))

    # Get bot username on startup
    async def post_init(application):
        bot = await application.bot.get_me()
        cfg.BOT_USERNAME = bot.username
        logger.info(f"✅ Bot started as @{bot.username}")
        logger.info(f"👑 Owner ID: {cfg.OWNER_ID}")

    app.post_init = post_init

    port = int(os.environ.get("PORT", 8080))
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL", "")

    if webhook_url:
        # Render pe webhook use karo
        logger.info(f"Starting webhook on port {port}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url}/webhook",
            url_path="/webhook",
        )
    else:
        # Local pe polling
        logger.info("Starting polling...")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

