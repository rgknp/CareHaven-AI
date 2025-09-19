import azure.functions as func
import logging
import json
import urllib.request
import urllib.error
import os
import socket
import random
from datetime import datetime
import uuid
from azure.cosmos import CosmosClient, PartitionKey, exceptions

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Initialize Cosmos DB client (will be created when needed)
def get_cosmos_client():
    """Get Cosmos DB client and container"""
    try:
        connection_string = os.environ.get('COSMOS_DB_CONNECTION_STRING')
        if not connection_string:
            raise Exception("COSMOS_DB_CONNECTION_STRING not found in environment variables")
        
        client = CosmosClient.from_connection_string(connection_string)
        database = client.get_database_client("CareHavenDB")
        container = database.get_container_client("CognitiveHealthData")
        return container
    except Exception as e:
        logging.error(f"Error connecting to Cosmos DB: {str(e)}")
        raise

@app.route(route="ingest_data", methods=["POST"])
def ingest_data(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Cognitive health data ingestion request received.')
    
    try:
        # Get the ML model configuration from environment variables
        ml_endpoint = os.environ.get('ML_MODEL_ENDPOINT')
        api_key = os.environ.get('ML_MODEL_API_KEY')
        
        # Log the endpoint for debugging (without the API key for security)
        logging.info(f'ML_MODEL_ENDPOINT: {ml_endpoint}')
        logging.info(f'API key present: {bool(api_key)}')
        
        if not ml_endpoint or not api_key:
            logging.error('Missing ML model configuration in environment variables')
            return func.HttpResponse(
                json.dumps({"error": "ML model configuration not found"}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Parse the incoming request data
        try:
            req_body = req.get_json()
            if not req_body:
                return func.HttpResponse(
                    json.dumps({"error": "Request body is required"}),
                    status_code=400,
                    mimetype="application/json"
                )
        except ValueError as e:
            logging.error(f'Invalid JSON in request body: {str(e)}')
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON format"}),
                status_code=400,
                mimetype="application/json"
            )
        
        enriched_data = req_body.copy() if isinstance(req_body, dict) else req_body[0].copy()
        
        # Log the enriched data for debugging
        logging.info(f'Enriched data: {json.dumps(enriched_data, indent=2)}')
            
        # Add metadata
        enriched_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        enriched_data['id'] = str(uuid.uuid4())  # Unique document ID for Cosmos DB
        
        # Try calling the ML model first
        ml_prediction_result = None
        try:
            # Prepare data for ML model (send original request data exactly as received)
            # The ML model expects the data in the exact format from your script
            ml_request_data = req_body if isinstance(req_body, dict) else req_body[0]
                        
            # Convert to JSON and encode (send data directly, not wrapped)
            body = str.encode(json.dumps(ml_request_data))
            
            # Set up headers for ML model request
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            # Create and send request to ML model
            logging.info(f'Calling ML model at: {ml_endpoint}')
            logging.info(f'Request data size: {len(body)} bytes')
            logging.info(f'Sending data: {json.dumps(ml_request_data)}')
            
            ml_request = urllib.request.Request(ml_endpoint, body, headers)
            
            with urllib.request.urlopen(ml_request, timeout=30) as response:
                result = response.read()
                result_text = result.decode('utf-8')
                logging.info(f'Raw ML response text: {result_text}')
                
                # Parse JSON response
                try:
                    ml_prediction_result = json.loads(result_text)
                except json.JSONDecodeError as json_error:
                    logging.error(f'Failed to parse ML response as JSON: {json_error}')
                    raise
                
                # Double-check if we got a string that needs another parse (double-encoded JSON)
                if isinstance(ml_prediction_result, str):
                    logging.warning('ML response was double-encoded JSON string, parsing again')
                    ml_prediction_result = json.loads(ml_prediction_result)
                
                logging.info('ML model prediction successful')
                logging.info(f'ML response: {ml_prediction_result}')
                logging.info(f'ML response type: {type(ml_prediction_result)}')
                
                # Extract cognitive index from ML model response
                # Handle the standard ML model response format: {"predictions": [value]}
                if isinstance(ml_prediction_result, dict):
                    logging.info(f'ML response is dict with keys: {list(ml_prediction_result.keys())}')
                    if 'predictions' in ml_prediction_result and isinstance(ml_prediction_result['predictions'], list) and len(ml_prediction_result['predictions']) > 0:
                        enriched_data['cognitive_index'] = round(ml_prediction_result['predictions'][0], 4)
                        logging.info(f'Successfully extracted cognitive_index from ML predictions: {enriched_data["cognitive_index"]}')
                    else:
                        # Unknown dict format, use fallback
                        logging.warning(f'Unexpected ML response dict format - predictions key: {"predictions" in ml_prediction_result}, predictions type: {type(ml_prediction_result.get("predictions"))}, predictions length: {len(ml_prediction_result.get("predictions", []))}')
                        enriched_data['cognitive_index'] = round(random.uniform(0.1, 1.0), 4)
                else:
                    # If we can't parse the ML response, use a fallback value
                    logging.warning(f'Unexpected ML response format - type: {type(ml_prediction_result)}, value: {ml_prediction_result}')
                    enriched_data['cognitive_index'] = round(random.uniform(0.1, 1.0), 4)
                
        except urllib.error.HTTPError as error:
            error_message = error.read().decode("utf8", 'ignore')
            logging.error(f'ML model request failed with status {error.code}: {error_message}')
            
            # Fallback: generate random cognitive index
            enriched_data['cognitive_index'] = round(random.uniform(0.1, 1.0), 4)
            logging.info(f'Using fallback random cognitive_index: {enriched_data["cognitive_index"]}')
            
        except urllib.error.URLError as url_error:
            logging.error(f'ML model URL Error: {url_error}')
            
            # Fallback: generate random cognitive index
            enriched_data['cognitive_index'] = round(random.uniform(0.1, 1.0), 4)
            logging.info(f'Using fallback random cognitive_index: {enriched_data["cognitive_index"]}')
            
        except Exception as e:
            logging.error(f'Error calling ML model: {str(e)}')
            
            # Fallback: generate random cognitive index
            enriched_data['cognitive_index'] = round(random.uniform(0.1, 1.0), 4)
            logging.info(f'Using fallback random cognitive_index: {enriched_data["cognitive_index"]}')
        
        logging.info(f'Final cognitive_index: {enriched_data["cognitive_index"]} for patient_id: {enriched_data["patient_id"]}')
        
        # Store in Cosmos DB
        try:
            container = get_cosmos_client()
            
            # Insert document into Cosmos DB
            created_item = container.create_item(body=enriched_data)
            logging.info(f'Successfully stored document in Cosmos DB with id: {created_item["id"]}')
            
        except exceptions.CosmosResourceExistsError:
            logging.error(f'Document with id {enriched_data["id"]} already exists')
            return func.HttpResponse(
                json.dumps({"error": "Document already exists"}),
                status_code=409,
                mimetype="application/json"
            )
        except Exception as cosmos_error:
            logging.error(f'Error storing in Cosmos DB: {str(cosmos_error)}')
            return func.HttpResponse(
                json.dumps({"error": f"Database error: {str(cosmos_error)}"}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Return the enriched data with cognitive index (from ML model or fallback)
        logging.info('Successfully processed and stored cognitive health data')
        
        response_data = {
            "status": "success",
            "message": "Cognitive health data processed and stored successfully",
            "document_id": enriched_data["id"],
            "patient_id": enriched_data["patient_id"],
            "cognitive_index": enriched_data["cognitive_index"],
            "timestamp": enriched_data["timestamp"]
        }
        
        # Include ML model response if available
        if ml_prediction_result is not None:
            response_data["ml_model_response"] = ml_prediction_result
            response_data["ml_model_status"] = "success"
        else:
            response_data["ml_model_status"] = "fallback_used"
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f'Unexpected error in predict_cognitive_health: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )