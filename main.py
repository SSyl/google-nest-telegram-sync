"""
Google Nest Camera to Telegram Sync Application

Entry point for the sync service. Initializes Google connection, discovers Nest cameras,
and schedules periodic syncing of camera events to a Telegram channel.

Uses AsyncIOScheduler to run sync jobs at configurable intervals.
"""

from dotenv import load_dotenv

load_dotenv()

from tools import logger
from google_auth_wrapper import GoogleConnection
from telegram_sync import TelegramEventsSync

import os
import datetime
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

__version__ = "1.0"

GOOGLE_MASTER_TOKEN = os.getenv("GOOGLE_MASTER_TOKEN")
GOOGLE_USERNAME = os.getenv("GOOGLE_USERNAME")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
FORCE_RESEND_ALL = os.getenv("FORCE_RESEND_ALL", "false").lower() in ("true", "1")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1")

TIMEZONE = os.getenv("TIMEZONE")
TIME_FORMAT = os.getenv("TIME_FORMAT")

try:
    REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", "2"))
except ValueError:
    logger.warning("Invalid REFRESH_INTERVAL_MINUTES, using default of 2 minutes")
    REFRESH_INTERVAL_MINUTES = 2

assert GOOGLE_MASTER_TOKEN and GOOGLE_USERNAME and TELEGRAM_CHANNEL_ID and TELEGRAM_BOT_TOKEN


def main():
    """
    Initialize and run the sync service.

    Sets up Google authentication, discovers Nest cameras, initializes Telegram sync,
    and starts the scheduler to run periodic syncs.
    """
    logger.info("Welcome to the Google Nest Doorbell <-> Telegram Sync")
    logger.info(f"Version: {__version__}")

    logger.info("Initializing the Google connection using the master_token")
    google_connection = GoogleConnection(GOOGLE_MASTER_TOKEN, GOOGLE_USERNAME)

    logger.info("Getting Camera Devices")
    nest_camera_devices = google_connection.get_nest_camera_devices()
    logger.info(f"Found {len(nest_camera_devices)} camera device(s)")

    tes = TelegramEventsSync(
        telegram_bot_token=TELEGRAM_BOT_TOKEN,
        telegram_channel_id=TELEGRAM_CHANNEL_ID,
        nest_camera_devices=nest_camera_devices,
        google_connection=google_connection,
        timezone=TIMEZONE,
        time_format=TIME_FORMAT,
        force_resend_all=FORCE_RESEND_ALL,
        dry_run=DRY_RUN
    )

    logger.info("Initialized a Telegram Sync")
    if DRY_RUN:
        logger.warning("DRY RUN MODE ENABLED - Videos will NOT be sent to Telegram!")
    logger.info(f"Syncing every {REFRESH_INTERVAL_MINUTES} minute(s)")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(
        tes.sync,
        'interval',
        minutes=REFRESH_INTERVAL_MINUTES,
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=10)
    )
    scheduler.start()

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.close()

if __name__ == "__main__":
    main()