from nest_api import NestDoorbellDevice
from tools import logger
from models import CameraEvent

from io import BytesIO
import pytz
import datetime
import os
import locale
import json
import asyncio
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

    def __init__(self, telegram_bot_token, telegram_channel_id, nest_camera_devices, timezone=None, time_format=None, force_resend_all=False, dry_run=False) -> None:
        self._telegram_bot = Bot(token=telegram_bot_token)
        self._telegram_channel_id = telegram_channel_id
        self._nest_camera_devices = nest_camera_devices
        self._force_resend_all = force_resend_all
        self._dry_run = dry_run
        
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


    async def handle_realtime_event(self, event_data):
        """
        Handle real-time event from Pub/Sub with event type information

        Args:
            event_data: Dict containing:
                - event_id: Unique event ID
                - timestamp: Event datetime
                - device_id: Device ID
                - event_types: List of event types (e.g., ['person', 'motion'])
                - raw_data: Raw Pub/Sub data
        """
        device_id = event_data.get('device_id')
        device_display_name = event_data.get('device_display_name', '')
        event_types = event_data.get('event_types', [])
        event_time = event_data.get('timestamp')

        logger.info(f"Received real-time event: {event_types} from '{device_display_name}' at {event_time}")

        # Find the matching camera device by name (SDM and unofficial API use different IDs)
        nest_device = None
        logger.debug(f"Looking for device with display name: '{device_display_name}'")
        logger.debug(f"Available cameras: {[(device.device_name, device.device_id) for device in self._nest_camera_devices]}")

        for device in self._nest_camera_devices:
            # Match by device name (case-insensitive, partial match)
            device_name_lower = device.device_name.lower()
            display_name_lower = device_display_name.lower()

            # Check if names match exactly or if one contains the other
            if (device_name_lower == display_name_lower or
                device_name_lower in display_name_lower or
                display_name_lower in device_name_lower):
                logger.debug(f"Matched device: '{device.device_name}' with SDM name '{device_display_name}' ({device.device_id})")
                nest_device = device
                break

        if not nest_device:
            logger.warning(f"Device '{device_display_name}' not found in configured cameras")
            logger.warning(f"Available device names: {[device.device_name for device in self._nest_camera_devices]}")
            return

        # Generate event type display string
        event_type_str = self._format_event_types(event_types)

        # Wait 2 minutes for the event to complete and for Google to encode the video
        logger.info(f"Waiting 2 minutes for event to complete and encode...")
        await asyncio.sleep(120)  # 2 minutes

        logger.info(f"Processing event: {event_type_str} from {nest_device.device_name}")

        # Download the video clip for this event
        # Download a 1-minute clip: 5 seconds before event start to 55 seconds after (60 seconds total)
        try:
            start_time = event_time - datetime.timedelta(seconds=5)
            end_time = event_time + datetime.timedelta(seconds=55)

            # Download the video using the unofficial API
            logger.debug(f"Downloading video clip from {start_time} to {end_time}")
            video_data = nest_device._NestDoorbellDevice__download_event_by_time(start_time, end_time)

            if not video_data:
                logger.warning(f"No video data returned for event {event_data.get('event_id')}")
                return

            # Convert event time to display timezone
            event_local_time = event_time.astimezone(self._display_timezone)
            time_str = event_local_time.strftime(self._time_format)

            # Format caption with event type
            video_caption = f"{event_type_str} - {nest_device.device_name} [{time_str}]"

            # Send to Telegram
            if self._dry_run:
                logger.info(f"[DRY RUN] Would send: {video_caption} ({len(video_data)} bytes)")
            else:
                video_io = BytesIO(video_data)
                video_media = InputMediaVideo(
                    media=video_io,
                    caption=video_caption
                )

                await self._telegram_bot.send_media_group(
                    chat_id=self._telegram_channel_id,
                    media=[video_media],
                    disable_notification=True,
                )
                logger.info(f"Sent real-time event to Telegram: {video_caption}")

            # Track this event
            event_id = f"{start_time.isoformat()}->{end_time.isoformat()}|{device_id}"
            self._recent_events.add(event_id)
            self._save_sent_events()

        except Exception as e:
            logger.error(f"Failed to process real-time event: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _format_event_types(self, event_types):
        """
        Format event types list into a display string

        Args:
            event_types: List of event type strings (e.g., ['person', 'motion'])

        Returns:
            Formatted string (e.g., "Person Detected")
        """
        if not event_types:
            return "Event"

        # Event type display names
        type_map = {
            'person': 'Person Detected',
            'motion': 'Motion Detected',
            'sound': 'Sound Detected',
            'package': 'Package Detected',
            'animal': 'Animal Detected',
            'vehicle': 'Vehicle Detected',
            'chime': 'Doorbell Pressed'
        }

        # Get the most specific event type (prefer person over motion, etc.)
        priority = ['person', 'package', 'animal', 'vehicle', 'chime', 'sound', 'motion']

        for event_type in priority:
            if event_type in event_types:
                return type_map.get(event_type, event_type.title())

        # If no priority match, use the first one
        return type_map.get(event_types[0], event_types[0].title())