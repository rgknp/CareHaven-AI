import logging
import os
import json
import random
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize random seed to ensure different values each run
random.seed()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_cosmos_client():
    """Initialize Cosmos DB client from environment variables."""
    connection_string = os.environ.get('COSMOS_DB_CONNECTION_STRING')
    if not connection_string:
        raise ValueError("COSMOS_DB_CONNECTION_STRING environment variable not found")
    return CosmosClient.from_connection_string(connection_string)

def get_all_patients(cosmos_client) -> List[Dict[str, Any]]:
    """Get all patients from the PatientProfiles container."""
    try:
        database = cosmos_client.get_database_client("CareHavenDB")
        container = database.get_container_client("PatientProfiles")
        
        # Query all patients
        query = "SELECT * FROM c"
        patients = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        logging.info(f"Found {len(patients)} patients in PatientProfiles container")
        return patients
        
    except Exception as e:
        logging.error(f"Failed to get patients: {str(e)}")
        return []

def generate_random_dates_past_year(num_dates: int = 5) -> List[datetime]:
    """Generate random well-spaced dates over the past year."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365)
    
    # Generate random dates and sort them
    random_dates = []
    for _ in range(num_dates):
        # Generate random number of days from start_date
        random_days = random.randint(0, 365)
        random_date = start_date + timedelta(days=random_days)
        
        # Add some random hours/minutes to make it more realistic
        random_hours = random.randint(8, 18)  # Business hours
        random_minutes = random.randint(0, 59)
        
        random_date = random_date.replace(hour=random_hours, minute=random_minutes, second=0, microsecond=0)
        random_dates.append(random_date)
    
    # Sort dates chronologically
    random_dates.sort()
    
    # Ensure dates are well-spaced (minimum 30 days apart for fewer records)
    well_spaced_dates = []
    last_date = None
    
    for date in random_dates:
        if last_date is None or (date - last_date).days >= 30:
            well_spaced_dates.append(date)
            last_date = date
    
    # If we don't have enough well-spaced dates, fill the gap
    while len(well_spaced_dates) < num_dates:
        # Generate a new date that's at least 7 days from existing dates
        attempts = 0
        while attempts < 100:  # Prevent infinite loop
            random_days = random.randint(0, 365)
            new_date = start_date + timedelta(days=random_days)
            new_date = new_date.replace(hour=random.randint(8, 18), minute=random.randint(0, 59), second=0, microsecond=0)
            
            # Check if this date is well-spaced from existing dates (30 days)
            is_well_spaced = True
            for existing_date in well_spaced_dates:
                if abs((new_date - existing_date).days) < 30:
                    is_well_spaced = False
                    break
            
            if is_well_spaced:
                well_spaced_dates.append(new_date)
                break
            
            attempts += 1
        
        if attempts >= 100:
            # If we can't find well-spaced dates, just add remaining dates with minimum spacing
            remaining_needed = num_dates - len(well_spaced_dates)
            for i in range(remaining_needed):
                last_date = well_spaced_dates[-1] if well_spaced_dates else start_date
                new_date = last_date + timedelta(days=30 + i * 30)
                if new_date <= end_date:
                    well_spaced_dates.append(new_date)
            break
    
    # Sort final dates and return only the requested number
    well_spaced_dates.sort()
    return well_spaced_dates[:num_dates]

def extract_baselines(patient: Dict[str, Any]) -> Tuple[float, int, int, int]:
    """Extract baseline cognitive metrics from patient profile."""
    cb = patient.get('cognitive_baseline', {}) or {}
    mmse = int(cb.get('mmse', 26))
    moca = int(cb.get('moca', 24))
    depression = int(cb.get('depression_score', 6))
    
    # Calculate cognitive factor (0.3 to 1.0)
    cognitive_factor = max(0.3, min(1.0, (mmse + moca) / 60))
    
    return cognitive_factor, mmse, moca, depression

def generate_cognitive_session_data(patient: Dict[str, Any], session_date: datetime) -> Dict[str, Any]:
    """Generate realistic cognitive session data based on patient profile for a specific date."""
    cf, mmse, moca, depression = extract_baselines(patient)
    
    # Add debugging
    logging.info(f"🧠 Patient {patient['patient_id'][:8]}: cf={cf:.3f}, mmse={mmse}, moca={moca}, depression={depression}")
    
    # Depression penalty (higher depression -> subtle performance penalties)
    dep_penalty = min(0.15, depression * 0.005)
    
    # Generate attention metrics
    attention_span_base = random.normalvariate(4.0 + cf * 3.0 - dep_penalty * 1.5, 0.55)
    digit_span = max(2, min(round(attention_span_base), 8))
    attention_errors = max(0, int(random.normalvariate((6 - digit_span) * 0.6, 0.7)))
    attention_latency = max(0.6, random.normalvariate(1.65 - cf * 0.85 + dep_penalty * 0.4, 0.14))
    
    logging.info(f"📊 Generated: digit_span={digit_span}, attention_latency={attention_latency:.2f}")
    
    # Generate executive function metrics
    exec_fluency_base = random.normalvariate(12 + cf * 14 - dep_penalty * 6, 2.8)
    verbal_fluency = max(3, int(round(exec_fluency_base)))
    exec_artic_base = random.normalvariate(1.38 + cf * 0.92 - dep_penalty * 0.25, 0.18)
    articulation_rate = max(0.6, round(exec_artic_base, 2))
    exec_pause_base = random.normalvariate(1420 - cf * 620 + dep_penalty * 220, 170)
    avg_pause = int(max(300, exec_pause_base))
    
    logging.info(f"🗣️  Generated: verbal_fluency={verbal_fluency}, articulation_rate={articulation_rate}")
    
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
    
    logging.info(f"⚡ Generated: avg_reaction_time={avg_reaction_time}")
    
    # Generate mood/behavior metrics
    dep_adj = (depression / 30)
    sentiment_base = random.normalvariate(0.47 + cf * 0.25 - dep_penalty * 1.1, 0.09)
    sentiment = max(0.0, min(1.0, sentiment_base))
    mood_score = max(1, min(5, int(round(3 + (sentiment - 0.5) * 4))))  # Convert to 1-5 scale
    
    logging.info(f"😊 Generated: sentiment={sentiment:.2f}, mood_score={mood_score}")
    
    # Get device ID from patient profile
    device_ids = patient.get('device_ids', {})
    device_id = device_ids.get('speech') or device_ids.get('wearable') or f"DEV-{patient['patient_id'][:8]}"
    
    return {
        "patient_id": patient['patient_id'],
        "device_id": device_id,
        "session_date": session_date.isoformat() + "Z",
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
        
        response = requests.post(url, json=data, headers=headers, timeout=10)  # Reduced timeout for faster processing
        
        if response.status_code == 200:
            logging.info(f"✅ Successfully sent data to edge connector for patient {data['patient_id']} on {data['session_date']}")
            return True
        else:
            logging.error(f"❌ Edge connector returned status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logging.error("⏰ Timeout while calling edge connector")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"🌐 Error calling edge connector: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"💥 Unexpected error sending to edge connector: {str(e)}")
        return False

def process_patient_historical_data(patient: Dict[str, Any], records_per_patient: int = 5, delay_between_records: float = 0.05) -> int:
    """Generate and send historical data for a single patient."""
    patient_id = patient['patient_id']
    patient_name = patient.get('name', 'Unknown')
    
    logging.info(f"📊 Processing historical data for patient: {patient_name} ({patient_id})")
    
    # Generate random dates for this patient
    session_dates = generate_random_dates_past_year(records_per_patient)
    
    successful_records = 0
    
    for i, session_date in enumerate(session_dates, 1):
        try:
            # Generate cognitive session data for this date
            session_data = generate_cognitive_session_data(patient, session_date)
            
            # Send to edge connector
            success = send_to_edge_connector(session_data)
            
            if success:
                successful_records += 1
                # Only log first and last record for each patient to reduce verbosity
                if i == 1 or i == len(session_dates):
                    logging.info(f"   Record {i}/{records_per_patient} ✅ - {session_date.strftime('%Y-%m-%d')}")
            else:
                logging.error(f"   Record {i}/{records_per_patient} ❌ - {session_date.strftime('%Y-%m-%d')}")
            
            # Apply minimal delay between records (only if delay > 0)
            if i < len(session_dates) and delay_between_records > 0:  # Don't delay after the last record
                time.sleep(delay_between_records)
                
        except Exception as e:
            logging.error(f"💥 Error processing record {i} for patient {patient_id}: {str(e)}")
    
    logging.info(f"📈 Patient {patient_name}: {successful_records}/{records_per_patient} records sent successfully")
    return successful_records

def main():
    """Main function to process historical data for all patients."""
    logging.info("🚀 Starting historical cognitive health data generation...")
    
    # Configuration - Optimized for 1000 patients
    RECORDS_PER_PATIENT = 5  # Reduced from 10 for large patient base
    DELAY_BETWEEN_RECORDS = 0.05  # seconds (50ms - even faster!)
    DELAY_BETWEEN_PATIENTS = 0.2  # seconds (200ms - even faster!)
    
    try:
        # Initialize Cosmos DB client
        logging.info("🔗 Connecting to Cosmos DB...")
        cosmos_client = get_cosmos_client()
        
        # Get all patients
        logging.info("👥 Fetching all patients from PatientProfiles...")
        patients = get_all_patients(cosmos_client)
        
        if not patients:
            logging.error("❌ No patients found. Exiting.")
            return
        
        logging.info(f"📋 Found {len(patients)} patients. Will generate {RECORDS_PER_PATIENT} records per patient.")
        logging.info(f"⏱️  Rate limiting: {DELAY_BETWEEN_RECORDS}s between records, {DELAY_BETWEEN_PATIENTS}s between patients")
        
        # Estimate total time
        estimated_time_per_patient = (RECORDS_PER_PATIENT * DELAY_BETWEEN_RECORDS) + DELAY_BETWEEN_PATIENTS + 0.5  # +0.5 for processing overhead
        estimated_total_minutes = (len(patients) * estimated_time_per_patient) / 60
        logging.info(f"⏰ Estimated completion time: {estimated_total_minutes:.1f} minutes")
        
        total_records_sent = 0
        total_records_expected = len(patients) * RECORDS_PER_PATIENT
        
        # Process each patient
        start_time = time.time()
        for patient_index, patient in enumerate(patients, 1):
            try:
                # Calculate and show progress every 50 patients or first/last
                progress_pct = (patient_index - 1) / len(patients) * 100
                if patient_index == 1 or patient_index % 50 == 0 or patient_index == len(patients):
                    logging.info(f"\n👤 [{progress_pct:.1f}%] Processing patient {patient_index}/{len(patients)}")
                elif patient_index % 10 == 0:  # Brief progress every 10 patients
                    logging.info(f"📊 Progress: {patient_index}/{len(patients)} patients ({progress_pct:.1f}%)")
                
                # Process this patient's historical data
                records_sent = process_patient_historical_data(
                    patient, 
                    RECORDS_PER_PATIENT, 
                    DELAY_BETWEEN_RECORDS
                )
                
                total_records_sent += records_sent
                
                # Apply minimal delay between patients (except for the last patient)
                if patient_index < len(patients) and DELAY_BETWEEN_PATIENTS > 0:
                    time.sleep(DELAY_BETWEEN_PATIENTS)
                
            except Exception as e:
                logging.error(f"💥 Error processing patient {patient_index}: {str(e)}")
                continue
        
        # Final summary with timing
        total_time = time.time() - start_time
        success_rate = (total_records_sent / total_records_expected) * 100 if total_records_expected > 0 else 0
        records_per_minute = (total_records_sent / total_time) * 60 if total_time > 0 else 0
        
        logging.info(f"\n🎉 COMPLETED!")
        logging.info(f"📊 Total Records Sent: {total_records_sent}/{total_records_expected} ({success_rate:.1f}%)")
        logging.info(f"👥 Patients Processed: {len(patients)}")
        logging.info(f"⏱️  Total Time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        logging.info(f"🚀 Processing Rate: {records_per_minute:.1f} records/min")
        logging.info(f"📅 Date Range: Past 365 days (30+ day intervals)")
        
    except Exception as e:
        logging.error(f"💥 Fatal error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()
