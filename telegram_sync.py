"""
Telegram sync orchestrator - core application logic.

Coordinates the event sync process:
1. Fetch events from Google Home API (with event types and timestamps)
2. Download videos from Nest API using Google Home timestamps
3. Send to Telegram with formatted captions
4. Track sent events to avoid duplicates (7-day history)

Event flow:
- Google Home API provides: event type, start/end time, event ID
- Nest API provides: video file (MP4 clip)
- Telegram gets: video + caption with event type and timestamp

Configuration:
- Timezone for display (auto-detected if not specified)
- Time format (12h/24h/custom strftime)
- Dry run mode for testing
- Force resend for debugging
"""

from nest_device import NestDevice
from tools import logger
from google_home_events import GoogleHomeEvents

from io import BytesIO
import pytz
import datetime
import os
import json
from dotenv import load_dotenv

from telegram import Bot, InputMediaVideo

load_dotenv()


class TelegramEventsSync(object):
    """
    Main sync orchestrator for Nest camera events to Telegram.

    Responsibilities:
    - Fetch events from Google Home API (event types + timestamps)
    - Download videos from Nest API
    - Send to Telegram channel with formatted captions
    - Track sent events (deduplication with 7-day auto-cleanup)
    - Handle timezone conversion and time formatting

    The sync process is idempotent - safe to run repeatedly without duplicates.
    Event tracking persists across restarts via sent_events.json.
    """

    FORMAT_24H = '%d/%m/%Y %H:%M:%S'
    FORMAT_12H = '%m/%d/%Y %I:%M:%S %p'

    DATA_DIR = os.getenv('DATA_DIR', '.')
    SENT_EVENTS_FILE = os.path.join(DATA_DIR, 'sent_events.json')

    def __init__(self, telegram_bot_token, telegram_channel_id, nest_camera_devices, google_connection, timezone=None, time_format=None, force_resend_all=False, dry_run=False) -> None:
        # Ensure data directory exists
        os.makedirs(self.DATA_DIR, exist_ok=True)

        self._telegram_bot = Bot(token=telegram_bot_token)
        self._telegram_channel_id = telegram_channel_id
        self._nest_camera_devices = nest_camera_devices
        self._force_resend_all = force_resend_all
        self._dry_run = dry_run

        # Google Home API provides event types (graceful degradation if unavailable)
        self._google_home_events = GoogleHomeEvents(google_connection)

        if timezone:
            try:
                self._display_timezone = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                logger.warning(f"Invalid TIMEZONE '{timezone}', falling back to auto-detect")
                timezone = None

        if not timezone:
            try:
                import tzlocal
                self._display_timezone = pytz.timezone(str(tzlocal.get_localzone()))
            except Exception:
                self._display_timezone = pytz.UTC

        logger.info(f"Using timezone for display: {self._display_timezone}")

        self._time_format = self._parse_time_format(time_format)
        logger.info(f"Using time format: {self._time_format}")

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
                return set(self._cleanup_old_events(data).keys())
        except Exception as e:
            logger.warning(f"Could not load sent events file: {e}, starting fresh")
            return set()

    def _cleanup_old_events(self, data):
        """
        Remove event history entries older than 7 days.

        Args:
            data: Dict of event_id -> ISO timestamp string

        Returns:
            Filtered dict with only recent events (< 7 days old)
        """
        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
        return {
            event_id: timestamp
            for event_id, timestamp in data.items()
            if datetime.datetime.fromisoformat(timestamp) > cutoff_time
        }

    def _save_sent_events(self):
        """Save sent event IDs to JSON file"""
        try:
            existing_data = {}
            if os.path.exists(self.SENT_EVENTS_FILE):
                with open(self.SENT_EVENTS_FILE, 'r') as f:
                    existing_data = json.load(f)

            current_time = datetime.datetime.now().isoformat()
            for event_id in self._recent_events:
                if event_id not in existing_data:
                    existing_data[event_id] = current_time

            with open(self.SENT_EVENTS_FILE, 'w') as f:
                json.dump(self._cleanup_old_events(existing_data), f, indent=2)

        except Exception as e:
            logger.error(f"Could not save sent events file: {e}")

    def _parse_time_format(self, time_format):
        """
        Parse TIME_FORMAT setting into strftime format string.

        Args:
            time_format: '24h', '12h', custom strftime format, or None

        Returns:
            Valid strftime format string (defaults to '%c' if invalid)
        """
        if not time_format:
            return '%c'  # System locale default

        time_format_lower = time_format.strip().lower()
        if time_format_lower == '24h':
            return self.FORMAT_24H
        elif time_format_lower == '12h':
            return self.FORMAT_12H
        else:
            try:
                datetime.datetime.now().strftime(time_format)
                return time_format
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid TIME_FORMAT '{time_format}': {e}, using default")
                return '%c'

    def _get_current_time_utc(self):
        """Get current time in UTC for API calls"""
        return pytz.UTC.localize(datetime.datetime.utcnow())

    async def sync_single_nest_camera(self, nest_device: NestDevice):

        logger.info(f"Syncing: {nest_device.device_id}")
        end_time_utc = self._get_current_time_utc()

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
        """
        Process and send events from Google Home API.

        For each event:
        1. Check if already sent (deduplication)
        2. Download video using Google Home timestamps
        3. Format caption with event type and timestamp
        4. Send to Telegram (or skip if dry run)
        5. Mark as sent in persistent storage

        Args:
            nest_device: NestDevice to download videos from
            google_home_events: List of GoogleHomeEvent objects
        """
        skipped = 0

        # Sort events chronologically (oldest first)
        google_home_events.sort(key=lambda event: event.start_time)

        for gh_event in google_home_events:
            event_id = f"{gh_event.start_time_ms}->{gh_event.end_time_ms}|{nest_device.device_id}"

            if event_id in self._recent_events:
                logger.debug(f"Event ({gh_event.description}) already sent, skipping..")
                skipped += 1
                continue

            logger.debug(f"Downloading event: {gh_event.description} [{gh_event.start_time}]")

            video_data = self._download_video_by_timestamps(
                nest_device,
                gh_event.start_time_ms,
                gh_event.end_time_ms
            )

            if not video_data:
                logger.warning(f"Failed to download video for event: {gh_event.description}")
                continue

            video_io = BytesIO(video_data)

            event_local_time = gh_event.start_time.astimezone(self._display_timezone)
            time_str = event_local_time.strftime(self._time_format)

            event_type = gh_event.description
            needs_suffix = not any(word in event_type.lower() for word in [" · ", "seen", "detected"])
            suffix = " Seen" if needs_suffix else ""
            video_caption = f"{event_type}{suffix} - {nest_device.device_name} [{time_str}]"

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

        self._save_sent_events()

    def _download_video_by_timestamps(self, nest_device: NestDevice, start_ms: int, end_ms: int) -> bytes:
        """
        Download video clip from Nest API.

        Uses timestamps from Google Home API for perfect alignment with event metadata.
        This mirrors how Google's website downloads videos.

        Args:
            nest_device: Device to download from
            start_ms: Event start time in milliseconds since epoch
            end_ms: Event end time in milliseconds since epoch

        Returns:
            Video bytes (MP4 file) or None if download fails
        """
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
        """
        Main sync entry point - process all cameras.

        Called periodically by the scheduler (default: every 2 minutes).
        Fetches new events and sends to Telegram for each configured camera.
        """
        logger.info("Syncing all camera devices")
        for nest_device in self._nest_camera_devices:
            await self.sync_single_nest_camera(nest_device)