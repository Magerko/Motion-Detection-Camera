import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_IDS = [int(uid) for uid in os.getenv("ALLOWED_USER_IDS", "").split(",") if uid.strip()]

MIN_CONTOUR_AREA = int(os.getenv("MIN_CONTOUR_AREA", 1000))
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", 640))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", 480))

PHOTO_COOLDOWN_PERIOD = int(os.getenv("PHOTO_COOLDOWN_PERIOD", 30))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", 15))
VIDEO_NO_MOTION_STOP_DELAY = int(os.getenv("VIDEO_NO_MOTION_STOP_DELAY", 5))

VIDEO_RECORD_PATH = os.getenv("VIDEO_RECORD_PATH", "motion_videos")
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "motion_screenshots")

MAX_STORAGE_MB = int(os.getenv("MAX_STORAGE_MB", 500))
