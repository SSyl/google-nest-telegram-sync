"""
Google Home API integration for fetching camera events.
Provides complete event data including type, timestamps, and video clip info.
"""

import requests
import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from tools import logger


@dataclass
class GoogleHomeEvent:
    """Represents a camera event from Google Home API."""
    event_id: str
    description: str  # e.g., "Person", "Package detected · Person"
    start_time: datetime.datetime  # UTC
    end_time: datetime.datetime    # UTC

    @property
    def start_time_ms(self) -> int:
        """Start time in milliseconds since epoch."""
        return int(self.start_time.timestamp() * 1000)

    @property
    def end_time_ms(self) -> int:
        """End time in milliseconds since epoch."""
        return int(self.end_time.timestamp() * 1000)


class GoogleHomeEvents:
    """
    Fetches camera event metadata from Google Home API using OAuth authentication.
    Uses existing GoogleConnection for authentication - no cookies needed.
    """

    FOYER_ENDPOINT = "https://googlehomefoyer-pa.clients6.google.com/$rpc/google.internal.home.foyer.v1.CameraService/ListTimelinePeriods"

    # Static headers required by the API
    HEADERS_BASE = {
        'Content-Type': 'application/json+protobuf',
        'X-Server-Token': 'CAMSEhUJ45f_C9a4yibZwhTc5gAdBw==',
        'x-foyer-client-environment': 'CAc=',
    }

    def __init__(self, google_connection):
        """
        Initialize with existing GoogleConnection.

        Args:
            google_connection: GoogleConnection instance (already authenticated)
        """
        self._connection = google_connection

    def get_events(self, device_id: str, start_time_ms: int, end_time_ms: int) -> List[GoogleHomeEvent]:
        """
        Fetch events from Google Home API for a specific time range.

        Args:
            device_id: Device/structure ID (from Google Home, not Nest device ID)
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch

        Returns:
            List of GoogleHomeEvent objects with event type and precise timestamps
            Returns empty list if API call fails (graceful degradation)
        """
        try:
            # Get OAuth access token (auto-refreshed by glocaltokens)
            access_token = self._connection._google_auth.get_access_token()
            if not access_token:
                logger.warning("Could not get access token for Google Home API")
                return []

            # Prepare request
            end_sec = end_time_ms // 1000
            end_ns = (end_time_ms % 1000) * 1000000
            start_sec = start_time_ms // 1000
            start_ns = (start_time_ms % 1000) * 1000000

            payload = [[device_id, [end_sec, end_ns], [start_sec, start_ns], None, 12], 1]

            headers = {
                **self.HEADERS_BASE,
                'Authorization': f'Bearer {access_token}',
            }

            logger.debug(f"Fetching events from Google Home API for device {device_id}")

            response = requests.post(
                self.FOYER_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                logger.warning(f"Google Home API returned status {response.status_code}")
                return []

            # Parse response
            return self._parse_events(response.json())

        except Exception as e:
            logger.warning(f"Failed to fetch events from Google Home API: {e}")
            return []

    def _parse_events(self, timeline_data) -> List[GoogleHomeEvent]:
        """
        Parse events from Google Home API response.

        The response contains events with human-readable descriptions and precise timestamps.
        Multiple events at the same timestamp are combined into a single event.

        Returns:
            List of GoogleHomeEvent objects
        """
        from tools import VERBOSE
        import pytz

        events = []
        events_by_timestamp = {}  # Temp dict for combining events at same time

        try:
            if not timeline_data or len(timeline_data) < 2:
                return events

            timeline_periods = timeline_data[1]

            for period in timeline_periods:
                if not period or len(period) < 3:
                    continue

                events_array = period[2]
                if not events_array or not isinstance(events_array, list):
                    continue

                # Each event: [event_id, description, timestamp_str, [start_time], [end_time], ...]
                for event in events_array:
                    if not event or len(event) < 5:
                        continue

                    if VERBOSE:
                        logger.debug(f"Full event structure (length {len(event)}): {event[:10]}")

                    event_id = str(event[0])
                    event_description = event[1]
                    start_time_array = event[3]  # [seconds, nanoseconds]
                    end_time_array = event[4]    # [seconds, nanoseconds]

                    if not (event_description and start_time_array and end_time_array
                            and len(start_time_array) >= 2 and len(end_time_array) >= 2):
                        continue

                    # Convert to datetime objects (UTC)
                    start_timestamp = int(start_time_array[0]) + int(start_time_array[1]) / 1e9
                    end_timestamp = int(end_time_array[0]) + int(end_time_array[1]) / 1e9

                    start_time = datetime.datetime.fromtimestamp(start_timestamp, tz=pytz.UTC)
                    end_time = datetime.datetime.fromtimestamp(end_timestamp, tz=pytz.UTC)

                    # Use millisecond timestamp as key for combining events
                    start_ms = int(start_timestamp * 1000)

                    # Handle multiple events at same timestamp by combining descriptions
                    if start_ms in events_by_timestamp:
                        existing = events_by_timestamp[start_ms]
                        # Combine descriptions if different
                        if event_description not in existing.description:
                            existing.description = f"{existing.description}, {event_description}"
                            logger.info(f"Combined events at {start_ms}: {existing.description}")
                    else:
                        new_event = GoogleHomeEvent(
                            event_id=event_id,
                            description=event_description,
                            start_time=start_time,
                            end_time=end_time
                        )
                        events_by_timestamp[start_ms] = new_event
                        logger.debug(f"Found event: {event_description} at {start_time}")

            # Convert dict to list
            events = list(events_by_timestamp.values())

        except Exception as e:
            logger.warning(f"Error parsing Google Home events: {e}")

        return events
