#!/usr/bin/env python3
"""
Script to push patient profile data to Cosmos DB.
This script creates a new container 'PatientProfiles' and uploads all patient data from patient_profiles.json.
The container is partitioned by patient_id for optimal querying.
"""

import json
import os
import sys
from typing import Dict, List, Any
from azure.cosmos import CosmosClient, PartitionKey, exceptions
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PatientProfileUploader:
    """Handles uploading patient profile data to Cosmos DB."""
    
    def __init__(self, connection_string: str, database_name: str = "CareHavenDB"):
        """
        Initialize the uploader with Cosmos DB connection details.
        
        Args:
            connection_string: Cosmos DB connection string
            database_name: Name of the database (default: CareHavenDB)
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.database = None
        self.container = None
        
    def connect(self):
        """Connect to Cosmos DB and initialize database client."""
        try:
            self.client = CosmosClient.from_connection_string(self.connection_string)
            self.database = self.client.get_database_client(self.database_name)
            logger.info(f"Connected to Cosmos DB database: {self.database_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Cosmos DB: {str(e)}")
            raise
    
    def create_container(self, container_name: str = "PatientProfiles"):
        """
        Create the PatientProfiles container if it doesn't exist.
        
        Args:
            container_name: Name of the container to create
        """
        try:
            # Check if container already exists
            try:
                self.container = self.database.get_container_client(container_name)
                logger.info(f"Container '{container_name}' already exists")
                return
            except exceptions.CosmosResourceNotFoundError:
                pass
            
            # Create container with patient_id as partition key
            container = self.database.create_container(
                id=container_name,
                partition_key=PartitionKey(path="/patient_id"),
                offer_throughput=400  # Start with minimum throughput
            )
            self.container = container
            logger.info(f"Created container '{container_name}' with partition key '/patient_id'")
            
        except Exception as e:
            logger.error(f"Failed to create container '{container_name}': {str(e)}")
            raise
    
    def load_patient_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load patient profile data from JSON file.
        
        Args:
            file_path: Path to the patient_profiles.json file
            
        Returns:
            List of patient profile dictionaries
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            logger.info(f"Loaded {len(data)} patient profiles from {file_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load patient data from {file_path}: {str(e)}")
            raise
    
    def upload_patient_profiles(self, patient_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Upload patient profiles to Cosmos DB.
        
        Args:
            patient_data: List of patient profile dictionaries
            
        Returns:
            Dictionary with upload statistics
        """
        stats = {
            'total': len(patient_data),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, patient in enumerate(patient_data):
            try:
                # Add metadata
                patient['id'] = patient['patient_id']  # Cosmos DB requires 'id' field
                patient['document_type'] = 'patient_profile'
                patient['created_at'] = '2025-09-18T00:00:00Z'  # Add timestamp
                
                # Upload to Cosmos DB
                self.container.create_item(body=patient)
                stats['successful'] += 1
                
                if (i + 1) % 100 == 0:
                    logger.info(f"Uploaded {i + 1}/{stats['total']} patient profiles")
                    
            except exceptions.CosmosResourceExistsError:
                logger.warning(f"Patient {patient['patient_id']} already exists, skipping")
                stats['successful'] += 1  # Count as successful since data exists
                
            except Exception as e:
                error_msg = f"Failed to upload patient {patient.get('patient_id', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                stats['failed'] += 1
                stats['errors'].append(error_msg)
        
        return stats
    
    def verify_upload(self, sample_patient_id: str = None) -> bool:
        """
        Verify that data was uploaded successfully by querying for a patient.
        
        Args:
            sample_patient_id: Patient ID to verify (uses first patient if None)
            
        Returns:
            True if verification successful, False otherwise
        """
        try:
            if not sample_patient_id:
                # Get first patient from the container
                query = "SELECT TOP 1 c.patient_id FROM c"
                items = list(self.container.query_items(query=query, enable_cross_partition_query=True))
                if not items:
                    logger.error("No patients found in container")
                    return False
                sample_patient_id = items[0]['patient_id']
            
            # Query for the specific patient
            query = "SELECT * FROM c WHERE c.patient_id = @patient_id"
            parameters = [{"name": "@patient_id", "value": sample_patient_id}]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=sample_patient_id
            ))
            
            if items:
                logger.info(f"Verification successful: Found patient {sample_patient_id}")
                logger.info(f"Patient data: {items[0]['name']} (DOB: {items[0]['dob']})")
                return True
            else:
                logger.error(f"Verification failed: Patient {sample_patient_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Verification failed with error: {str(e)}")
            return False

def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        logger.info("Loaded environment variables from .env file")

def main():
    """Main function to execute the upload process."""
    
    # Load environment variables from .env file
    load_env_file()
    
    # Get connection string from environment variable
    connection_string = os.environ.get('COSMOS_DB_CONNECTION_STRING')
    if not connection_string:
        logger.error("COSMOS_DB_CONNECTION_STRING environment variable not found")
        logger.info("Please either:")
        logger.info("1. Set the environment variable: $env:COSMOS_DB_CONNECTION_STRING = 'your_connection_string'")
        logger.info("2. Create a .env file in this directory with: COSMOS_DB_CONNECTION_STRING=your_connection_string")
        sys.exit(1)
    
    # Determine the path to patient_profiles.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, '..', 'dataproducers', 'data', 'patient_profiles.json')
    
    if not os.path.exists(data_file):
        logger.error(f"Patient profiles file not found: {data_file}")
        sys.exit(1)
    
    try:
        # Initialize uploader
        uploader = PatientProfileUploader(connection_string)
        uploader.connect()
        
        # Create container
        uploader.create_container("PatientProfiles")
        
        # Load patient data
        patient_data = uploader.load_patient_data(data_file)
        
        # Upload data
        logger.info("Starting patient profile upload...")
        stats = uploader.upload_patient_profiles(patient_data)
        
        # Print results
        logger.info("Upload completed!")
        logger.info(f"Total patients: {stats['total']}")
        logger.info(f"Successfully uploaded: {stats['successful']}")
        logger.info(f"Failed uploads: {stats['failed']}")
        
        if stats['errors']:
            logger.warning("Errors encountered:")
            for error in stats['errors'][:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
            if len(stats['errors']) > 5:
                logger.warning(f"  ... and {len(stats['errors']) - 5} more errors")
        
        # Verify upload
        logger.info("Verifying upload...")
        if uploader.verify_upload():
            logger.info("✅ Upload verification successful!")
        else:
            logger.error("❌ Upload verification failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Script failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
