# bot_handler/bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

try:
    from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
    from . import state as bot_state
except ModuleNotFoundError:
    import sys
    import os

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
    from bot_handler import state as bot_state

default_bot_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=TELEGRAM_BOT_TOKEN, default=default_bot_properties)
dp = Dispatcher()
logger = logging.getLogger(__name__)


class AccessMiddleware:
    def __init__(self, allowed_ids: list[int]):
        self.allowed_ids = allowed_ids
        self.logger = logging.getLogger(f"{__name__}.AccessMiddleware")

    async def __call__(self, handler, event: types.Update, data: dict):
        user = None
        if isinstance(event, types.Message):
            user = event.from_user
        elif isinstance(event, types.CallbackQuery):
            user = event.from_user

        if user and user.id not in self.allowed_ids:
            self.logger.warning(f"Access denied for user ID: {user.id} ({user.full_name})")
            if isinstance(event, types.Message):
                await event.answer("Access denied.")
            elif isinstance(event, types.CallbackQuery):
                await event.answer("Access denied.", show_alert=True)
            return
        return await handler(event, data)


dp.update.outer_middleware(AccessMiddleware(ALLOWED_USER_IDS))


def get_main_keyboard():
    monitoring_text = "Выключить мониторинг" if bot_state.monitoring_active else "Включить мониторинг"
    monitoring_action = "toggle_monitoring_off" if bot_state.monitoring_active else "toggle_monitoring_on"

    mode_text_photo = "📸 Фото режим" + (" ✅" if bot_state.current_mode == "photo" else "")
    mode_text_video = "📹 Видео режим" + (" ✅" if bot_state.current_mode == "video" else "")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=monitoring_text, callback_data=monitoring_action)],
        [
            InlineKeyboardButton(text=mode_text_photo, callback_data="set_mode_photo"),
            InlineKeyboardButton(text=mode_text_video, callback_data="set_mode_video")
        ]
    ])
    return keyboard


async def send_status_message(chat_id: int):
    status_text = (
        f"Состояние мониторинга: {hbold('ВКЛЮЧЕН') if bot_state.monitoring_active else hbold('ВЫКЛЮЧЕН')}\n"
        f"Текущий режим: {hbold(bot_state.current_mode.upper())}"
    )
    await bot.send_message(chat_id, status_text, reply_markup=get_main_keyboard())


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет, {hbold(message.from_user.full_name)}!")
    await send_status_message(message.chat.id)


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    await send_status_message(message.chat.id)


@dp.message(Command("status"))
async def cmd_status(message: Message):
    status = "ВКЛЮЧЕН" if bot_state.monitoring_active else "ВЫКЛЮЧЕН"
    mode = bot_state.current_mode.upper()
    await message.answer(f"Мониторинг: {status}\nРежим: {mode}")


@dp.callback_query(F.data.startswith("toggle_monitoring_"))
async def cq_toggle_monitoring(callback: CallbackQuery):
    action = callback.data.split("_")[-1]
    if action == "on":
        bot_state.monitoring_active = True
        logger.info("Мониторинг включен пользователем")
    elif action == "off":
        bot_state.monitoring_active = False
        logger.info("Мониторинг выключен пользователем")

    await callback.message.edit_text(
        f"Состояние мониторинга: {hbold('ВКЛЮЧЕН') if bot_state.monitoring_active else hbold('ВЫКЛЮЧЕН')}\n"
        f"Текущий режим: {hbold(bot_state.current_mode.upper())}",
        reply_markup=get_main_keyboard()
    )
    await callback.answer(f"Мониторинг {'включен' if bot_state.monitoring_active else 'выключен'}")


@dp.callback_query(F.data.startswith("set_mode_"))
async def cq_set_mode(callback: CallbackQuery):
    new_mode = callback.data.split("_")[-1]
    if new_mode in ["photo", "video"]:
        bot_state.current_mode = new_mode
        logger.info(f"Режим изменен на: {new_mode}")

    await callback.message.edit_text(
        f"Состояние мониторинга: {hbold('ВКЛЮЧЕН') if bot_state.monitoring_active else hbold('ВЫКЛЮЧЕН')}\n"
        f"Текущий режим: {hbold(bot_state.current_mode.upper())}",
        reply_markup=get_main_keyboard()
    )
    await callback.answer(f"Режим установлен на: {new_mode}")


async def send_alert_to_user(user_id: int, message_text: str, file_path: str = None, file_type: str = "photo"):
    try:
        if file_path:
            input_file = FSInputFile(file_path)
            if file_type == "photo":
                await bot.send_photo(chat_id=user_id, photo=input_file, caption=message_text)
            elif file_type == "video":
                await bot.send_video(chat_id=user_id, video=input_file, caption=message_text, supports_streaming=True)
        else:
            await bot.send_message(chat_id=user_id, text=message_text)
        logger.info(f"Оповещение ({file_type if file_path else 'text'}) отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке оповещения ({file_type}) пользователю {user_id}: {e}", exc_info=True)


async def broadcast_alert(message_text: str, file_path: str = None, file_type: str = "photo"):
    logger.info(f"Начало рассылки оповещения: {message_text[:50]}...")
    tasks = []
    for user_id in ALLOWED_USER_IDS:
        tasks.append(send_alert_to_user(user_id, message_text, file_path, file_type))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Ошибка при отправке пользователю {ALLOWED_USER_IDS[i]}: {result}")


async def start_bot_polling():
    logger.info("Запуск Telegram бота в режиме polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске polling: {e}", exc_info=True)
    finally:
        logger.info("Polling остановлен.")
        await bot.session.close()
