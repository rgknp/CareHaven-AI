from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional

# Set up logging for the agent
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Agent(ABC):
    """
    Abstract base class for a healthcare intelligence agent.

    This class provides a robust and type-safe contract for all AI agents,
    with added support for logging and error handling.
    """
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """
        Initializes the agent with a unique ID and configuration.
        """
        self.agent_id = agent_id
        self.config = config
        self.prediction_interval = self.config.get('prediction_interval_seconds', 10)
        self.logger = logging.getLogger(f'Agent.{self.agent_id}')
        self.last_run_timestamp = None

    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """
        Acquires data from configured sources.

        This method should handle potential data source failures.
        """
        try:
            # Placeholder for data acquisition logic
            pass
        except Exception as e:
            self.logger.error(f"Failed to acquire data: {e}")
            raise

    @abstractmethod
    def run_prediction(self, data: Dict[str, Any]) -> Any:
        """
        Runs the prediction model on the acquired data.

        The specific prediction logic is implemented by the concrete agent.
        """
        try:
            # Placeholder for prediction logic
            pass
        except Exception as e:
            self.logger.error(f"Prediction failed with error: {e}")
            raise

    @abstractmethod
    def generate_output(self, prediction_result: Any) -> Optional[Dict[str, Any]]:
        """
        Processes the prediction result and generates an output event if it's
        a 'high value' event.

        Returns:
            An event dictionary with a defined structure, or None.
        """
        try:
            # Placeholder for output generation logic
            pass
        except Exception as e:
            self.logger.error(f"Failed to generate output event: {e}")
            return None