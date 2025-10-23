from nest_api import NestDoorbellDevice
from tools import logger
from models import CameraEvent

from io import BytesIO
import pytz
import datetime
import os
import locale
import json
from pathlib import Path
from dotenv import load_dotenv

from telegram import Bot, InputMediaVideo

# Load environment variables
load_dotenv()


class TelegramEventsSync(object):

    # Preset formats
    FORMAT_24H = '%H:%M:%S %d/%m/%Y'  # 23:40:50 22/10/2025
    FORMAT_12H = '%I:%M:%S%p %m/%d/%Y'  # 11:40:50PM 10/22/2025
    
    SENT_EVENTS_FILE = 'sent_events.json'

    def __init__(self, telegram_bot_token, telegram_channel_id, nest_camera_devices, timezone=None, time_format=None, force_resend_all=False) -> None:
        self._telegram_bot = Bot(token=telegram_bot_token)
        self._telegram_channel_id = telegram_channel_id
        self._nest_camera_devices = nest_camera_devices
        self._force_resend_all = force_resend_all
        
        # Setup timezone for display purposes
        if timezone:
            self._display_timezone = pytz.timezone(timezone)
        else:
            # Auto-detect system timezone
            try:
                import tzlocal
                self._display_timezone = pytz.timezone(str(tzlocal.get_localzone()))
            except Exception:
                self._display_timezone = pytz.UTC
        
        logger.info(f"Using timezone for display: {self._display_timezone}")
        
        # Setup time format
        self._time_format = self._parse_time_format(time_format)
        logger.info(f"Using time format: {self._time_format}")
        
        # Load sent events from file (unless force resend is enabled)
        if self._force_resend_all:
            self._recent_events = set()
            logger.warning("FORCE_RESEND_ALL enabled - ignoring sent events history!")
        else:
            self._recent_events = self._load_sent_events()
            logger.info(f"Loaded {len(self._recent_events)} previously sent event IDs")

    def _load_sent_events(self):
        """Load sent event IDs from JSON file"""
        if not os.path.exists(self.SENT_EVENTS_FILE):
            return set()
        
        try:
            with open(self.SENT_EVENTS_FILE, 'r') as f:
                data = json.load(f)
                # Clean up entries older than 7 days
                cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
                filtered = {
                    event_id: timestamp 
                    for event_id, timestamp in data.items()
                    if datetime.datetime.fromisoformat(timestamp) > cutoff_time
                }
                return set(filtered.keys())
        except Exception as e:
            logger.warning(f"Could not load sent events file: {e}, starting fresh")
            return set()

    def _save_sent_events(self):
        """Save sent event IDs to JSON file"""
        try:
            # Load existing data to preserve timestamps
            existing_data = {}
            if os.path.exists(self.SENT_EVENTS_FILE):
                with open(self.SENT_EVENTS_FILE, 'r') as f:
                    existing_data = json.load(f)
            
            # Add new events with current timestamp
            current_time = datetime.datetime.now().isoformat()
            for event_id in self._recent_events:
                if event_id not in existing_data:
                    existing_data[event_id] = current_time
            
            # Clean up old entries (older than 7 days)
            cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
            filtered_data = {
                event_id: timestamp 
                for event_id, timestamp in existing_data.items()
                if datetime.datetime.fromisoformat(timestamp) > cutoff_time
            }
            
            with open(self.SENT_EVENTS_FILE, 'w') as f:
                json.dump(filtered_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Could not save sent events file: {e}")

    def _parse_time_format(self, time_format):
        """Parse time format setting and return strftime format string"""
        if time_format is None or time_format.strip() == '':
            # Use system locale default
            try:
                locale.setlocale(locale.LC_TIME, '')
            except:
                pass
            return '%c'
        
        time_format_lower = time_format.strip().lower()
        
        if time_format_lower == '24h':
            return self.FORMAT_24H
        elif time_format_lower == '12h':
            return self.FORMAT_12H
        else:
            # Assume it's a custom strftime format string
            return time_format

    def _get_current_time_utc(self):
        """Get current time in UTC for API calls"""
        return pytz.UTC.localize(datetime.datetime.utcnow())

    async def sync_single_nest_camera(self, nest_device : NestDoorbellDevice):

        logger.info(f"Syncing: {nest_device.device_id}")
        all_recent_camera_events : list[CameraEvent] = nest_device.get_events(
            end_time = self._get_current_time_utc(),  # Always use UTC for API calls
            duration_minutes=3 * 60 # This is the maxmimum time Google is saving my videos
        )

        logger.info(f"[{nest_device.device_id}] Received {len(all_recent_camera_events)} camera events")

        skipped = 0
        for camera_event_obj in all_recent_camera_events:
            # Always check if already sent in THIS run
            if camera_event_obj.event_id in self._recent_events:
                logger.debug(f"CameraEvent ({camera_event_obj}) already sent, skipping..")
                skipped += 1
                continue

            logger.debug(f"Downloading camera event: {camera_event_obj}")
            video_data = nest_device.download_camera_event(camera_event_obj)
            video_io = BytesIO(video_data)

            video_caption = f"{nest_device.device_name} clip"
            # Convert event time to display timezone for the caption
            event_local_time = camera_event_obj.start_time.astimezone(self._display_timezone)
            time_str = event_local_time.strftime(self._time_format)
            
            video_media = InputMediaVideo(
                media=video_io,
                caption=f"{video_caption} [{time_str}]"
            )

            await self._telegram_bot.send_media_group(
                chat_id=self._telegram_channel_id,
                media=[video_media],
                disable_notification=True,
            )
            logger.debug("Sent clip successfully")

            self._recent_events.add(camera_event_obj.event_id)

        downloaded_and_sent = len(all_recent_camera_events) - skipped
        logger.info(f"[{nest_device.device_id}] Downloaded and sent: {downloaded_and_sent}, skipped (already sent): {skipped}")
        
        # Save after processing each camera
        self._save_sent_events()

    async def sync(self):
        logger.info("Syncing all camera devices")
        for nest_device in self._nest_camera_devices:
            await self.sync_single_nest_camera(nest_device)