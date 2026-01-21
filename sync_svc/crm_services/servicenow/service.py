from typing import Dict, Any
from .client import CreateIncidentRecord


def mock_transformation(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mock transformation function that just passes back the data."""

    """
    We can transform the data here to match the ServiceNow schema.
    """
    return data


def process_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an event and create an incident record in ServiceNow.
    
    Args:
        event: Event dictionary containing event_id, idempotency_key, entity, etc.
    
    Returns:
        Response from CreateIncidentRecord
    """
    transformed_data = mock_transformation(event)
    
    entity_data = transformed_data.get('entity', {})
    idempotency_key = transformed_data.get('idempotency_key', '')

    ## We can check the idempotency key here to prevent duplication via redis or database
    
    response = CreateIncidentRecord(
        incident_data=entity_data,
        idempotency_key=idempotency_key
    )
    
    return response
