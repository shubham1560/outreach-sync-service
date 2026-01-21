"""
Event builders for constructing well-structured, versioned events.
"""
import uuid
from datetime import datetime, timezone

# Namespace for deterministic UUID generation (idempotency keys)
IDEMPOTENCY_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def build_customer_event(event_type: str, customer) -> dict:
    """
    Build a versioned customer event following the event contract.
    
    Args:
        event_type: Event type (e.g., "record.created", "record.updated")
        customer: Customer model instance
        
    Returns:
        Dictionary containing the complete event structure with:
        - event_id: Unique identifier for tracing
        - idempotency_key: Deterministic key for deduplication
        - event_type: Type of event
        - occurred_at: ISO 8601 timestamp in UTC
        - source: System identifier
        - entity: Entity type, ID
        - payload: Event data
        - metadata: Schema metadata
    """
    
    idempotency_name = f"{event_type}:customer:{customer.id}"
    idempotency_key = str(uuid.uuid5(IDEMPOTENCY_NAMESPACE, idempotency_name))
    
    return {
        "event_id": str(uuid.uuid4()),
        "idempotency_key": idempotency_key,
        "event_type": event_type,
        "occurred_at": customer.updated_at.astimezone(timezone.utc).isoformat(),
        "source": "internal-system",
        "entity": {
            "type": "customer",
            "id": str(customer.id),
        },
        "payload": {
            "name": customer.name,
            "email": customer.email,
            "status": customer.status,
        },
        "metadata": {
            "schema_version": 1
        }
    }
