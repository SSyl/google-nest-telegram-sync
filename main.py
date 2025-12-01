from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

from tools import logger
from google_auth_wrapper import GoogleConnection
from telegram_sync import TelegramEventsSync
from nest_sdm_api import create_sdm_client_from_env
from pubsub_listener import create_pubsub_listener_from_env

import os
import datetime
import asyncio
import threading
from apscheduler.schedulers.asyncio import AsyncIOScheduler


GOOGLE_MASTER_TOKEN = os.getenv("GOOGLE_MASTER_TOKEN")
GOOGLE_USERNAME = os.getenv("GOOGLE_USERNAME")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
FORCE_RESEND_ALL = os.getenv("FORCE_RESEND_ALL", "false").lower() in ("true", "1")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1")

TIMEZONE = os.getenv("TIMEZONE")
TIME_FORMAT = os.getenv("TIME_FORMAT")

# Get refresh interval from env, default to 2 minutes
try:
    REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", "2"))
except ValueError:
    logger.warning("Invalid REFRESH_INTERVAL_MINUTES value, using default of 2 minutes")
    REFRESH_INTERVAL_MINUTES = 2

assert GOOGLE_MASTER_TOKEN and GOOGLE_USERNAME and TELEGRAM_CHANNEL_ID and TELEGRAM_BOT_TOKEN


def main():

    logger.info("Welcome to the Google Nest Doorbell <-> Telegram Syncer")

    logger.info("Initializing the Google connection using the master_token")
    google_connection = GoogleConnection(GOOGLE_MASTER_TOKEN, GOOGLE_USERNAME)

    logger.info("Getting Camera Devices")
    nest_camera_devices = google_connection.get_nest_camera_devices()
    logger.info(f"Found {len(nest_camera_devices)} Camera Device{'s' if len(nest_camera_devices) > 1 else ''}")

    tes = TelegramEventsSync(
        telegram_bot_token=TELEGRAM_BOT_TOKEN,
        telegram_channel_id=TELEGRAM_CHANNEL_ID,
        timezone=TIMEZONE,
        time_format=TIME_FORMAT,
        force_resend_all=FORCE_RESEND_ALL,
        dry_run=DRY_RUN,
        nest_camera_devices=nest_camera_devices
    )

    logger.info("Initialized a Telegram Syncer")
    if DRY_RUN:
        logger.warning("DRY RUN MODE ENABLED - Videos will NOT be sent to Telegram!")

    # Initialize SDM API client (for event types)
    logger.info("Initializing Smart Device Management API...")
    sdm_client = create_sdm_client_from_env()
    if sdm_client:
        logger.info("SDM API initialized - real-time events enabled")
        # List devices to verify connection
        sdm_devices = sdm_client.list_devices()
    else:
        logger.warning("SDM API not configured - using polling mode only")

    # Create Pub/Sub listener for real-time events
    pubsub_listener = create_pubsub_listener_from_env(tes.handle_realtime_event)

    # Start Pub/Sub listener in background thread
    if pubsub_listener:
        logger.info("Starting Pub/Sub listener for real-time events...")
        pubsub_thread = threading.Thread(
            target=pubsub_listener.start_listening,
            daemon=True,
            name="PubSubListener"
        )
        pubsub_thread.start()
        logger.info("Pub/Sub listener started in background")
    else:
        logger.warning("Pub/Sub listener not configured - real-time events disabled")

    # Also keep the scheduler running as a fallback
    logger.info(f"Starting fallback polling every {REFRESH_INTERVAL_MINUTES} minute(s)")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Schedule the job to run every x minutes
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(
        tes.sync,
        'interval',
        minutes=REFRESH_INTERVAL_MINUTES,
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=10)
    )
    scheduler.start()

    logger.info("=" * 60)
    logger.info("Application started successfully!")
    logger.info("  - Real-time events: " + ("ENABLED" if pubsub_listener else "DISABLED"))
    logger.info("  - Fallback polling: ENABLED")
    logger.info("=" * 60)

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        scheduler.shutdown()
        loop.close()

if __name__ == "__main__":
    main()