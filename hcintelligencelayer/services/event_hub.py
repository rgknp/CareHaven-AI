import os
import asyncio
import logging
from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub.aio import EventHubConsumerClient
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AzureEventHubClient:
    """
    A client to interact with Azure Event Hub, using environment variables for configuration.
    """
    def __init__(self, consumer_group='$Default'):
        """
        Initializes the client by retrieving connection details from environment variables.
        """
        # Retrieve connection string and event hub name from environment variables
        self.connection_str = os.getenv("AZURE_EVENTHUB_CONNECTION_STR")
        self.eventhub_name = os.getenv("AZURE_EVENTHUB_NAME")

        if not self.connection_str or not self.eventhub_name:
            raise ValueError("Environment variables 'AZURE_EVENTHUB_CONNECTION_STR' and 'AZURE_EVENTHUB_NAME' must be set.")

        self.consumer_group = consumer_group
        self.producer_client = None
        logger.info("AzureEventHubClient initialized from environment variables.")

    # All other methods (initialize_producer, publish, receive_messages, close) remain the same as the previous implementation
    async def initialize_producer(self):
        """Initializes the producer client for sending events."""
        if self.producer_client is None:
            self.producer_client = EventHubProducerClient.from_connection_string(
                conn_str=self.connection_str,
                eventhub_name=self.eventhub_name
            )
            logger.info("Event Hub producer client initialized.")
            
    async def publish(self, events: List[Dict[str, Any]]):
        """
        Publishes a list of events to the Event Hub.
        """
        if self.producer_client is None:
            await self.initialize_producer()

        try:
            async with self.producer_client:
                event_data_batch = await self.producer_client.create_batch()
                for event in events:
                    event_data_batch.add(EventData(str(event)))
                await self.producer_client.send_batch(event_data_batch)
                logger.info(f"Published {len(events)} events to Azure Event Hub.")
        except Exception as e:
            logger.error(f"Failed to publish events to Azure Event Hub: {e}")

    async def receive_messages(self, on_event_received):
        """
        Starts an asynchronous listener to receive messages from the Event Hub.
        """
        consumer_client = EventHubConsumerClient.from_connection_string(
            conn_str=self.connection_str,
            consumer_group=self.consumer_group,
            eventhub_name=self.eventhub_name,
        )
        logger.info(f"Starting to receive messages from Event Hub: {self.eventhub_name}")
        
        async with consumer_client:
            await consumer_client.receive_batch(
                on_event_received,
                max_batch_size=10,
                max_wait_time=5
            )

    async def close(self):
        """Closes the producer client."""
        if self.producer_client:
            await self.producer_client.close()
            logger.info("Producer client closed.")