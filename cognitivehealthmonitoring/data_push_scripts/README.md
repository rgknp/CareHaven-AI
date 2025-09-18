# Data Push Scripts

This directory contains scripts for pushing data to Cosmos DB containers.

## Patient Profiles Upload Script

The `push_patient_profiles.py` script uploads patient profile data from `patient_profiles.json` to a new Cosmos DB container called "PatientProfiles".

### Prerequisites

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up your Cosmos DB connection string using **either** method:

   **Option A: Using .env file (Recommended)**
   ```bash
   # Your .env file should contain:
   COSMOS_DB_CONNECTION_STRING=AccountEndpoint=https://your-account.documents.azure.com:443/;AccountKey=your-key-here;
   ```

   **Option B: Using environment variable**
   ```bash
   # Windows PowerShell
   $env:COSMOS_DB_CONNECTION_STRING = "your_cosmos_db_connection_string_here"
   
   # Windows Command Prompt
   set COSMOS_DB_CONNECTION_STRING=your_cosmos_db_connection_string_here
   
   # Linux/Mac
   export COSMOS_DB_CONNECTION_STRING="your_cosmos_db_connection_string_here"
   ```

### Usage

Run the script from this directory:

```bash
python push_patient_profiles.py
```

### What the script does

1. **Creates Container**: Creates a new Cosmos DB container called "PatientProfiles" if it doesn't exist
2. **Partition Key**: Uses `patient_id` as the partition key for optimal querying
3. **Data Upload**: Uploads all patient profiles from `../dataproducers/data/patient_profiles.json`
4. **Verification**: Verifies the upload by querying for a sample patient
5. **Logging**: Provides detailed logging of the upload process

### Container Structure

- **Database**: CareHavenDB
- **Container**: PatientProfiles
- **Partition Key**: `/patient_id`
- **Throughput**: 400 RU/s (minimum)

### Querying Patient Data

Once uploaded, you can query patient data by patient_id efficiently:

```sql
-- Get a specific patient
SELECT * FROM c WHERE c.patient_id = "290d3a50-82cb-452b-bedb-b7b5315a1a8a"

-- Get all patients with specific comorbidities
SELECT c.patient_id, c.name, c.comorbidities 
FROM c 
WHERE ARRAY_CONTAINS(c.comorbidities, "diabetes")

-- Get patients by education level
SELECT c.patient_id, c.name, c.education_years 
FROM c 
WHERE c.education_years >= 16

-- Get patients with specific MMSE scores
SELECT c.patient_id, c.name, c.cognitive_baseline.mmse 
FROM c 
WHERE c.cognitive_baseline.mmse >= 25
```

### Error Handling

The script includes comprehensive error handling:
- Checks for existing containers
- Handles duplicate patient IDs gracefully
- Provides detailed error logs
- Verifies successful upload

### Data Structure

Each patient document in Cosmos DB will have the following structure:
```json
{
  "id": "290d3a50-82cb-452b-bedb-b7b5315a1a8a",
  "patient_id": "290d3a50-82cb-452b-bedb-b7b5315a1a8a",
  "name": "William Hernandez",
  "dob": "1947-10-19",
  "sex": "female",
  "education_years": 10,
  "comorbidities": ["chronic_kidney_disease", "hyperlipidemia", "hypertension"],
  "medications": ["amlodipine", "atorvastatin", "epoetin"],
  "device_ids": {
    "wearable": "WEAR-001",
    "speech": "SPK-001"
  },
  "cognitive_baseline": {
    "mmse": 27,
    "moca": 24,
    "depression_score": 3
  },
  "document_type": "patient_profile",
  "created_at": "2025-09-18T00:00:00Z"
}
```
