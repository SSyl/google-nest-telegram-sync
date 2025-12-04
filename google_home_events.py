"""
Google Home API integration for fetching camera event types.
Provides event descriptions like "Package detected · Person" for Nest camera events.
"""

import requests
from typing import Dict, Optional
from tools import logger


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

    def get_event_types(self, device_id: str, start_time_ms: int, end_time_ms: int) -> Dict[str, str]:
        """
        Fetch event types from Google Home API for a specific time range.

        Args:
            device_id: Device/structure ID (from Google Home, not Nest device ID)
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch

        Returns:
            Dictionary mapping timestamp_ms -> event_description
            Example: {"1764825280332": "Package no longer seen · Person"}
            Returns empty dict if API call fails (graceful degradation)
        """
        try:
            # Get OAuth access token (auto-refreshed by glocaltokens)
            access_token = self._connection._google_auth.get_access_token()
            if not access_token:
                logger.warning("Could not get access token for Google Home API")
                return {}

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

            logger.debug(f"Fetching event types from Google Home API for device {device_id}")

            response = requests.post(
                self.FOYER_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                logger.warning(f"Google Home API returned status {response.status_code}")
                return {}

            # Parse response
            return self._parse_events(response.json())

        except Exception as e:
            logger.warning(f"Failed to fetch event types from Google Home API: {e}")
            return {}

    def _parse_events(self, timeline_data) -> Dict[str, str]:
        """
        Parse event descriptions from Google Home API response.

        The response contains events with human-readable descriptions.
        We map them by timestamp (in milliseconds) for easy lookup.

        Returns:
            Dict mapping "start_time_ms" -> "event_description"
        """
        events = {}

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

                    event_description = event[1]
                    start_time_array = event[3]  # [seconds, nanoseconds]

                    if event_description and start_time_array and len(start_time_array) >= 2:
                        # Convert to milliseconds timestamp for matching
                        start_ms = str(int(start_time_array[0]) * 1000 + int(start_time_array[1]) // 1000000)
                        events[start_ms] = event_description
                        logger.debug(f"Found event: {event_description} at timestamp {start_ms}")

        except Exception as e:
            logger.warning(f"Error parsing Google Home events: {e}")

        return events
