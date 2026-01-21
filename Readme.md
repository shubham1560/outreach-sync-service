# Sync Service - Record Synchronization Service

A production-ready event-driven synchronization service that processes events from Kafka and syncs them to external CRM systems (e.g., ServiceNow) with robust error handling, retry logic, and idempotency guarantees.

## Overview

This service implements **one key part** of a bi-directional record synchronization system: **synchronizing events from an internal system to an external CRM provider (ServiceNow)**.

### Key Features

Event-Driven Architecture** - Kafka-based event processing
Robust HTTP Client** - Retry logic with exponential backoff (2^n: 2s, 4s, 8s, 16s, 32s)
Dead Letter Queue (DLQ)** - Failed events are sent to DLQ for manual review
Structured Logging** - UUID-based error correlation for log aggregation tools

## Architecture

Producer(simply queues messages to kafka) -> Kafka Events -> Consumer -> Service -> Client -> Servicenow -> DLQ on failure

## Components

### 1. **HTTP Client** (`shared/httpclient.py`)
The core component with production-ready features:

- **Retry Logic**: Exponential backoff (2^1, 2^2, 2^3, 2^4, 2^5 seconds)
- **Error Classification**: Smart retryable vs non-retryable error detection
  - Retries: ConnectionError, Timeout, 5xx errors, 429 (rate limit)
  - No retry: 4xx errors (except 429)
- **Structured Logging**: UUID-based error correlation
- **Configurable**: Max retries, timeout, jitter

### 2. **Event Consumer** (`consumer.py`)
- Consumes events from Kafka topic
- Idempotency checking to prevent duplicates
- Offset commits after successful processing
- DLQ for failed events

### 3. **Service Layer** (`crm_services/servicenow/service.py`)
- Event transformation (mocked right now)
- Business logic orchestration
- Provider abstraction

## Setup

### Prerequisites

- Python 3.8+
- Kafka running (localhost:9092 by default)
- ServiceNow instance (or mock)

### Installation

1. **Clone the repository**
```bash
cd sync_svc
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Variables**
```bash
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export KAFKA_GROUP_ID="sync-service"
export KAFKA_TOPIC="internal.customer.events"
export KAFKA_DLQ_TOPIC="internal.customer.events.dlq"

# ServiceNow Configuration
export SERVICENOW_BASE_URL="https://{{dev-instance}}.service-now.com"
export SERVICENOW_USERNAME="admin"
export SERVICENOW_PASSWORD="{{password}}"

# HTTP Client Configuration (optional)
export HTTP_MAX_RETRIES="3"
export HTTP_TIMEOUT="30"
```

4. **Run the service**
```bash
python consumer.py
```

## Event Format

Events are expected in the following format:

```json
{
  "event_id": "c87987bf-12fc-4838-92f9-ed91b5b42036",
  "idempotency_key": "5fd42ba7-8870-589e-b35f-b2626a4ab391",
  "event_type": "record.updated",
  "event_version": 1,
  "occurred_at": "2026-01-20T17:16:48.933893+00:00",
  "source": "internal-system",
  "entity": {
    "type": "customer",
    "id": "b99f5f46-ee92-4f2b-bb6a-ba073e24a138",
    "version": "2026-01-20T17:16:48.933893+00:00"
  },
  "payload": {
    "name": "Test Customer",
    "email": "test.customer@example.com",
    "status": "active"
  },
  "metadata": {
    "schema_version": 1
  }
}
```

## How It Works

1. **Event Consumption**: Consumer polls Kafka for events
2. **Idempotency Check**: Verifies if event was already processed
3. **Transformation**: Transforms event to provider-specific format
4. **HTTP Request**: Makes POST request to ServiceNow API
5. **Retry Logic**: Automatically retries on transient errors with exponential backoff
6. **Offset Commit**: Commits Kafka offset only after successful processing
7. **DLQ**: Failed events are sent to DLQ for manual review

## Error Handling

### Retry Strategy

The HTTP client implements exponential backoff:
- **Attempt 1**: 2 seconds (2^1)
- **Attempt 2**: 4 seconds (2^2)
- **Attempt 3**: 8 seconds (2^3)
- **Attempt 4**: 16 seconds (2^4)
- **Attempt 5+**: 32 seconds (2^5) - max cap

### Error Classification

- **Retryable**: ConnectionError, Timeout, 5xx errors, 429 (rate limit)
- **Non-Retryable**: 4xx errors (except 429) - sent to DLQ immediately

### Logging

Errors are logged with UUIDs for correlation:
```
ERROR: abc-123-def-456 - HttpClient.post - Attempt 1/4 - ConnectionError - URL: https://...
INFO: abc-123-def-456 - HttpClient.post - Retrying in 2.00s (attempt 2/4)
```

Search logs by UUID in Datadog/Splunk to see all retry attempts for a single error.

## Testing

### Manual Testing

1. **Start Kafka** (if not already running)
```bash
# Using Docker
docker run -p 9092:9092 apache/kafka:latest
```

2. **Produce a test event**
```bash
# Using kafka-console-producer
echo '{"event_id":"test-123","idempotency_key":"key-123","entity":{"type":"customer"}}' | \
  kafka-console-producer --broker-list localhost:9092 --topic internal.customer.events
```

3. **Run the consumer**
```bash
python consumer.py
```

## Scalability Considerations

### Current Implementation

- **Single Consumer**: Processes events sequentially
- **In-Memory Idempotency**: Not suitable for distributed systems
- **No Rate Limiting**: Could overwhelm external APIs

## Design Decisions

### Why This Approach?

1. **Event-Driven**: Scales to 300M+ requests/day with Kafka's high throughput
2. **HTTP Client Retry**: Handles transient network errors automatically
3. **Idempotency**: Prevents duplicate processing in distributed systems
4. **DLQ**: Failed events don't block the pipeline

### Trade-offs

- **At-Least-Once Processing**: Events may be processed multiple times (mitigated by idempotency)
- **Sequential Processing**: One event at a time (can be parallelized with async or partitions)

## Future Enhancements

Support for UPDATE and DELETE operations
Bi-directional sync (external → internal)
Multiple CRM provider support (Salesforce, HubSpot, etc.)
Schema validation
Rate limiting per provider
Metrics and observability
Unit and integration tests
