"""
Google Smart Device Management API Client

Handles OAuth authentication and API interactions with the official Google SDM API.
Provides access to device information and event metadata.
"""

import os
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from tools import logger


class SDMClient:
    """Client for interacting with Google Smart Device Management API"""

    API_BASE = "https://smartdevicemanagement.googleapis.com/v1"
    TOKEN_URI = "https://oauth2.googleapis.com/token"

    def __init__(self, project_id, client_id, client_secret, refresh_token):
        """
        Initialize SDM API client

        Args:
            project_id: SDM Project ID from Device Access Console
            client_id: OAuth 2.0 Client ID
            client_secret: OAuth 2.0 Client Secret
            refresh_token: OAuth refresh token
        """
        self.project_id = project_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

        # Initialize OAuth credentials
        self.credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=self.TOKEN_URI,
            client_id=client_id,
            client_secret=client_secret
        )

        # Refresh the access token
        self._refresh_access_token()

    def _refresh_access_token(self):
        """Refresh the OAuth access token"""
        try:
            logger.debug("Refreshing SDM API access token...")
            self.credentials.refresh(Request())
            logger.debug("SDM API access token refreshed successfully")
        except Exception as e:
            logger.error(f"Failed to refresh SDM API access token: {e}")
            raise

    def _make_request(self, method, endpoint, **kwargs):
        """
        Make an authenticated request to the SDM API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests

        Returns:
            Response JSON data
        """
        # Refresh token if expired
        if not self.credentials.valid:
            self._refresh_access_token()

        url = f"{self.API_BASE}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json"
        }

        logger.debug(f"SDM API Request: {method} {url}")

        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()

        return response.json()

    def list_devices(self):
        """
        List all devices in the project

        Returns:
            List of device objects with metadata
        """
        endpoint = f"enterprises/{self.project_id}/devices"

        try:
            data = self._make_request("GET", endpoint)
            devices = data.get("devices", [])

            logger.info(f"Found {len(devices)} device(s) in SDM project")

            for device in devices:
                device_name = device.get("name", "Unknown")
                device_type = device.get("type", "Unknown")
                display_name = device.get("traits", {}).get("sdm.devices.traits.Info", {}).get("customName", "No Name")
                logger.debug(f"  - {device_name} ({device_type}) - Display name: {display_name}")

            return devices

        except Exception as e:
            logger.error(f"Failed to list SDM devices: {e}")
            return []

    def get_device(self, device_name):
        """
        Get detailed information about a specific device

        Args:
            device_name: Full device name (e.g., enterprises/.../devices/...)

        Returns:
            Device object with full details
        """
        # Remove the base path if it's a full name
        if device_name.startswith("enterprises/"):
            endpoint = device_name
        else:
            endpoint = f"enterprises/{self.project_id}/devices/{device_name}"

        try:
            device = self._make_request("GET", endpoint)
            logger.debug(f"Retrieved device details for {device.get('name')}")
            return device

        except Exception as e:
            logger.error(f"Failed to get device {device_name}: {e}")
            return None

    def get_device_id_from_name(self, full_device_name):
        """
        Extract device ID from full device name

        Args:
            full_device_name: Full name like 'enterprises/.../devices/DEVICE_ID'

        Returns:
            Just the device ID portion
        """
        if "/" in full_device_name:
            return full_device_name.split("/")[-1]
        return full_device_name

    def get_camera_devices(self):
        """
        Get all camera devices with relevant traits

        Returns:
            List of camera devices
        """
        all_devices = self.list_devices()

        camera_devices = []
        for device in all_devices:
            # Check if device is a camera (has CameraLiveStream or CameraEventImage traits)
            traits = device.get("traits", {})
            if any(trait.startswith("sdm.devices.traits.Camera") for trait in traits.keys()):
                camera_devices.append(device)

        logger.info(f"Found {len(camera_devices)} camera device(s)")
        return camera_devices


def create_sdm_client_from_env():
    """
    Create SDM client from environment variables

    Returns:
        SDMClient instance or None if credentials are missing
    """
    project_id = os.getenv("SDM_PROJECT_ID")
    client_id = os.getenv("SDM_CLIENT_ID")
    client_secret = os.getenv("SDM_CLIENT_SECRET")
    refresh_token = os.getenv("SDM_REFRESH_TOKEN")

    if not all([project_id, client_id, client_secret, refresh_token]):
        logger.warning("SDM API credentials not fully configured. Skipping SDM integration.")
        logger.debug(f"Missing: {', '.join([k for k, v in {'SDM_PROJECT_ID': project_id, 'SDM_CLIENT_ID': client_id, 'SDM_CLIENT_SECRET': client_secret, 'SDM_REFRESH_TOKEN': refresh_token}.items() if not v])}")
        return None

    try:
        client = SDMClient(project_id, client_id, client_secret, refresh_token)
        logger.info("SDM API client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize SDM API client: {e}")
        return None
