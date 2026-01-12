# main.py
import asyncio
import time
import os
import logging
from collections import Counter

try:
    from config import (
        MIN_CONTOUR_AREA, FRAME_WIDTH, FRAME_HEIGHT,
        TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS,
        PHOTO_COOLDOWN_PERIOD, VIDEO_FPS,
        VIDEO_NO_MOTION_STOP_DELAY, SCREENSHOT_DIR, VIDEO_RECORD_PATH,
        MAX_STORAGE_MB
    )
    from bot_handler import bot_state
except ModuleNotFoundError as e:
    print(f"Критическая ошибка импорта в main.py: {e}. Убедитесь, что все файлы на месте и PYTHONPATH настроен.")
    exit(1)

from motion_detection import MotionDetector
from image_processing import ObjectIdentifier
from bot_handler import start_bot_polling as start_telegram_bot, broadcast_alert

logger = logging.getLogger(__name__)


def format_detected_objects(detected_list):
    if not detected_list or detected_list == ["неизвестный объект"] or detected_list == ["ошибка идентификации"]:
        return "Объекты не идентифицированы."

    counts = Counter(detected_list)
    parts = []
    for item, count in counts.items():
        parts.append(f"{item}: {count}")
    return "В кадре: " + ", ".join(parts) + "."


def get_directory_size_mb(directory):
    total = 0
    if os.path.exists(directory):
        for f in os.listdir(directory):
            fp = os.path.join(directory, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total / (1024 * 1024)


def cleanup_old_files(directory, max_mb):
    if not os.path.exists(directory):
        return

    current_size = get_directory_size_mb(directory)
    if current_size <= max_mb:
        return

    files = []
    for f in os.listdir(directory):
        fp = os.path.join(directory, f)
        if os.path.isfile(fp):
            files.append((fp, os.path.getmtime(fp), os.path.getsize(fp)))

    files.sort(key=lambda x: x[1])

    for fp, _, size in files:
        if current_size <= max_mb * 0.8:
            break
        try:
            os.remove(fp)
            current_size -= size / (1024 * 1024)
            logger.info(f"Удален старый файл: {fp}")
        except Exception as e:
            logger.warning(f"Не удалось удалить {fp}: {e}")


async def main_loop():
    logger.info("Инициализация системы детекции...")
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    if not os.path.exists(VIDEO_RECORD_PATH):
        os.makedirs(VIDEO_RECORD_PATH, exist_ok=True)

    cleanup_old_files(SCREENSHOT_DIR, MAX_STORAGE_MB / 2)
    cleanup_old_files(VIDEO_RECORD_PATH, MAX_STORAGE_MB / 2)

    detector = MotionDetector(min_area=MIN_CONTOUR_AREA, frame_width=FRAME_WIDTH, frame_height=FRAME_HEIGHT)
    identifier = ObjectIdentifier()

    if not detector.start_capture(camera_index=0):
        logger.error("Не удалось запустить детектор движения.")
        return

    logger.info("Система детекции движения запущена.")

    last_photo_alert_time = 0
    is_video_recording = False
    current_video_filename = None
    last_motion_time_video = 0
    initial_objects_for_video_caption = []

    try:
        while True:
            if not bot_state.monitoring_active:
                await asyncio.sleep(1)
                if is_video_recording:  # Если выключили мониторинг во время записи
                    detector.stop_video_recording()
                    logger.info(f"Запись видео {current_video_filename} прервана из-за отключения мониторинга.")
                    # Можно отправить незаконченное видео или удалить
                    # os.remove(current_video_filename) # если не хотим отправлять
                    is_video_recording = False
                    current_video_filename = None
                continue

            frame_with_motion = detector.detect_motion()
            current_time = time.time()

            if bot_state.current_mode == "photo":
                if is_video_recording:  # Переключились с видео на фото во время записи
                    detector.stop_video_recording()
                    logger.info(f"Запись видео {current_video_filename} остановлена из-за смены режима на фото.")
                    # Решаем, отправлять ли его
                    # await broadcast_alert(f"Видеозапись остановлена: {format_detected_objects(initial_objects_for_video_caption)}", current_video_filename, "video")
                    is_video_recording = False
                    current_video_filename = None

                if frame_with_motion is not None:
                    if (current_time - last_photo_alert_time) > PHOTO_COOLDOWN_PERIOD:
                        logger.info("Фото режим: Движение обнаружено!")
                        screenshot_path = detector.capture_screenshot(frame_with_motion, directory=SCREENSHOT_DIR)
                        if screenshot_path:
                            detected_objects_list = identifier.identify_objects(screenshot_path)
                            caption = f"🚨 Фото: {format_detected_objects(detected_objects_list)}"
                            await broadcast_alert(caption, screenshot_path, "photo")
                            last_photo_alert_time = current_time
                        else:
                            logger.warning("Не удалось сохранить скриншот.")
                else:  # Нет движения в фото режиме
                    pass  # Ничего не делаем


            elif bot_state.current_mode == "video":
                if frame_with_motion is not None:
                    last_motion_time_video = current_time
                    if not is_video_recording:
                        current_video_filename = detector.start_video_recording(directory=VIDEO_RECORD_PATH,
                                                                                fps=VIDEO_FPS)
                        if current_video_filename:
                            is_video_recording = True
                            # Получаем объекты для заголовка в начале записи
                            temp_shot_for_caption = detector.capture_screenshot(frame_with_motion,
                                                                                SCREENSHOT_DIR)  # Временный кадр для анализа
                            if temp_shot_for_caption:
                                initial_objects_for_video_caption = identifier.identify_objects(temp_shot_for_caption)
                                os.remove(temp_shot_for_caption)  # Удаляем временный кадр
                            else:
                                initial_objects_for_video_caption = ["не удалось получить объекты"]

                            caption_start = f"📹 Началась видеозапись: {format_detected_objects(initial_objects_for_video_caption)}"
                            await broadcast_alert(caption_start)  # Уведомление без файла
                            logger.info(f"Видео режим: Начата запись видео {current_video_filename}")
                        else:
                            logger.error("Не удалось начать запись видео.")

                    if is_video_recording:
                        detector.write_video_frame(frame_with_motion)

                elif is_video_recording:  # Движения нет, но запись идет
                    if (current_time - last_motion_time_video) > VIDEO_NO_MOTION_STOP_DELAY:
                        logger.info(
                            f"Видео режим: Нет движения в течение {VIDEO_NO_MOTION_STOP_DELAY} сек. Остановка записи.")
                        video_path = detector.stop_video_recording()
                        if video_path:
                            caption_end = f"📹 Видеозапись завершена: {format_detected_objects(initial_objects_for_video_caption)}"
                            await broadcast_alert(caption_end, video_path, "video")
                        is_video_recording = False
                        current_video_filename = None
                        initial_objects_for_video_caption = []

            await asyncio.sleep(0.05)  # Уменьшаем задержку для более плавной записи видео

    except KeyboardInterrupt:
        logger.info("Остановка основного цикла по команде пользователя...")
    except Exception as e:
        logger.error(f"Произошла ошибка в главном цикле: {e}", exc_info=True)
    finally:
        logger.info("Завершение работы детектора...")
        if is_video_recording and detector.video_writer:  # Убедимся, что видео сохранилось при экстренном выходе
            path = detector.stop_video_recording()
            logger.info(f"Принудительно сохранено видео: {path}")
        detector.stop_capture()
        logger.info("Детектор остановлен.")


async def main_app_entrypoint():
    logger.info("Запуск основного приложения...")
    telegram_task = asyncio.create_task(start_telegram_bot())
    main_loop_task = asyncio.create_task(main_loop())

    try:
        done, pending = await asyncio.wait(
            [telegram_task, main_loop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            if task.exception():
                logger.error(f"Задача завершилась с ошибкой: {task.exception()}", exc_info=task.exception())
    except Exception as e:
        logger.critical(f"Критическая ошибка в asyncio.wait: {e}", exc_info=True)
    finally:
        if not telegram_task.done(): telegram_task.cancel()
        if not main_loop_task.done(): main_loop_task.cancel()
        await asyncio.gather(telegram_task, main_loop_task, return_exceptions=True)
        logger.info("Основное приложение завершает работу.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    valid_config = True
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("Критическая ошибка: TELEGRAM_BOT_TOKEN не установлен.")
        valid_config = False
    if not ALLOWED_USER_IDS or 123456789 in ALLOWED_USER_IDS:
        logger.warning("ВНИМАНИЕ: Список ALLOWED_USER_IDS пуст или содержит примеры.")
    if not valid_config: exit(1)

    try:
        asyncio.run(main_app_entrypoint())
    except KeyboardInterrupt:
        logger.info("Программа завершена пользователем (Ctrl+C).")
    except Exception as e:
        logger.critical(f"Непредвиденная критическая ошибка при запуске: {e}", exc_info=True)
