import os
import json
import random
import requests
from openai import AzureOpenAI
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

# --- Pydantic Models ---
class A2ATask(BaseModel):
    id: str
    skill_name: str
    parameters: Dict[str, Any]

class A2AMessage(BaseModel):
    task: A2ATask

# --- Environment Setup ---
# Set your Azure OpenAI credentials from environment variables
try:
    AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
    AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
    AZURE_OPENAI_DEPLOYMENT_NAME = os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]
    AZURE_OPENAI_API_VERSION = os.environ["AZURE_OPENAI_API_VERSION"]
except KeyError as e:
    raise ValueError(f"Missing required environment variable: {e}")

router = APIRouter()

# simple agent api key handler
API_KEYS = [os.getenv("AGENT_API_KEY"),]
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key in API_KEYS:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key"
    )

# --- Agent's Internal Fall Prediction Logic ---
def get_fall_risk_prediction(patient_id: str, age: int, mobility_score: int, medication_list: Optional[List[str]] = None) -> Dict[str, Any]:
    # This is the "black box" prediction logic.
    # It simply generates a random boolean with a 25% chance of being True.
    is_high_risk = random.random() < 0.25
    
    status = "completed"
    if is_high_risk:
        notification_message = f"HIGH RISK ALERT: Patient {patient_id} ({age} years old) has been identified as high risk for a fall. Consider immediate intervention."
        risk_level = "High"
    else:
        notification_message = f"Patient {patient_id} ({age} years old) is currently low risk for a fall. Continue to monitor."
        risk_level = "Low"

    return {
        "prediction_status": risk_level,
        "notification_message": notification_message
    }

# --- Azure OpenAI Client and Tool Call Logic ---
def get_azure_openai_client():
    return AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION
    )

# --- A2A Server Endpoints ---

# unprotected for discovery
@router.get("/.well-known/agent.json")
async def get_agent_card(request: Request):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "agent_card.json")
    with open(file_path, "r") as f:
        agent_card = json.load(f)
    # Get the base URL dynamically from the request headers
    base_url = str(request.base_url).strip('/')
    # Replace the placeholder with the dynamic URL
    agent_card["url"] = f"{base_url}"
    return JSONResponse(content=agent_card)


@router.post("/tasks/send", status_code=status.HTTP_200_OK, dependencies=[Depends(get_api_key)])
async def handle_a2a_task(message: A2AMessage):
    skill_name = message.task.skill_name
    parameters = message.task.parameters
    
    # Check if the requested skill exists
    if skill_name == "predict_fall_risk":
        # Extract the parameters from the message
        patient_id = parameters.get("patient_id")
        age = parameters.get("age")
        mobility_score = parameters.get("mobility_score")
        medication_list = parameters.get("medication_list", [])
        
        # Call the internal fall prediction logic
        prediction_result = get_fall_risk_prediction(patient_id, age, mobility_score, medication_list)
        
        return {
            "task_id": message.task.id,
            "status": "completed",
            "result": prediction_result
        }
    else:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found.")