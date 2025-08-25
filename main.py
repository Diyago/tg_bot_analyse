import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ChatMemberOwner, ChatMemberAdministrator
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv
import re

from ai_analyzer import CommunicationAnalyzer
from message_cache import MessageCache
from config import Config

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Initialize services
message_cache = MessageCache(max_size=Config.CACHE_SIZE)
ai_analyzer = CommunicationAnalyzer()

# Track command usage for rate limiting
user_last_command = {}


def is_user_authorized(user_id: int) -> bool:
    """Check if user is in the authorized users list"""
    return user_id in Config.AUTHORIZED_USERS


def is_main_admin(user_id: int) -> bool:
    """Check if user is the main admin (first in the list)"""
    return len(Config.AUTHORIZED_USERS) > 0 and user_id == Config.AUTHORIZED_USERS[0]


def add_authorized_user(user_id: int) -> bool:
    """Add user to authorized list"""
    if user_id not in Config.AUTHORIZED_USERS:
        Config.AUTHORIZED_USERS.append(user_id)
        return True
    return False


def remove_authorized_user(user_id: int) -> bool:
    """Remove user from authorized list"""
    if user_id in Config.AUTHORIZED_USERS and not is_main_admin(user_id):
        Config.AUTHORIZED_USERS.remove(user_id)
        return True
    return False


def check_rate_limit(user_id: int) -> bool:
    """Check if user can execute command (rate limiting)"""
    now = datetime.now()
    if user_id in user_last_command:
        time_diff = now - user_last_command[user_id]
        if time_diff < timedelta(seconds=Config.RATE_LIMIT_SECONDS):
            return False
    user_last_command[user_id] = now
    return True


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2"""
    # Characters that need to be escaped in MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


async def safe_send_message(bot_or_message, chat_id: int = None, text: str = "", **kwargs):
    """Safely send a message, falling back to plain text if markdown fails"""
    try:
        if hasattr(bot_or_message, 'send_message'):  # It's a bot instance
            return await bot_or_message.send_message(chat_id=chat_id, text=text, **kwargs)
        else:  # It's a message instance
            return await bot_or_message.answer(text=text, **kwargs)
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            # Remove parse_mode and try again with plain text
            kwargs.pop('parse_mode', None)
            if hasattr(bot_or_message, 'send_message'):
                return await bot_or_message.send_message(chat_id=chat_id, text=text, **kwargs)
            else:
                return await bot_or_message.answer(text=text, **kwargs)
        else:
            raise


async def safe_edit_message(message, text: str, **kwargs):
    """Safely edit a message, handling cases where message might not exist"""
    try:
        return await message.edit_text(text=text, **kwargs)
    except TelegramBadRequest as e:
        if "message to edit not found" in str(e).lower():
            # Message was already deleted, do nothing
            return None
        elif "can't parse entities" in str(e).lower():
            # Remove parse_mode and try again with plain text
            kwargs.pop('parse_mode', None)
            return await message.edit_text(text=text, **kwargs)
        else:
            raise


@dp.message(CommandStart())
async def start_command(message: Message):
    """Handle /start command in private messages"""
    if message.chat.type != ChatType.PRIVATE:
        return
    
    welcome_text = """
🤖 **Коммуникационный Коуч**

Я анализирую рабочие коммуникации в групповых чатах и предоставляю конфиденциальные отчеты.

**Как использовать:**
1. Добавьте меня в групповой чат
2. Используйте команды анализа (только для администраторов)
3. Получите приватный отчет в личных сообщениях

Используйте /help для получения списка команд.
"""
    await safe_send_message(message, text=welcome_text, parse_mode='Markdown')


@dp.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command in private messages"""
    if message.chat.type != ChatType.PRIVATE:
        return
    
    help_text = """
📖 **Доступные команды:**

**В групповых чатах (только для авторизованных пользователей):**
• `/analyze_last_100` — анализ последних 100 сообщений
• `/analyze_last_24h` — анализ сообщений за последние 24 часа
• `/my_communication` — персональный анализ вашего стиля общения
• `/analyze_user @username` — анализ стиля общения указанного пользователя (ответьте на сообщение пользователя)
• `/chat_stats` — показать статистику сообщений в чате

**В групповых чатах и личных сообщениях:**
• `/analyze_user_all @username` — анализ стиля общения пользователя из всех чатов с ботом
• `/analyze_user_all <user_id>` — анализ по числовому ID пользователя

**Управление доступом (только для главного администратора):**
• `/add_user @username` — добавить пользователя по имени
• `/add_user <user_id>` — добавить пользователя по ID
• Ответить на сообщение командой `/add_user` — добавить автора сообщения
• `/remove_user @username` или `/remove_user <user_id>` — удалить пользователя
• Ответить на сообщение командой `/remove_user` — удалить автора сообщения
• `/list_users` — показать список авторизованных пользователей

**Важно:**
• Анализ доступен только для сообщений, отправленных после добавления бота
• Отчеты приходят только в личные сообщения
• Команды доступны только авторизованным пользователям
• Ограничение: одна команда в {0} секунд

**Что анализируется:**
• Тон общения в команде
• Эффективность коммуникации
• Рекомендации по улучшению
• Общая атмосфера в команде

Все данные обрабатываются конфиденциально.
""".format(Config.RATE_LIMIT_SECONDS)
    
    await safe_send_message(message, text=help_text, parse_mode='Markdown')


@dp.message(Command("analyze_last_100"))
async def analyze_last_100(message: Message):
    """Analyze last 100 messages"""
    await handle_analysis_command(message, "last_100")


@dp.message(Command("analyze_last_24h"))
async def analyze_last_24h(message: Message):
    """Analyze messages from last 24 hours"""
    await handle_analysis_command(message, "last_24h")


@dp.message(Command("add_user"))
async def add_user_command(message: Message):
    """Add user to authorized list (main admin only)"""
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("Эта команда работает только в групповых чатах.")
        return
    
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    # Check if user is main admin
    if not is_main_admin(user_id):
        await message.answer("❌ Только главный администратор может добавлять пользователей.")
        return
    
    # Check if this is a reply to someone's message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        new_user_id = target_user.id
        username = target_user.username or target_user.first_name or "Пользователь"
        
        if add_authorized_user(new_user_id):
            await message.answer(f"✅ Пользователь @{username} (ID: {new_user_id}) добавлен в список авторизованных.")
            logger.info(f"User {new_user_id} (@{username}) added to authorized list by {user_id}")
        else:
            await message.answer(f"ℹ️ Пользователь @{username} (ID: {new_user_id}) уже в списке авторизованных.")
        return
    
    # Parse user ID or username from command
    try:
        command_parts = (message.text or "").split()
        if len(command_parts) != 2:
            await message.answer(
                "❌ Использование:\n"
                "• /add_user <user_id> - добавить по ID\n"
                "• /add_user @username - добавить по username\n"
                "• Ответьте на сообщение пользователя командой /add_user"
            )
            return
        
        user_input = command_parts[1]
        
        # If it starts with @, it's a username
        if user_input.startswith('@'):
            username = user_input[1:]  # Remove @
            try:
                # Try to get user info by username
                chat_member = await bot.get_chat_member(message.chat.id, username)
                new_user_id = chat_member.user.id
                
                if add_authorized_user(new_user_id):
                    await message.answer(f"✅ Пользователь @{username} (ID: {new_user_id}) добавлен в список авторизованных.")
                    logger.info(f"User {new_user_id} (@{username}) added to authorized list by {user_id}")
                else:
                    await message.answer(f"ℹ️ Пользователь @{username} (ID: {new_user_id}) уже в списке авторизованных.")
                    
            except Exception as e:
                await message.answer(
                    f"❌ Не удалось найти пользователя @{username} в этом чате.\n"
                    "Убедитесь, что пользователь есть в чате или используйте числовой ID."
                )
                logger.error(f"Error finding user @{username}: {e}")
        else:
            # Try to parse as numeric ID
            new_user_id = int(user_input)
            
            if add_authorized_user(new_user_id):
                await message.answer(f"✅ Пользователь с ID {new_user_id} добавлен в список авторизованных.")
                logger.info(f"User {new_user_id} added to authorized list by {user_id}")
            else:
                await message.answer(f"ℹ️ Пользователь с ID {new_user_id} уже в списке авторизованных.")
            
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте числовой ID или @username.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении пользователя: {str(e)}")
        logger.error(f"Error adding user: {e}")


@dp.message(Command("remove_user"))
async def remove_user_command(message: Message):
    """Remove user from authorized list (main admin only)"""
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("Эта команда работает только в групповых чатах.")
        return
    
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    # Check if user is main admin
    if not is_main_admin(user_id):
        await message.answer("❌ Только главный администратор может удалять пользователей.")
        return
    
    # Check if this is a reply to someone's message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id
        username = target_user.username or target_user.first_name or "Пользователь"
        
        if remove_authorized_user(target_user_id):
            await message.answer(f"✅ Пользователь @{username} (ID: {target_user_id}) удален из списка авторизованных.")
            logger.info(f"User {target_user_id} (@{username}) removed from authorized list by {user_id}")
        else:
            await message.answer(f"❌ Невозможно удалить пользователя @{username}. Возможно, это главный администратор.")
        return
    
    # Parse user ID or username from command
    try:
        command_parts = (message.text or "").split()
        if len(command_parts) != 2:
            await message.answer(
                "❌ Использование:\n"
                "• /remove_user <user_id> - удалить по ID\n"
                "• /remove_user @username - удалить по username\n"
                "• Ответьте на сообщение пользователя командой /remove_user"
            )
            return
        
        user_input = command_parts[1]
        
        # If it starts with @, it's a username
        if user_input.startswith('@'):
            username = user_input[1:]  # Remove @
            try:
                # Try to get user info by username
                chat_member = await bot.get_chat_member(message.chat.id, username)
                target_user_id = chat_member.user.id
                
                if remove_authorized_user(target_user_id):
                    await message.answer(f"✅ Пользователь @{username} (ID: {target_user_id}) удален из списка авторизованных.")
                    logger.info(f"User {target_user_id} (@{username}) removed from authorized list by {user_id}")
                else:
                    await message.answer(f"❌ Невозможно удалить пользователя @{username}. Возможно, это главный администратор или пользователь не найден.")
                    
            except Exception as e:
                await message.answer(
                    f"❌ Не удалось найти пользователя @{username} в этом чате.\n"
                    "Убедитесь, что пользователь есть в чате или используйте числовой ID."
                )
                logger.error(f"Error finding user @{username}: {e}")
        else:
            # Try to parse as numeric ID
            target_user_id = int(user_input)
            
            if remove_authorized_user(target_user_id):
                await message.answer(f"✅ Пользователь с ID {target_user_id} удален из списка авторизованных.")
                logger.info(f"User {target_user_id} removed from authorized list by {user_id}")
            else:
                await message.answer(f"❌ Невозможно удалить пользователя с ID {target_user_id}. Возможно, это главный администратор или пользователь не найден.")
            
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте числовой ID или @username.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении пользователя: {str(e)}")
        logger.error(f"Error removing user: {e}")


@dp.message(Command("list_users"))
async def list_users_command(message: Message):
    """Show list of authorized users (main admin only)"""
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("Эта команда работает только в групповых чатах.")
        return
    
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    # Check if user is main admin
    if not is_main_admin(user_id):
        await message.answer("❌ Только главный администратор может просматривать список пользователей.")
        return
    
    if not Config.AUTHORIZED_USERS:
        await message.answer("📝 Список авторизованных пользователей пуст.")
        return
    
    user_list = "📝 **Авторизованные пользователи:**\n\n"
    for i, uid in enumerate(Config.AUTHORIZED_USERS):
        role = " (Главный админ)" if i == 0 else ""
        user_list += f"• `{uid}`{role}\n"
    
    await safe_send_message(message, text=user_list, parse_mode='Markdown')


@dp.message(Command("chat_stats"))
async def chat_stats_command(message: Message):
    """Show chat cache statistics (authorized users only)"""
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("Эта команда работает только в групповых чатах.")
        return
    
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check if user is authorized
    if not is_user_authorized(user_id):
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return
    
    # Get cache statistics
    cache_stats = message_cache.get_chat_stats(chat_id)
    
    stats_text = f"📊 **Статистика чата '{message.chat.title}'**\n\n"
    stats_text += f"💬 **Сообщения в кеше:** {cache_stats['total_messages']}\n"
    stats_text += f"👥 **Активных пользователей:** {cache_stats['unique_users']}\n"
    
    if cache_stats['oldest_message']:
        stats_text += f"📅 **Первое сообщение в кеше:** {cache_stats['oldest_message'].strftime('%Y-%m-%d %H:%M')}\n"
    else:
        stats_text += f"📅 **Первое сообщение в кеше:** Нет сообщений\n"
        
    if cache_stats['newest_message']:
        stats_text += f"🕐 **Последнее сообщение в кеше:** {cache_stats['newest_message'].strftime('%Y-%m-%d %H:%M')}\n"
    else:
        stats_text += f"🕐 **Последнее сообщение в кеше:** Нет сообщений\n"
    
    stats_text += f"\n🔧 **Максимальный размер кеша:** {Config.CACHE_SIZE} сообщений\n"
    
    if cache_stats['total_messages'] == 0:
        stats_text += "\n❗ **Внимание:** Кеш пуст. Бот начнет сохранять сообщения только после отправки этой команды."
    elif cache_stats['total_messages'] < 10:
        stats_text += "\n💡 **Совет:** Для качественного анализа рекомендуется минимум 20-50 сообщений."
    
    await safe_send_message(message, text=stats_text, parse_mode='Markdown')


@dp.message(Command("my_communication"))
async def my_communication_command(message: Message):
    """Analyze personal communication style (authorized users only)"""
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("Эта команда работает только в групповых чатах.")
        return
    
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name or "Пользователь"
    
    # Check if user is authorized
    if not is_user_authorized(user_id):
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return
    
    # Check rate limiting
    if not check_rate_limit(user_id):
        await message.answer(
            f"⏱️ Подождите {Config.RATE_LIMIT_SECONDS} секунд между командами анализа."
        )
        return
    
    # Show thinking message
    thinking_msg = await message.answer("🤔 Анализирую ваш стиль коммуникации...")
    
    try:
        # Get user's messages
        user_messages = message_cache.get_user_messages(chat_id, user_id)
        
        # Get user's interactions with others
        interactions = message_cache.get_user_interactions(chat_id, user_id)
        
        if not user_messages:
            await safe_edit_message(
                thinking_msg,
                "❌ Нет доступных сообщений от вас для анализа. "
                "Напишите несколько сообщений в чате и попробуйте снова."
            )
            return
        
        # Perform personal analysis
        analysis_result = await ai_analyzer.analyze_user_communication(
            user_messages, interactions, username
        )
        
        # Delete thinking message and send private analysis
        await thinking_msg.delete()
        
        # Send analysis privately to user
        await safe_send_message(
            bot,
            chat_id=user_id,
            text=analysis_result,
            parse_mode='Markdown'
        )
        
        # Confirm in group chat
        await message.answer(
            f"✅ Персональный анализ отправлен @{username} в личные сообщения."
        )
        
        logger.info(f"Personal analysis completed for user {user_id} in chat {chat_id}")
        
    except Exception as e:
        await safe_edit_message(thinking_msg, f"❌ Ошибка при анализе: {str(e)}")
        logger.error(f"Personal analysis error: {e}")


@dp.message(Command("analyze_user"))
async def analyze_user_command(message: Message):
    """Analyze specific user's communication style (authorized users only)"""
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("Эта команда работает только в групповых чатах.")
        return
    
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check if user is authorized
    if not is_user_authorized(user_id):
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return
    
    # Check rate limiting
    if not check_rate_limit(user_id):
        await message.answer(
            f"⏱️ Подождите {Config.RATE_LIMIT_SECONDS} секунд между командами анализа."
        )
        return
    
    target_user_id = None
    target_username = None
    
    # Check if replying to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        target_username = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name or "Пользователь"
    else:
        # Parse username from command
        command_parts = (message.text or "").split()
        if len(command_parts) < 2:
            await message.answer(
                "❌ Использование:\n"
                "• `/analyze_user @username` - анализ по имени\n"
                "• Ответьте на сообщение пользователя командой `/analyze_user`"
            )
            return
        
        user_input = command_parts[1]
        if user_input.startswith('@'):
            username = user_input[1:]
            try:
                # Try to find user by username in cached messages
                all_messages = message_cache.get_last_n_messages(chat_id, 1000)
                for msg in all_messages:
                    if msg.get('username', '').lower() == username.lower():
                        target_user_id = msg['user_id']
                        target_username = msg['username']
                        break
                
                if not target_user_id:
                    await message.answer(
                        f"❌ Пользователь @{username} не найден в кеше сообщений этого чата. "
                        "Ответьте на сообщение пользователя командой /analyze_user."
                    )
                    return
            except Exception as e:
                await message.answer(f"❌ Ошибка поиска пользователя: {str(e)}")
                return
        else:
            await message.answer("❌ Неверный формат. Используйте @username.")
            return
    
    if not target_user_id:
        await message.answer("❌ Не удалось определить пользователя для анализа.")
        return
    
    # Show thinking message
    thinking_msg = await message.answer(f"🤔 Анализирую стиль коммуникации {target_username}...")
    
    try:
        # Get target user's messages
        user_messages = message_cache.get_user_messages(chat_id, target_user_id)
        
        # Get target user's interactions with others
        interactions = message_cache.get_user_interactions(chat_id, target_user_id)
        
        if not user_messages:
            await safe_edit_message(
                thinking_msg,
                f"❌ Нет доступных сообщений от {target_username} для анализа."
            )
            return
        
        # Perform personal analysis
        analysis_result = await ai_analyzer.analyze_user_communication(
            user_messages, interactions, target_username
        )
        
        # Delete thinking message and send private analysis
        await thinking_msg.delete()
        
        # Send analysis privately to requesting user
        await safe_send_message(
            bot,
            chat_id=user_id,
            text=analysis_result,
            parse_mode='Markdown'
        )
        
        # Confirm in group chat
        await message.answer(
            f"✅ Анализ {target_username} отправлен в личные сообщения."
        )
        
        logger.info(f"User analysis completed for target {target_user_id} by user {user_id} in chat {chat_id}")
        
    except Exception as e:
        await safe_edit_message(thinking_msg, f"❌ Ошибка при анализе: {str(e)}")
        logger.error(f"User analysis error: {e}")


@dp.message(Command("analyze_user_all"))
async def analyze_user_all_command(message: Message):
    """Analyze specific user's communication style across all chats (authorized users only)"""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    is_private_chat = message.chat.type == ChatType.PRIVATE
    
    # Check if user is authorized
    if not is_user_authorized(user_id):
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return
    
    # Check rate limiting
    if not check_rate_limit(user_id):
        await message.answer(
            f"⏱️ Подождите {Config.RATE_LIMIT_SECONDS} секунд между командами анализа."
        )
        return
    
    target_user_id = None
    target_username = None
    
    # Check if replying to a message (only in group chats)
    if not is_private_chat and message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        target_username = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name or "Пользователь"
    else:
        # Parse username or user_id from command
        command_parts = (message.text or "").split()
        if len(command_parts) < 2:
            usage_text = "❌ Использование:\n• `/analyze_user_all @username` - анализ по имени из всех чатов"
            if not is_private_chat:
                usage_text += "\n• Ответьте на сообщение пользователя командой `/analyze_user_all`"
            usage_text += "\n• `/analyze_user_all <user_id>` - анализ по числовому ID пользователя"
            await message.answer(usage_text)
            return
        
        user_input = command_parts[1]
        if user_input.startswith('@'):
            # Username search
            username = user_input[1:]
            try:
                # Try to find user by username in cached messages from all chats
                for chat_id in message_cache.get_all_chats():
                    all_messages = message_cache.get_last_n_messages(chat_id, 1000)
                    for msg in all_messages:
                        if msg.get('username', '').lower() == username.lower():
                            target_user_id = msg['user_id']
                            target_username = msg['username']
                            break
                    if target_user_id:
                        break
                
                if not target_user_id:
                    await message.answer(
                        f"❌ Пользователь @{username} не найден в кеше сообщений ни в одном из чатов."
                    )
                    return
            except Exception as e:
                await message.answer(f"❌ Ошибка поиска пользователя: {str(e)}")
                return
        elif user_input.isdigit():
            # User ID search
            target_user_id = int(user_input)
            # Try to find username in cache
            for chat_id in message_cache.get_all_chats():
                all_messages = message_cache.get_last_n_messages(chat_id, 1000)
                for msg in all_messages:
                    if msg.get('user_id') == target_user_id:
                        target_username = msg.get('username', f"User_{target_user_id}")
                        break
                if target_username:
                    break
            
            if not target_username:
                target_username = f"User_{target_user_id}"
        else:
            await message.answer(
                "❌ Неверный формат. Используйте @username, числовой user_id" + 
                (" или ответьте на сообщение пользователя." if not is_private_chat else ".")
            )
            return
    
    # Show thinking message
    thinking_msg = await message.answer("🤔 Анализирую стиль коммуникации из всех чатов...")
    
    try:
        # Get user's messages from all chats
        user_messages = message_cache.get_user_messages_all_chats(target_user_id)
        
        # Get user's interactions with others from all chats
        interactions = message_cache.get_user_interactions_all_chats(target_user_id)
        
        # Get user stats across all chats
        user_stats = message_cache.get_user_chat_stats(target_user_id)
        
        if not user_messages:
            await thinking_msg.edit_text(
                f"❌ Нет доступных сообщений от {target_username} для анализа из всех чатов. "
                "Пользователь еще не отправлял сообщения после добавления бота в чаты."
            )
            return
        
        # Perform personal analysis
        analysis_result = await ai_analyzer.analyze_user_communication(
            user_messages, interactions, target_username
        )
        
        # Add cross-chat statistics to the analysis
        stats_summary = (
            f"\n\n📊 **Статистика по всем чатам:**\n"
            f"• Всего сообщений: {user_stats['total_messages']}\n"
            f"• Чатов с активностью: {user_stats['chats_count']}\n"
        )
        
        if user_stats['oldest_message'] and user_stats['newest_message']:
            stats_summary += (
                f"• Период активности: {user_stats['oldest_message'].strftime('%Y-%m-%d')} - "
                f"{user_stats['newest_message'].strftime('%Y-%m-%d')}\n"
            )
        
        # Combine analysis with statistics
        full_analysis = analysis_result + stats_summary
        
        # Delete thinking message
        await thinking_msg.delete()
        
        if is_private_chat:
            # In private chat, send analysis directly to this chat
            await safe_send_message(
                message,
                text=full_analysis,
                parse_mode='Markdown'
            )
        else:
            # In group chat, send analysis privately to requesting user
            await safe_send_message(
                bot,
                chat_id=user_id,
                text=full_analysis,
                parse_mode='Markdown'
            )
            
            # Confirm in group chat
            await message.answer(
                f"✅ Анализ {target_username} из всех чатов отправлен в личные сообщения.\n"
                f"📊 Проанализировано {user_stats['total_messages']} сообщений из {user_stats['chats_count']} чатов."
            )
        
        logger.info(f"Cross-chat user analysis completed for target {target_user_id} by user {user_id}")
        
    except Exception as e:
        await safe_edit_message(thinking_msg, f"❌ Ошибка при анализе: {str(e)}")
        logger.error(f"Cross-chat user analysis error: {e}")


async def handle_analysis_command(message: Message, analysis_type: str):
    """Handle analysis commands with common logic"""
    # Only work in group chats
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("Команды анализа работают только в групповых чатах.")
        return
    
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check if user is authorized
    if not is_user_authorized(user_id):
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return
    
    # Check rate limiting
    if not check_rate_limit(user_id):
        await message.answer(
            f"⏱ Пожалуйста, подождите {Config.RATE_LIMIT_SECONDS} секунд между командами анализа."
        )
        return
    
    # Get messages based on analysis type
    if analysis_type == "last_100":
        messages = message_cache.get_last_n_messages(chat_id, 100)
        analysis_description = "последних 100 сообщений"
    elif analysis_type == "last_24h":
        messages = message_cache.get_messages_since(chat_id, datetime.now() - timedelta(hours=24))
        analysis_description = "сообщений за последние 24 часа"
    else:
        await message.answer("❌ Неизвестный тип анализа.")
        return
    
    if not messages:
        # Get cache stats to provide better feedback
        cache_stats = message_cache.get_chat_stats(chat_id)
        if cache_stats['total_messages'] == 0:
            await message.answer(
                "❌ Нет сообщений для анализа.\n\n"
                "🔍 **Возможные причины:**\n"
                "• Бот был добавлен недавно и еще не накопил сообщения\n"
                "• Боты в Telegram не видят историю до их добавления в чат\n"
                "• В чате пока нет текстовых сообщений (команды не считаются)\n\n"
                "💡 **Решение:** Подождите, пока участники напишут несколько сообщений после добавления бота."
            )
        else:
            await message.answer(
                f"❌ Недостаточно сообщений для анализа {analysis_description}.\n\n"
                f"📊 **Статистика чата:**\n"
                f"• Всего сообщений в кеше: {cache_stats['total_messages']}\n"
                f"• Активных пользователей: {cache_stats['unique_users']}\n"
                f"• Первое сообщение: {cache_stats['oldest_message'].strftime('%Y-%m-%d %H:%M') if cache_stats['oldest_message'] else 'Нет'}\n\n"
                f"💡 Попробуйте команду с меньшим количеством сообщений или подождите больше активности в чате."
            )
        return
    
    # Send notification in group chat
    await message.answer(
        f"🔍 Начинаю анализ {analysis_description} ({len(messages)} сообщений). "
        f"Отчет будет отправлен в личные сообщения."
    )
    
    # Send private notification about analysis start
    try:
        await bot.send_message(
            user_id,
            f"🔄 Анализирую {analysis_description} из чата '{message.chat.title}'. "
            "Это может занять несколько минут..."
        )
    except Exception as e:
        logger.error(f"Failed to send private notification: {e}")
        await message.answer("❌ Не удалось отправить уведомление в личные сообщения. Убедитесь, что вы начали диалог с ботом командой /start.")
        return
    
    # Perform analysis
    try:
        analysis_result = await ai_analyzer.analyze_messages(messages)
        
        # Send analysis result privately
        await safe_send_message(
            bot,
            chat_id=user_id,
            text=f"📊 **Анализ коммуникаций: {message.chat.title}**\n\n{analysis_result}",
            parse_mode='Markdown'
        )
        
        logger.info(f"Analysis completed for user {user_id} in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await safe_send_message(
            bot,
            chat_id=user_id,
            text="❌ Произошла ошибка при анализе сообщений. Попробуйте позже или обратитесь к администратору бота.",
            parse_mode='Markdown'
        )


@dp.message(F.text & F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cache_group_message(message: Message):
    """Cache all text messages from group chats"""
    # Skip bot commands
    if message.text and message.text.startswith('/'):
        return
    
    # Skip if no user info or text
    if not message.from_user or not message.text:
        return
    
    # Cache the message
    message_cache.add_message(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        username=message.from_user.username or message.from_user.first_name or "Пользователь",
        text=message.text,
        timestamp=datetime.now()
    )
    
    # Log every 10th message for monitoring
    cache_stats = message_cache.get_chat_stats(message.chat.id)
    if cache_stats['total_messages'] % 10 == 0:
        logger.info(f"Chat {message.chat.id} now has {cache_stats['total_messages']} cached messages from {cache_stats['unique_users']} users")


async def main():
    """Main function to start the bot"""
    logger.info("Starting Communication Coach Bot...")
    
    # Check required environment variables
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    if not Config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return
    
    if not Config.AUTHORIZED_USERS:
        logger.warning("No authorized users configured. Set AUTHORIZED_USERS environment variable with comma-separated user IDs.")
        logger.warning("Example: AUTHORIZED_USERS=123456789,987654321")
    else:
        logger.info(f"Authorized users: {Config.AUTHORIZED_USERS}")
        logger.info(f"Main admin: {Config.AUTHORIZED_USERS[0]}")
    
    try:
        # Start polling
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
