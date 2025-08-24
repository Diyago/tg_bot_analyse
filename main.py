# This will be the main entry point for the bot.
import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from config import TELEGRAM_BOT_TOKEN
from ai_analyzer import get_analysis

# --- In-Memory Cache ---
MESSAGE_CACHE = defaultdict(lambda: deque(maxlen=200))

# --- Command Handlers ---

async def start_handler(message: Message):
    """Handles the /start command in private chats."""
    await message.answer(
        "Привет! Я — Коммуникационный Коуч. Моя задача — помочь вам "
        "проанализировать общение в рабочих чатах.\n\n"
        "Добавьте меня в групповой чат, и я начну собирать сообщения (я не имею доступа к старой истории!). "
        "Когда вам понадобится анализ, используйте одну из команд прямо в группе.\n\n"
        "Чтобы узнать больше о командах, отправьте /help."
    )

async def help_handler(message: Message):
    """Handles the /help command in private chats."""
    await message.answer(
        "📌 **Как использовать бота:**\n\n"
        "1. **Добавьте меня в ваш групповой чат.**\n"
        "   Я начну собирать сообщения с момента добавления.\n\n"
        "2. **Используйте команду для анализа (в группе):**\n"
        "   - `/analyze_last_100` — проанализировать последние 100 сообщений.\n"
        "   - `/analyze_last_24h` — проанализировать сообщения за последние 24 часа.\n\n"
        "3. **Получите отчет:**\n"
        "   Отчет об анализе придет вам в **личные сообщения**, чтобы обеспечить конфиденциальность.\n\n"
        "🔒 **Важно:** Только администраторы чата могут запускать анализ. "
        "Отчеты доступны только тому, кто вызвал команду."
    )

# --- Message Caching Handler ---

async def cache_group_messages(message: Message):
    """Catches all text messages in groups and saves them to the cache."""
    if message.text and message.from_user:
        chat_id = message.chat.id
        MESSAGE_CACHE[chat_id].append({
            "text": message.text,
            "user_id": message.from_user.id,
            "user_name": message.from_user.full_name,
            "timestamp": message.date,
        })
        logging.info(f"Cached message from {message.from_user.full_name} in chat {chat_id}")

# --- Analysis Handler ---

async def analyze_handler(message: Message, bot: Bot):
    """Handles the /analyze commands in group chats."""
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    command = message.text.split()[0] if message.text else ""

    # 1. Check if the user is an admin
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            await message.reply("Эту команду могут использовать только администраторы чата.")
            return
    except TelegramBadRequest:
        await message.reply("Не удалось проверить права доступа. Убедитесь, что я имею права администратора в этом чате.")
        return

    # 2. Get messages from cache
    chat_messages = list(MESSAGE_CACHE[chat_id])
    if not chat_messages:
        await message.reply("Нет сообщений для анализа. Я собираю сообщения с момента моего добавления в чат.")
        return

    messages_to_analyze = []
    if command == "/analyze_last_100":
        messages_to_analyze = chat_messages[-100:]
    elif command == "/analyze_last_24h":
        one_day_ago = datetime.now().astimezone() - timedelta(hours=24)
        messages_to_analyze = [msg for msg in chat_messages if msg["timestamp"] > one_day_ago]

    if not messages_to_analyze:
        await message.reply("Не найдено сообщений за указанный период.")
        return

    # 3. Notify user and run analysis
    try:
        await bot.send_message(user_id, "Начинаю анализ... Это может занять несколько минут.")
    except TelegramBadRequest:
        bot_info = await bot.get_me()
        await message.reply(
            "Не могу отправить вам отчет в личные сообщения. "
            f"Пожалуйста, начните диалог со мной (@{bot_info.username}) и попробуйте снова."
        )
        return

    report = await get_analysis(messages_to_analyze)
    await bot.send_message(user_id, report, parse_mode="Markdown")


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Pass the bot instance to the dispatcher to make it available in handlers
    dp["bot"] = bot

    # Register handlers for private chats only
    dp.message.register(start_handler, CommandStart(), F.chat.type == "private")
    dp.message.register(help_handler, Command("help"), F.chat.type == "private")

    # Register handler for analysis commands in groups
    dp.message.register(
        analyze_handler,
        Command("analyze_last_100", "analyze_last_24h"),
        F.chat.type.in_({"group", "supergroup"})
    )

    # Register handler for caching group messages
    dp.message.register(cache_group_messages, F.text, F.chat.type.in_({"group", "supergroup"}))


    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
