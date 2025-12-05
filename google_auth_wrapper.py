"""
Google authentication and device discovery.

Provides OAuth token management with automatic refresh and Nest camera device discovery
via Google's HomeGraph API. Extends glocaltokens to support multiple OAuth scopes
(Nest API requires a different scope than default Google Home access).

Key responsibilities:
- Multi-scope OAuth token management with auto-refresh
- Nest camera device discovery via HomeGraph
- Authenticated API requests to Nest services
"""

import datetime
import requests
from nest_device import NestDevice 

from tools import logger
import glocaltokens.client

class GLocalAuthenticationTokensMultiService(glocaltokens.client.GLocalAuthenticationTokens):
    """
    Extended glocaltokens client with multi-scope OAuth support.

    The base glocaltokens client caches a single access token, but Nest API
    requires a different OAuth scope than default Google Home. This extension
    tracks which scope was used and refreshes when the scope changes.

    Token lifecycle:
    - Cached until expiration (typically 1 hour)
    - Auto-refreshed using Google Master Token
    - Per-scope caching (different tokens for different services)
    """

    def __init__(self, *args, **kwargs) -> None:
        super(GLocalAuthenticationTokensMultiService, self).__init__(*args, **kwargs)

        self._last_access_token_service = None
    
    def get_access_token(self, service=glocaltokens.client.ACCESS_TOKEN_SERVICE) -> str | None:
        """Return existing or fetch access_token"""
        if (
            self.access_token is None
            or self.access_token_date is None
            or self._has_expired(self.access_token_date, glocaltokens.client.ACCESS_TOKEN_DURATION)
            or self._last_access_token_service != service
        ):
            logger.debug(
                "There is no access_token stored, "
                "or it has expired, getting a new one..."
            )
            master_token = self.get_master_token()
            if master_token is None:
                logger.debug("Unable to obtain master token.")
                return None
            if self.username is None:
                logger.error("Username is not set.")
                return None
            res = glocaltokens.client.perform_oauth(
                self._escape_username(self.username),
                master_token,
                self.get_android_id(),
                app=glocaltokens.client.ACCESS_TOKEN_APP_NAME,
                service=service,
                client_sig=glocaltokens.client.ACCESS_TOKEN_CLIENT_SIGNATURE,
            )
            if "Auth" not in res:
                logger.error("[!] Could not get access token.")
                logger.debug("Request response: %s", res)
                return None
            self.access_token = res["Auth"]
            self.access_token_date = datetime.datetime.now()
            self._last_access_token_service = service
        logger.debug(
            "Access token: %s, datetime %s",
            self.access_token,
            self.access_token_date,
        )
        return self.access_token

class GoogleConnection(object):
    """
    Google API connection manager for Nest camera integration.

    Manages authentication, device discovery, and API requests to both Google Home
    and Nest services. Provides methods for discovering Nest cameras and making
    authenticated requests to Nest's video API.
    """

    NAME = "Google"

    NEST_SCOPE = "oauth2:https://www.googleapis.com/auth/nest-account"

    def __init__(self, master_token, username, password="FAKE_PASSWORD"):
        self._google_auth = GLocalAuthenticationTokensMultiService(
            master_token=master_token, 
            username=username, 
            password=password,
        )

    def make_nest_get_request(self, device_id : str, url : str, params={}):
        """
        Make authenticated GET request to Nest API.

        Args:
            device_id: Nest device ID
            url: URI template with {device_id} placeholder
            params: Query parameters

        Returns:
            Response content (bytes for video, parsed data for other endpoints)
        """
        url = url.format(device_id=device_id)
        logger.debug(f"Sending request to: '{url}' with params: '{params}'")

        access_token = self._google_auth.get_access_token(service=GoogleConnection.NEST_SCOPE)
        if not access_token:
            raise Exception("Couldn't get a Nest access token")
        
        res = requests.get(
            url=url, 
            params=params, 
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        res.raise_for_status()
        return res.content

    def get_nest_camera_devices(self):
        """
        Discover Nest cameras via Google HomeGraph API.

        Returns:
            List of NestDevice objects for all Nest cameras in the Google account.
            Each device has Nest device ID and Google Home device ID for API calls.
        """
        homegraph_response = self._google_auth.get_homegraph()

        return [
            NestDevice(
                connection=self,
                device_id=device.device_info.agent_info.unique_id,
                device_name=device.device_name,
                google_home_device_id=device.device_info.device_id  # For Google Home API
            )
            for device in homegraph_response.home.devices
            if "action.devices.traits.CameraStream" in device.traits and "Nest" in device.hardware.model
        ]
