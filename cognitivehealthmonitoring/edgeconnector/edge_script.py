import urllib.request
import json

# Request data goes here
# The example below assumes JSON formatting which may be updated
# depending on the format your endpoint expects.
# More information can be found here:
# https://docs.microsoft.com/azure/machine-learning/how-to-deploy-advanced-entry-script
data = {
    "patient_id": "P123",
    "device_id": "D456",
    "session_date": "2025-09-17T10:30:00Z",
    "attention": {
        "digit_span_max": 7,
        "latency_sec": 3.1
    },
    "executive_function": {
        "verbal_fluency_words": 42,
        "avg_pause_ms": 1800
    },
    "memory": {
        "immediate_recall": 9,
        "delayed_recall": 7
    },
    "orientation": {
        "orientation_correct": 8
    },
    "processing_speed": {
        "avg_reaction_time_ms": 520
    },
    "mood_behavior": {
        "mood_score": 3
    }
}

body = str.encode(json.dumps(data))

url = 'https://cog-health-endpt-f9d11f.eastus.inference.ml.azure.com/score'
# Replace this with the primary/secondary key, AMLToken, or Microsoft Entra ID token for the endpoint
api_key = ''
if not api_key:
    raise Exception("A key should be provided to invoke the endpoint")


headers = {'Content-Type':'application/json', 'Accept': 'application/json', 'Authorization':('Bearer '+ api_key)}

req = urllib.request.Request(url, body, headers)

try:
    response = urllib.request.urlopen(req)

    result = response.read()
    print(result)
except urllib.error.HTTPError as error:
    print("The request failed with status code: " + str(error.code))

    # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
    print(error.info())
    print(error.read().decode("utf8", 'ignore'))