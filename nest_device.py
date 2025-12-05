"""
Nest device container and video download interface.

Provides a lightweight wrapper around Nest camera device information and the
Nest API video download endpoint. All event metadata comes from Google Home API;
this module only handles video file retrieval.

Architecture:
- Google Home API: Event metadata, types, timestamps (google_home_events.py)
- Nest API: Video file download only (this module)
"""


class NestDevice:
    """
    Lightweight device container with properties and video download URL.

    The Nest API is only used for video downloads - all event metadata
    comes from Google Home API.
    """

    # Nest API video download endpoint
    DOWNLOAD_VIDEO_URI = "https://nest-camera-frontend.googleapis.com/mp4clip/namespace/nest-phoenix-prod/device/{device_id}"

    def __init__(self, connection, device_id, device_name, google_home_device_id):
        """
        Initialize a Nest device.

        Args:
            connection: GoogleConnection instance for making authenticated requests
            device_id: Nest device ID (e.g., "DEVICE_D7D734D5EEDBEEBA")
            device_name: Human-readable device name (e.g., "Front Door")
            google_home_device_id: Google Home device ID for fetching events
        """
        self._connection = connection
        self.device_id = device_id
        self.device_name = device_name
        self.google_home_device_id = google_home_device_id
