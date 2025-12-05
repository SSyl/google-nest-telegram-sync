from nest_device import NestDevice
from tools import logger
from google_home_events import GoogleHomeEvents

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
    FORMAT_12H = '%I:%M:%S %p %m/%d/%Y'  # 11:40:50 PM 10/22/2025

    SENT_EVENTS_FILE = 'sent_events.json'

    def __init__(self, telegram_bot_token, telegram_channel_id, nest_camera_devices, google_connection, timezone=None, time_format=None, force_resend_all=False, dry_run=False) -> None:
        self._telegram_bot = Bot(token=telegram_bot_token)
        self._telegram_channel_id = telegram_channel_id
        self._nest_camera_devices = nest_camera_devices
        self._force_resend_all = force_resend_all
        self._dry_run = dry_run

        # Initialize Google Home API for event types (optional - graceful degradation)
        self._google_home_events = GoogleHomeEvents(google_connection)
        
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
        # Ensure the data directory exists
        data_dir = os.path.dirname(self.SENT_EVENTS_FILE)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"Created directory: {data_dir}")

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

    async def sync_single_nest_camera(self, nest_device: NestDevice):

        logger.info(f"Syncing: {nest_device.device_id}")
        end_time_utc = self._get_current_time_utc()

        # Fetch events from Google Home API
        if not nest_device.google_home_device_id:
            logger.error(f"[{nest_device.device_id}] No Google Home device ID - cannot fetch events")
            return

        try:
            start_time_ms = int((end_time_utc.timestamp() - (3 * 60 * 60)) * 1000)
            end_time_ms = int(end_time_utc.timestamp() * 1000)
            google_home_events = self._google_home_events.get_events(
                nest_device.google_home_device_id,
                start_time_ms,
                end_time_ms
            )

            if google_home_events:
                logger.info(f"[{nest_device.device_id}] Fetched {len(google_home_events)} events from Google Home")
                await self._process_google_home_events(nest_device, google_home_events)
            else:
                logger.info(f"[{nest_device.device_id}] No events found in the last 3 hours")

        except Exception as e:
            logger.error(f"[{nest_device.device_id}] Failed to fetch events from Google Home API: {e}")

    async def _process_google_home_events(self, nest_device: NestDevice, google_home_events):
        """Process events from Google Home API with precise timestamps and event types."""
        skipped = 0

        for gh_event in google_home_events:
            # Generate unique event ID based on Google Home event
            event_id = f"{gh_event.start_time_ms}->{gh_event.end_time_ms}|{nest_device.device_id}"

            # Check if already sent
            if event_id in self._recent_events:
                logger.debug(f"Event ({gh_event.description}) already sent, skipping..")
                skipped += 1
                continue

            logger.debug(f"Downloading event: {gh_event.description} [{gh_event.start_time}]")

            # Download video using Google Home API timestamps
            video_data = self._download_video_by_timestamps(
                nest_device,
                gh_event.start_time_ms,
                gh_event.end_time_ms
            )

            if not video_data:
                logger.warning(f"Failed to download video for event: {gh_event.description}")
                continue

            video_io = BytesIO(video_data)

            # Convert event time to display timezone for the caption
            event_local_time = gh_event.start_time.astimezone(self._display_timezone)
            time_str = event_local_time.strftime(self._time_format)

            # Build caption with event type
            event_type = gh_event.description

            # Format the caption based on event type content
            # If it already contains " · " or ends with "detected", keep as-is
            # Otherwise, add "Seen" for natural reading
            if " · " in event_type or event_type.endswith("detected") or "," in event_type:
                video_caption = f"{event_type} - {nest_device.device_name} [{time_str}]"
            else:
                video_caption = f"{event_type} Seen - {nest_device.device_name} [{time_str}]"

            logger.info(f"Caption: {video_caption}")

            video_media = InputMediaVideo(
                media=video_io,
                caption=video_caption
            )

            if self._dry_run:
                logger.info(f"[DRY RUN] Would send: {video_caption} ({len(video_data)} bytes)")
            else:
                await self._telegram_bot.send_media_group(
                    chat_id=self._telegram_channel_id,
                    media=[video_media],
                    disable_notification=True,
                )
                logger.debug("Sent clip successfully")

            self._recent_events.add(event_id)

        downloaded_and_sent = len(google_home_events) - skipped
        logger.info(f"[{nest_device.device_id}] Downloaded and sent: {downloaded_and_sent}, skipped (already sent): {skipped}")

        # Save after processing each camera
        self._save_sent_events()

    def _download_video_by_timestamps(self, nest_device: NestDevice, start_ms: int, end_ms: int) -> bytes:
        """Download video from Nest API using millisecond timestamps."""
        try:
            params = {
                "start_time": start_ms,
                "end_time": end_ms,
            }
            return nest_device._connection.make_nest_get_request(
                nest_device.device_id,
                nest_device.DOWNLOAD_VIDEO_URI,
                params=params
            )
        except Exception as e:
            logger.error(f"Failed to download video: {e}")
            return None

    async def sync(self):
        logger.info("Syncing all camera devices")
        for nest_device in self._nest_camera_devices:
            await self.sync_single_nest_camera(nest_device)