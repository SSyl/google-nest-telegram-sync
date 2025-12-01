"""
Google Cloud Pub/Sub Event Listener

Listens for real-time Nest camera events via Pub/Sub.
Parses event data and triggers video downloads.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
import pytz
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from concurrent.futures import TimeoutError as ConnectionTimeoutError
from tools import logger


class NestEventListener:
    """Listens for Nest events via Google Cloud Pub/Sub"""

    def __init__(self, service_account_file, topic_name, event_callback):
        """
        Initialize Pub/Sub listener

        Args:
            service_account_file: Path to service account JSON file
            topic_name: Full Pub/Sub topic name (projects/PROJECT_ID/topics/TOPIC_NAME)
            event_callback: Async function to call when event received (event_data)
        """
        self.service_account_file = service_account_file
        self.topic_name = topic_name
        self.event_callback = event_callback

        # Create subscription name based on topic
        project_id = topic_name.split("/")[1]
        topic_id = topic_name.split("/")[-1]
        self.subscription_name = f"projects/{project_id}/subscriptions/{topic_id}-python-sub"

        # Initialize credentials
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file
        )

        # Create subscriber client
        self.subscriber = pubsub_v1.SubscriberClient(credentials=credentials)

        logger.info(f"Pub/Sub listener initialized")
        logger.info(f"  Topic: {topic_name}")
        logger.info(f"  Subscription: {self.subscription_name}")

    def _create_subscription_if_needed(self):
        """Create Pub/Sub subscription if it doesn't exist"""
        try:
            # Try to get the subscription
            self.subscriber.get_subscription(request={"subscription": self.subscription_name})
            logger.debug(f"Using existing subscription: {self.subscription_name}")

        except Exception:
            # Subscription doesn't exist, create it
            try:
                logger.info(f"Creating new subscription: {self.subscription_name}")

                request = {
                    "name": self.subscription_name,
                    "topic": self.topic_name,
                    "ack_deadline_seconds": 60,
                    "enable_message_ordering": False
                }

                self.subscriber.create_subscription(request=request)
                logger.info("Subscription created successfully")

            except Exception as e:
                logger.error(f"Failed to create subscription: {e}")
                raise

    def _parse_event_message(self, message):
        """
        Parse Pub/Sub message into event data

        Args:
            message: Pub/Sub message object

        Returns:
            Dict with event information or None if parsing fails
        """
        try:
            # Decode message data
            data = json.loads(message.data.decode('utf-8'))

            logger.debug(f"Received Pub/Sub message: {json.dumps(data, indent=2)}")

            # Extract event information
            event_id = data.get("eventId")
            timestamp_str = data.get("timestamp")
            resource_update = data.get("resourceUpdate", {})

            # Get device name
            device_name = resource_update.get("name", "")

            # Get events
            events = resource_update.get("events", {})

            # Parse event types
            event_types = []
            for event_key, event_value in events.items():
                # Event keys look like: "sdm.devices.events.CameraPerson.Person"
                if "events" in event_key:
                    event_type = event_key.split(".")[-1].lower()
                    event_types.append(event_type)

            # Convert timestamp to datetime
            if timestamp_str:
                event_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                event_time = datetime.now(pytz.UTC)

            return {
                "event_id": event_id,
                "timestamp": event_time,
                "device_name": device_name,
                "device_id": device_name.split("/")[-1] if "/" in device_name else device_name,
                "event_types": event_types,
                "raw_data": data
            }

        except Exception as e:
            logger.error(f"Failed to parse Pub/Sub message: {e}")
            logger.debug(f"Raw message data: {message.data}")
            return None

    def _message_callback(self, message):
        """
        Callback function for received Pub/Sub messages

        Args:
            message: Pub/Sub message object
        """
        logger.debug(f"Received Pub/Sub message ID: {message.message_id}")

        # Parse event data
        event_data = self._parse_event_message(message)

        if event_data:
            logger.info(f"Event received: {event_data['event_types']} from {event_data['device_id']} at {event_data['timestamp']}")

            # Call the event callback asynchronously
            try:
                # Create event loop if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Run the callback
                loop.run_until_complete(self.event_callback(event_data))

            except Exception as e:
                logger.error(f"Error in event callback: {e}")

        # Acknowledge the message
        message.ack()
        logger.debug(f"Message acknowledged: {message.message_id}")

    def start_listening(self):
        """
        Start listening for Pub/Sub messages

        This is a blocking call that runs indefinitely.
        """
        # Create subscription if needed
        self._create_subscription_if_needed()

        logger.info("Starting Pub/Sub listener...")
        logger.info("Waiting for real-time events...")

        # Start streaming pull
        streaming_pull_future = self.subscriber.subscribe(
            self.subscription_name,
            callback=self._message_callback
        )

        try:
            # Wait indefinitely
            streaming_pull_future.result()

        except KeyboardInterrupt:
            logger.info("Stopping Pub/Sub listener (keyboard interrupt)...")
            streaming_pull_future.cancel()

        except ConnectionTimeoutError:
            logger.warning("Pub/Sub connection timeout, will retry...")
            streaming_pull_future.cancel()

        except Exception as e:
            logger.error(f"Pub/Sub listener error: {e}")
            streaming_pull_future.cancel()
            raise


def create_pubsub_listener_from_env(event_callback):
    """
    Create Pub/Sub listener from environment variables

    Args:
        event_callback: Async function to call when event received

    Returns:
        NestEventListener instance or None if config is missing
    """
    service_account_file = os.getenv("SDM_SERVICE_ACCOUNT_FILE", "service-account.json")
    topic_name = os.getenv("SDM_PUBSUB_TOPIC")

    if not topic_name:
        logger.warning("SDM_PUBSUB_TOPIC not configured. Pub/Sub listener disabled.")
        return None

    if not os.path.exists(service_account_file):
        logger.error(f"Service account file not found: {service_account_file}")
        return None

    try:
        listener = NestEventListener(service_account_file, topic_name, event_callback)
        return listener

    except Exception as e:
        logger.error(f"Failed to create Pub/Sub listener: {e}")
        return None
