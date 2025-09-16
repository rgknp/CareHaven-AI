from abc import ABC, abstractmethod
from typing import Any

class DataSource(ABC):
    """
    Abstract base class for different data sources.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def get_data(self, patient_id: str) -> Any:
        """
        Retrieves a batch of clinical or streaming/iot data.
        """
        pass



