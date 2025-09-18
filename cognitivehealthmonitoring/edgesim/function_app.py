import logging
import azure.functions as func
import os
import json
import random
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from azure.cosmos import CosmosClient, exceptions

app = func.FunctionApp()

# ------------------------------ Helper Functions ------------------------------ #

def get_cosmos_client():
    """Initialize Cosmos DB client from environment variables."""
    connection_string = os.environ.get('COSMOS_DB_CONNECTION_STRING')
    if not connection_string:
        raise ValueError("COSMOS_DB_CONNECTION_STRING environment variable not found")
    return CosmosClient.from_connection_string(connection_string)

def get_random_patient(cosmos_client) -> Optional[Dict[str, Any]]:
    """Get a random patient from the PatientProfiles container."""
    try:
        database = cosmos_client.get_database_client("CareHavenDB")
        container = database.get_container_client("PatientProfiles")
        
        # Get count of patients first
        count_query = "SELECT VALUE COUNT(1) FROM c"
        count_result = list(container.query_items(query=count_query, enable_cross_partition_query=True))
        total_patients = count_result[0] if count_result else 0
        
        if total_patients == 0:
            logging.warning("No patients found in PatientProfiles container")
            return None
        
        # Get random offset
        random_offset = random.randint(0, total_patients - 1)
        
        # Query with offset to get random patient
        query = f"SELECT * FROM c OFFSET {random_offset} LIMIT 1"
        patients = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if patients:
            patient = patients[0]
            logging.info(f"Selected random patient: {patient['patient_id']} - {patient['name']}")
            return patient
        else:
            logging.warning("No patient found with random offset")
            return None
            
    except Exception as e:
        logging.error(f"Failed to get random patient: {str(e)}")
        return None

def extract_baselines(patient: Dict[str, Any]) -> Tuple[float, int, int, int]:
    """Extract baseline cognitive metrics from patient profile."""
    cb = patient.get('cognitive_baseline', {}) or {}
    mmse = int(cb.get('mmse', 26))
    moca = int(cb.get('moca', 24))
    depression = int(cb.get('depression_score', 6))
    
    # Calculate cognitive factor (0.3 to 1.0)
    cognitive_factor = max(0.3, min(1.0, (mmse + moca) / 60))
    
    return cognitive_factor, mmse, moca, depression

def generate_cognitive_session_data(patient: Dict[str, Any]) -> Dict[str, Any]:
    """Generate realistic cognitive session data based on patient profile."""
    cf, mmse, moca, depression = extract_baselines(patient)
    
    # Depression penalty (higher depression -> subtle performance penalties)
    dep_penalty = min(0.15, depression * 0.005)
    
    # Generate attention metrics
    attention_span_base = random.normalvariate(4.0 + cf * 3.0 - dep_penalty * 1.5, 0.55)
    digit_span = max(2, min(round(attention_span_base), 8))
    attention_errors = max(0, int(random.normalvariate((6 - digit_span) * 0.6, 0.7)))
    attention_latency = max(0.6, random.normalvariate(1.65 - cf * 0.85 + dep_penalty * 0.4, 0.14))
    
    # Generate executive function metrics
    exec_fluency_base = random.normalvariate(12 + cf * 14 - dep_penalty * 6, 2.8)
    verbal_fluency = max(3, int(round(exec_fluency_base)))
    exec_artic_base = random.normalvariate(1.38 + cf * 0.92 - dep_penalty * 0.25, 0.18)
    articulation_rate = max(0.6, round(exec_artic_base, 2))
    exec_pause_base = random.normalvariate(1420 - cf * 620 + dep_penalty * 220, 170)
    avg_pause = int(max(300, exec_pause_base))
    
    # Generate memory metrics
    memory_immediate_base = random.normalvariate(2.9 + cf * 2.0 - dep_penalty * 1.2, 0.48)
    immediate_recall = max(0, min(5, int(round(memory_immediate_base))))
    memory_delayed_base = memory_immediate_base - random.normalvariate(0.9 - cf * 0.7 + dep_penalty * 0.3, 0.37)
    delayed_recall = max(0, min(immediate_recall, int(round(memory_delayed_base))))
    
    # Generate intrusion errors
    intrusions_prob = 0.10
    intrusions_prob += max(0, (immediate_recall - delayed_recall)) * 0.05
    intrusions_prob += max(0, 0.55 - cf) * 0.16
    intrusions_prob += (depression / 30) * 0.12
    intrusions_prob = min(0.40, intrusions_prob)
    intrusion_errors = 1 if random.random() < max(0.01, intrusions_prob) else 0
    
    # Generate orientation metrics
    date_correct = random.random() < (0.85 + (cf - 0.6) * 0.25)
    city_correct = random.random() < (0.8 + (cf - 0.6) * 0.30)
    orientation_score = (int(date_correct) + int(city_correct)) * 4  # Convert to 0-8 scale
    
    # Generate processing speed metrics
    reaction_time_base = random.normalvariate(905 - cf * 355 + dep_penalty * 140, 58)
    avg_reaction_time = int(max(350, reaction_time_base))
    missed_trials = max(0, int(random.normalvariate((avg_reaction_time - 600) / 160, 0.6))) if avg_reaction_time > 600 else 0
    
    # Generate mood/behavior metrics
    dep_adj = (depression / 30)
    sentiment_base = random.normalvariate(0.47 + cf * 0.25 - dep_penalty * 1.1, 0.09)
    sentiment = max(0.0, min(1.0, sentiment_base))
    mood_score = max(1, min(5, int(round(3 + (sentiment - 0.5) * 4))))  # Convert to 1-5 scale
    
    # Get device ID from patient profile
    device_ids = patient.get('device_ids', {})
    device_id = device_ids.get('speech') or device_ids.get('wearable') or f"DEV-{patient['patient_id'][:8]}"
    
    return {
        "patient_id": patient['patient_id'],
        "device_id": device_id,
        "session_date": datetime.utcnow().isoformat() + "Z",
        "attention": {
            "digit_span_max": digit_span,
            "errors": attention_errors,
            "latency_sec": round(attention_latency, 2)
        },
        "executive_function": {
            "verbal_fluency_words": verbal_fluency,
            "articulation_rate_wps": articulation_rate,
            "avg_pause_ms": avg_pause
        },
        "memory": {
            "immediate_recall": immediate_recall,
            "delayed_recall": delayed_recall,
            "intrusion_errors": intrusion_errors
        },
        "orientation": {
            "date_correct": date_correct,
            "city_correct": city_correct,
            "orientation_correct": orientation_score
        },
        "processing_speed": {
            "avg_reaction_time_ms": avg_reaction_time,
            "missed_trials": missed_trials
        },
        "mood_behavior": {
            "sentiment_score": round(sentiment, 2),
            "narrative_coherence": round(max(0.0, min(1.0, random.normalvariate(0.5 + cf * 0.34 - dep_adj * 0.8, 0.09))), 2),
            "mood_score": mood_score
        }
    }

def send_to_edge_connector(data: Dict[str, Any]) -> bool:
    """Send generated data to the edge connector function."""
    try:
        edge_connector_url = os.environ.get('EDGE_CONNECTOR_URL')
        function_code = os.environ.get('EDGE_CONNECTOR_FUNCTION_CODE')
        
        if not edge_connector_url or not function_code:
            logging.error("EDGE_CONNECTOR_URL or EDGE_CONNECTOR_FUNCTION_CODE environment variables not found")
            return False
        
        # Clean the URL and function code (remove any extra quotes)
        edge_connector_url = edge_connector_url.strip().strip('"').strip("'")
        function_code = function_code.strip().strip('"').strip("'")
        
        # Construct the full URL with function code
        url = f"{edge_connector_url}?code={function_code}"
                
        # Send POST request with JSON data
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            logging.info(f"Successfully sent data to edge connector for patient {data['patient_id']}")
            return True
        else:
            logging.error(f"Edge connector returned status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logging.error("Timeout while calling edge connector")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling edge connector: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error sending to edge connector: {str(e)}")
        return False

# ------------------------------ Azure Function ------------------------------ #

@app.timer_trigger(schedule="*/20 * * * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def datasim(myTimer: func.TimerRequest) -> None:
    """Timer-triggered function that generates and sends cognitive data every 5 minutes."""
    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Starting cognitive data simulation...')
    
    try:
        # Initialize Cosmos DB client
        cosmos_client = get_cosmos_client()
        
        # Get a random patient
        patient = get_random_patient(cosmos_client)
        if not patient:
            logging.error("Could not select a random patient")
            return
        
        # Generate cognitive session data
        session_data = generate_cognitive_session_data(patient)
        
        # Send data to edge connector
        success = send_to_edge_connector(session_data)
        
        if success:
            logging.info(f"✅ Successfully processed patient {session_data['patient_id']}")
        else:
            logging.error(f"❌ Failed to send data for patient {session_data['patient_id']}")
            
    except Exception as e:
        logging.error(f"Error in datasim function: {str(e)}")
        raise