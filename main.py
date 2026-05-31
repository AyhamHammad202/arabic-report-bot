"""
main.py
-------
Entry point for the Arabic Language Report Telegram Bot.

Startup sequence:
  1. Configure logging
  2. Initialise the SQLite database
  3. Register bot commands (visible in Telegram's / menu)
  4. Register routers
  5. Start polling
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat

from config import ADMIN_ID, BOT_TOKEN, SUPER_ADMIN_ID
from database import init_db
from handlers import admin_router, student_router, superadmin_router

# ──────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Bot command menus
# ──────────────────────────────────────────────

# Commands shown to every regular student
STUDENT_COMMANDS = [
    BotCommand(command="start",  description="بدء تسليم التقرير"),
    BotCommand(command="help",   description="التواصل مع الدعم"),
]

# Commands shown only to the admin (doctor)
ADMIN_COMMANDS = [
    BotCommand(command="start",       description="لوحة التحكم الرئيسية"),
    BotCommand(command="admin",       description="فتح لوحة التحكم"),
    BotCommand(command="help",        description="التواصل مع الدعم"),
    BotCommand(command="whoami",      description="عرض معرّفك على تيليغرام"),
]

# Commands shown only to the superadmin
SUPERADMIN_COMMANDS = [
    BotCommand(command="start",       description="لوحة التحكم الرئيسية"),
    BotCommand(command="admin",       description="فتح لوحة التحكم"),
    BotCommand(command="superadmin",  description="لوحة تحكم المشرف العام"),
    BotCommand(command="help",        description="التواصل مع الدعم"),
    BotCommand(command="whoami",      description="عرض معرّفك على تيليغرام"),
]


async def set_bot_commands(bot: Bot) -> None:
    """Register command menus scoped per user type."""
    # Default for all users (students)
    await bot.set_my_commands(STUDENT_COMMANDS, scope=BotCommandScopeAllPrivateChats())

    # Override for admin
    try:
        await bot.set_my_commands(
            ADMIN_COMMANDS,
            scope=BotCommandScopeChat(chat_id=ADMIN_ID),
        )
        logger.info("Admin command menu registered for ADMIN_ID=%s", ADMIN_ID)
    except Exception as exc:
        logger.warning("Could not set admin command scope: %s", exc)

    # Override for superadmin (may be same as admin)
    try:
        await bot.set_my_commands(
            SUPERADMIN_COMMANDS,
            scope=BotCommandScopeChat(chat_id=SUPER_ADMIN_ID),
        )
        logger.info("Superadmin command menu registered for SUPER_ADMIN_ID=%s", SUPER_ADMIN_ID)
    except Exception as exc:
        logger.warning("Could not set superadmin command scope: %s", exc)


# ──────────────────────────────────────────────
# Main coroutine
# ──────────────────────────────────────────────

async def main() -> None:
    # Initialise database tables
    await init_db()

    # Create bot instance with Markdown as default parse mode
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # Dispatcher with in-memory FSM storage
    # (swap MemoryStorage for RedisStorage in production for persistence across restarts)
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers — order matters:
    # 1. superadmin (most privileged, catches /superadmin first)
    # 2. student (handles /start, but redirects admin/superadmin appropriately)
    # 3. admin
    dp.include_router(superadmin_router)
    dp.include_router(student_router)
    dp.include_router(admin_router)

    logger.info("Bot is starting up…")

    try:
        # Drop pending updates accumulated while the bot was offline
        await bot.delete_webhook(drop_pending_updates=True)

        # Register command menus visible in Telegram UI
        await set_bot_commands(bot)

        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot shut down gracefully.")


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(main())
