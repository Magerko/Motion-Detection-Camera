# Motion Detection Camera

Система видеонаблюдения с обнаружением движения и уведомлениями в Telegram.

## Возможности

- Обнаружение движения с использованием OpenCV
- Распознавание людей с помощью MediaPipe (поза и лицо)
- Два режима работы: фото и видео
- Уведомления в Telegram с фото/видео при обнаружении движения
- Управление через Telegram бот (включение/выключение, смена режима)
- Автоматическая очистка старых файлов
- Конфигурация через .env файл

## Установка

1. Клонируйте репозиторий

2. Создайте виртуальное окружение:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `.env.example`:
```bash
copy .env.example .env
```

5. Настройте `.env`:
   - `TELEGRAM_BOT_TOKEN` - токен бота от @BotFather
   - `ALLOWED_USER_IDS` - ID пользователей через запятую

## Запуск

```bash
python main.py
```

## Команды бота

- `/start` - Начало работы, показ панели управления
- `/settings` - Настройки с клавиатурой управления
- `/status` - Быстрый статус системы

## Структура проекта

```
camera/
├── main.py                 # Точка входа
├── config.py               # Конфигурация
├── requirements.txt        # Зависимости
├── .env.example            # Пример конфигурации
├── bot_handler/            # Telegram бот
│   ├── bot.py              # Логика бота
│   └── state.py            # Состояние системы
├── motion_detection/       # Обнаружение движения
│   └── detector.py         # Детектор на OpenCV
└── image_processing/       # Обработка изображений
    └── identifier.py       # Распознавание объектов
```

## Параметры конфигурации

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `MIN_CONTOUR_AREA` | Минимальная площадь контура для детекции | 1000 |
| `FRAME_WIDTH` | Ширина кадра | 640 |
| `FRAME_HEIGHT` | Высота кадра | 480 |
| `PHOTO_COOLDOWN_PERIOD` | Пауза между фото (сек) | 30 |
| `VIDEO_FPS` | FPS видеозаписи | 15 |
| `VIDEO_NO_MOTION_STOP_DELAY` | Задержка остановки записи (сек) | 5 |
| `MAX_STORAGE_MB` | Лимит хранилища (МБ) | 500 |

## Требования

- Python 3.10+
- Веб-камера
- Windows/Linux/macOS

---

Проект для канала https://t.me/mcodeg
