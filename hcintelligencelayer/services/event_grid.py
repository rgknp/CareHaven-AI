import os
import logging
from typing import Dict, Any, List
from azure.eventgrid import EventGridPublisherClient
from azure.core.credentials import AzureKeyCredential

# Set up logging for the client
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EventGridClient:
    """
    A client to interact with Azure Event Grid for publishing events.
    """
    def __init__(self):
        """
        Initializes the client by retrieving connection details from environment variables.
        """
        self.endpoint = os.getenv("AZURE_EVENT_GRID_ENDPOINT")
        self.key = os.getenv("AZURE_EVENT_GRID_KEY")
        
        if not self.endpoint or not self.key:
            raise ValueError("Environment variables 'AZURE_EVENT_GRID_ENDPOINT' and 'AZURE_EVENT_GRID_KEY' must be set.")

        self.credential = AzureKeyCredential(self.key)
        self.client = EventGridPublisherClient(self.endpoint, self.credential)
        logger.info("EventGridClient initialized from environment variables.")

    def publish(self, events: List[Dict[str, Any]]):
        """
        Publishes a list of events to the Event Grid topic.

        Args:
            events (List[Dict[str, Any]]): A list of event dictionaries to be sent.
        """
        if not events:
            logger.info("No events to publish.")
            return

        try:
            # Event Grid expects a specific schema (e.g., CloudEvents or Event Grid Schema)
            # We'll use the standard Event Grid Schema here.
            event_grid_events = [
                {
                    "id": event.get("id", "event-id-not-specified"),
                    "subject": f"/agents/{event.get('agent_id', 'unknown')}",
                    "data": event,
                    "eventtype": event.get("event_type", "unspecified_event"),
                    "dataVersion": "1.0",
                }
                for event in events
            ]
            self.client.send(event_grid_events)
            logger.info(f"Published {len(events)} events to Azure Event Grid.")
        except Exception as e:
            logger.error(f"Failed to publish events to Azure Event Grid: {e}")

