"""
Simple device container for Nest camera information.
Used for video downloads via Nest API.
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
