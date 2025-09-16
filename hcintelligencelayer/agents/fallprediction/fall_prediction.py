import joblib
from typing import Dict, Any, Optional

from healthcare_intelligence.agents.base_agent import Agent
from healthcare_intelligence.data_sources.fhir import FHIRDataSource
from healthcare_intelligence.data_sources.iot import IOTDataSource

class FallPredictionAgent(Agent):
    """
    An agent designed to predict the risk of a patient falling.
    It uses a combination of clinical data and real-time IoT sensor data.
    """
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        
        # Initialize data sources
        self.fhir_data_source = FHIRDataSource(self.config['data_sources']['clinical'])
        self.iot_data_source = IOTDataSource(self.config['data_sources']['iot'])
        
        # Load the pre-trained machine learning model
        model_path = self.config['prediction_model']['path']
        self.model = joblib.load(model_path)
        
        self.risk_threshold = self.config.get('risk_threshold', 0.75)

    def get_data(self) -> Dict[str, Any]:
        """
        Acquires both clinical and IoT data for a specific patient.
        """
        try:
            # Assume a patient ID is configured or passed to the agent
            patient_id = self.config.get('patient_id')
            if not patient_id:
                raise ValueError("Patient ID not configured for agent.")
            
            clinical_data = self.fhir_data_source.get_patient_risk_data(patient_id)
            iot_data = self.iot_data_source.get_gait_data(patient_id)
            
            return {
                "patient_id": patient_id,
                "clinical_data": clinical_data,
                "iot_data": iot_data
            }
        except Exception as e:
            self.logger.error(f"Failed to acquire data for patient {patient_id}: {e}")
            raise

    def run_prediction(self, data: Dict[str, Any]) -> float:
        """
        Runs the fall risk prediction model on the combined data.
        
        The model is assumed to be a classifier that outputs a probability score.
        """
        patient_id = data.get("patient_id")
        
        # Pre-process data for the model (e.g., feature extraction, normalization)
        features = self._preprocess_data(data)
        
        try:
            # Predict the fall risk probability (a value between 0 and 1)
            risk_score = self.model.predict_proba([features])[0][1]
            self.logger.info(f"Patient {patient_id} fall risk score: {risk_score:.2f}")
            return risk_score
        except Exception as e:
            self.logger.error(f"Prediction failed for patient {patient_id}: {e}")
            raise

    def generate_output(self, prediction_result: float) -> Optional[Dict[str, Any]]:
        """
        Generates a high-value event if the fall risk score exceeds the threshold.
        """
        if prediction_result >= self.risk_threshold:
            self.logger.warning(f"High fall risk detected with score: {prediction_result:.2f}")
            return {
                "agent_id": self.agent_id,
                "event_type": "high_fall_risk",
                "severity": "high",
                "timestamp": "...",  # A real timestamp should be added here
                "details": {
                    "patient_id": self.config.get('patient_id'),
                    "risk_score": prediction_result
                }
            }
        self.logger.info(f"Fall risk is below threshold. No event generated.")
        return None

    def _preprocess_data(self, data: Dict[str, Any]) -> list:
        """
        Helper method to prepare data for the model.
        This would involve feature engineering based on the specific model requirements.
        """
        clinical = data.get('clinical_data', {})
        iot = data.get('iot_data', {})
        
        # Example feature engineering:
        # 1. Age from clinical data
        # 2. Medication count
        # 3. Average gait speed from IoT data
        # 4. Gait variability from IoT data
        
        # This is a placeholder; real implementation would be more complex
        age = clinical.get('age', 0)
        medication_count = len(clinical.get('medications', []))
        avg_gait_speed = iot.get('avg_gait_speed', 0)
        gait_variability = iot.get('gait_variability', 0)
        
        return [age, medication_count, avg_gait_speed, gait_variability]