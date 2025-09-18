# EdgeSim - Cognitive Data Simulation Azure Function

This Azure Function automatically generates and sends realistic cognitive assessment data at regular intervals by:

1. **Timer Trigger**: Runs every 5 minutes (configurable)
2. **Random Patient Selection**: Picks a random patient from Cosmos DB PatientProfiles container
3. **Data Generation**: Creates realistic cognitive assessment data based on patient's baseline
4. **Edge Connector Integration**: Sends data to your edge connector function

## 📋 **Features**

### **Realistic Data Simulation**
- **Attention Metrics**: Digit span, errors, latency based on cognitive baselines
- **Executive Function**: Verbal fluency, articulation rate, pause timing
- **Memory Assessment**: Immediate/delayed recall with intrusion errors
- **Orientation**: Date and location awareness scoring
- **Processing Speed**: Reaction times and missed trials
- **Mood/Behavior**: Sentiment and narrative coherence scoring

### **Patient-Aware Generation**
- Uses actual patient profiles from Cosmos DB
- Considers cognitive baselines (MMSE, MoCA scores)
- Factors in depression levels for realistic performance variation
- Maintains consistency with patient's demographic and health profile

### **Automated Workflow**
- Selects random patients for each simulation cycle
- Generates contextually appropriate data
- Automatically calls edge connector API
- Comprehensive logging and error handling

## 🔧 **Setup Instructions**

### **1. Environment Variables**

Update your `local.settings.json` with these required variables:

```json
{
  \"IsEncrypted\": false,
  \"Values\": {
    \"AzureWebJobsStorage\": \"your-storage-connection-string\",
    \"FUNCTIONS_WORKER_RUNTIME\": \"python\",
    \"COSMOS_DB_CONNECTION_STRING\": \"AccountEndpoint=https://your-cosmos.documents.azure.com:443/;AccountKey=your-key;\",
    \"EDGE_CONNECTOR_URL\": \"https://edgeconnector.azurewebsites.net/api/ingest_data\",
    \"EDGE_CONNECTOR_FUNCTION_CODE\": \"your-function-access-code\"
  }
}
```

### **2. Azure Function App Settings**

When deploying to Azure, add the same environment variables to your Function App Settings:

1. Go to Azure Portal > Function App > Configuration
2. Add the environment variables from above
3. Click \"Save\"

### **3. Dependencies**

The required packages are specified in `requirements.txt`:
- `azure-functions`: Azure Functions runtime
- `azure-cosmos`: Cosmos DB client
- `requests`: HTTP client for edge connector calls

## ⏰ **Timer Configuration**

The function currently runs **every 5 minutes**. To change the frequency, modify the schedule in `function_app.py`:

```python
@app.timer_trigger(schedule=\"0 */5 * * * *\", ...)  # Every 5 minutes
```

**Common Schedule Examples:**
- Every 1 minute: `\"0 */1 * * * *\"`
- Every 10 minutes: `\"0 */10 * * * *\"`
- Every hour: `\"0 0 * * * *\"`
- Every 30 seconds: `\"*/30 * * * * *\"`

## 📊 **Generated Data Format**

The function generates data in this structure:

```json
{
  \"patient_id\": \"290d3a50-82cb-452b-bedb-b7b5315a1a8a\",
  \"device_id\": \"SPK-001\",
  \"session_date\": \"2025-09-18T10:30:00Z\",
  \"attention\": {
    \"digit_span_max\": 7,
    \"errors\": 1,
    \"latency_sec\": 1.2
  },
  \"executive_function\": {
    \"verbal_fluency_words\": 18,
    \"articulation_rate_wps\": 2.1,
    \"avg_pause_ms\": 850
  },
  \"memory\": {
    \"immediate_recall\": 4,
    \"delayed_recall\": 3,
    \"intrusion_errors\": 0
  },
  \"orientation\": {
    \"date_correct\": true,
    \"city_correct\": true,
    \"orientation_correct\": 8
  },
  \"processing_speed\": {
    \"avg_reaction_time_ms\": 520,
    \"missed_trials\": 0
  },
  \"mood_behavior\": {
    \"sentiment_score\": 0.65,
    \"narrative_coherence\": 0.72,
    \"mood_score\": 3
  }
}
```

## 🚀 **Deployment**

### **Local Testing**
```bash
# Install dependencies
pip install -r requirements.txt

# Start the function locally
func start
```

### **Deploy to Azure**
```bash
# Login to Azure
az login

# Deploy function
func azure functionapp publish your-function-app-name
```

## 📝 **Monitoring & Logs**

The function provides comprehensive logging:

- **Patient Selection**: Logs which patient was randomly selected
- **Data Generation**: Confirms successful data creation
- **Edge Connector**: Logs HTTP request success/failure
- **Error Handling**: Detailed error messages for troubleshooting

View logs in:
- **Local**: Console output when running `func start`
- **Azure**: Azure Portal > Function App > Monitor > Logs

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **\"No patients found\"**
   - Ensure PatientProfiles container exists in Cosmos DB
   - Verify patient data was uploaded using the patient profiles upload script

2. **\"Edge connector failed\"**
   - Check EDGE_CONNECTOR_URL and EDGE_CONNECTOR_FUNCTION_CODE
   - Verify the edge connector function is running and accessible

3. **\"Cosmos DB connection failed\"**
   - Verify COSMOS_DB_CONNECTION_STRING is correct
   - Check Cosmos DB account access keys in Azure Portal

4. **Timer not triggering**
   - Ensure AzureWebJobsStorage is properly configured
   - Check that the function is not disabled in Azure Portal

### **Testing Individual Components:**

You can test parts of the system independently:
- **Patient Selection**: Check Cosmos DB queries in Azure Portal Data Explorer
- **Edge Connector**: Test HTTP endpoint directly with Postman or curl
- **Data Generation**: Review generated JSON structure in function logs

## 📈 **Performance Considerations**

- **Cosmos DB RU Consumption**: Random patient queries use cross-partition queries (~5-10 RUs per execution)
- **Edge Connector Load**: One HTTP request every 5 minutes (configurable)
- **Function Execution Time**: Typically 2-5 seconds per execution
- **Memory Usage**: Minimal (~50MB per execution)

The current configuration is suitable for development and moderate production loads. For high-frequency simulation (every few seconds), consider optimizing the patient selection query or implementing caching.

## 🔐 **Security Notes**

- Never commit `local.settings.json` with real credentials
- Use Azure Key Vault for production secrets
- Regularly rotate Cosmos DB and Function access keys
- Monitor function execution logs for any sensitive data exposure