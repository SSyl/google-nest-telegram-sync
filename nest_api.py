import pytz
import datetime
from models import CameraEvent

from tools import logger
import xml.etree.ElementTree as ET

class NestDoorbellDevice(object):

    NEST_API_DOMAIN = "https://nest-camera-frontend.googleapis.com"

    EVENTS_URI = NEST_API_DOMAIN + "/dashmanifest/namespace/nest-phoenix-prod/device/{device_id}"
    DOWNLOAD_VIDEO_URI = NEST_API_DOMAIN + "/mp4clip/namespace/nest-phoenix-prod/device/{device_id}"

    def __init__(self, google_connection, device_id, device_name, google_home_device_id=None):
        self._connection = google_connection
        self._device_id = device_id
        self._device_name = device_name
        self._google_home_device_id = google_home_device_id  # For fetching event types

    def __parse_events(self, events_xml):
        from tools import VERBOSE

        if VERBOSE:
            logger.debug(f"Full XML response:\n{events_xml.decode('utf-8') if isinstance(events_xml, bytes) else events_xml}")

        root = ET.fromstring(events_xml)

        if VERBOSE:
            # Check root attributes for any metadata
            logger.debug(f"Root MPD attributes: {root.attrib}")

        periods = root.findall(".//{urn:mpeg:dash:schema:mpd:2011}Period")
        events = []
        for period in periods:
            if VERBOSE:
                logger.debug(f"XML Period attributes: {period.attrib}")
                # Check ALL child elements recursively
                for child in period.iter():
                    if child.attrib:
                        logger.debug(f"  Child {child.tag}: {child.attrib}")

            # Extract period ID from BaseURL if available (for debugging only - not used for matching)
            if VERBOSE:
                period_id = None
                base_url = period.find(".//{urn:mpeg:dash:schema:mpd:2011}BaseURL")
                if base_url is not None and base_url.text:
                    # Extract UUID from URL like: .../periods/64d4934c-898e-454e-b343-878e49b53b61/...
                    import re
                    match = re.search(r'/periods/([a-f0-9-]+)/', base_url.text)
                    if match:
                        period_id = match.group(1)
                        logger.debug(f"Nest API period_id: {period_id} (not used for matching)")

            events.append(CameraEvent.from_attrib(period.attrib, self))
        return events

    def __download_event_by_time(self, start_time, end_time):
        params = {
            "start_time" : int(start_time.timestamp()*1000), # 1707368737876
            "end_time" : int(end_time.timestamp()*1000), # 1707368757371
        }
        return self._connection.make_nest_get_request(
            self._device_id,
            NestDoorbellDevice.DOWNLOAD_VIDEO_URI, 
            params=params
        )
    
    @property
    def device_id(self):
        return self._device_id

    @property
    def device_name(self):
        return self._device_name

    @property
    def google_home_device_id(self):
        return self._google_home_device_id

    def get_events(self, end_time: datetime.datetime, duration_minutes: int):
        start_time = end_time - datetime.timedelta(minutes=duration_minutes)
        params = {
            "start_time" : start_time.astimezone(pytz.timezone("UTC")).isoformat()[:-9]+"Z", # 2024-02-07T19:32:25.250Z
            "end_time" : end_time.astimezone(pytz.timezone("UTC")).isoformat()[:-9]+"Z", # 2024-02-08T19:32:25.250Z
            "types": 4,
            "variant" : 2,
        }
        return self.__parse_events(
            self._connection.make_nest_get_request(
                self._device_id,
                NestDoorbellDevice.EVENTS_URI,
                params=params
            )
        )
        
    def download_camera_event(self, camera_event : CameraEvent):
        return self.__download_event_by_time(
            camera_event.start_time,
            camera_event.end_time
        ) 
