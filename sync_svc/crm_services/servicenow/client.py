import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path to import shared module
from shared.httpclient import HttpClient

# ServiceNow API endpoints
postTableUrl = "/api/now/table/incident"

# Create client with ServiceNow base URL and basic auth
client = HttpClient(
    base_url="https://dev311661.service-now.com",
    auth=('admin', 'testinG@123')
)


def CreateIncidentRecord(incident_data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
    """
    Create an incident record in ServiceNow.
    
    Args:
        incident_data: Dictionary containing incident data (converted to JSON string for description)
        idempotency_key: Idempotency key (goes into short_description)
    
    Returns:
        Dictionary containing response with status_code, headers, and data
    """
    json_data = {
        "short_description": idempotency_key,
        "description": json.dumps(incident_data)
    }
    
    response = client.post(
        url=postTableUrl,
        json_data=json_data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    )
    
    return response
