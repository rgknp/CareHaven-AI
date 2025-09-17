import os
import json
import google.generativeai as genai
from fastapi import HTTPException, status, APIRouter, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any

# --- Pydantic Models ---
class A2ATask(BaseModel):
    id: str
    skill_name: str
    parameters: Dict[str, Any]

class A2AMessage(BaseModel):
    task: A2ATask

class ToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

# --- Environment Setup ---
# Set your Gemini API key from an environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

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

# --- Agent's Internal MCP Tool ---
def get_trip_activities(destination: str) -> str:
    # This is a mock MCP tool. In a real-world scenario, this would be
    # a separate service that the model calls.
    if destination.lower() == "new york":
        return "Visit Times Square, see a Broadway show, walk in Central Park."
    else:
        return "No activities found for this destination."

# --- Gemini Model with Tool Calling ---
async def get_gemini_response(prompt: str, tools: list) -> str:
    model = genai.GenerativeModel("gemini-2.5-pro", tools=tools)
    response = model.generate_content(prompt)
    
    # Handle tool calls
    if response.candidates[0].content.parts[0].function_call:
        tool_call = response.candidates[0].content.parts[0].function_call
        if tool_call.name == "get_trip_activities":
            result = get_trip_activities(**tool_call.args)
            return result
    
    return response.text

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
    
    # Check if the requested skill exists in the agent card
    if skill_name == "plan_trip":
        destination = parameters.get("destination")
        start_date = parameters.get("start_date")
        end_date = parameters.get("end_date")
        
        # Here, the agent receives an A2A request and decides how to fulfill it.
        # It uses Gemini's intelligence to do so.
        
        # Step 1: Call a remote A2A agent for weather (simulated)
        # In a real app, this would be an HTTP request to a remote A2A agent's endpoint
        weather_info = "The weather for your trip is expected to be sunny." # Simulated call
        
        # Step 2: Use an MCP-like tool for local data
        activities = get_trip_activities(destination)
        
        # Step 3: Use Gemini to synthesize the final response
        prompt = f"""
        A user wants to plan a trip to {destination} from {start_date} to {end_date}.
        The weather information is: {weather_info}
        The suggested activities are: {activities}
        
        Synthesize a final trip plan based on this information.
        """
        
        final_plan = await get_gemini_response(prompt, []) # Pass no tools here, just for synthesis
        
        return {
            "task_id": message.task.id,
            "status": "completed",
            "result": {
                "trip_plan": final_plan
            }
        }
    else:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found.")