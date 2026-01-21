"""
Kafka publisher abstraction for emitting events.

This module provides a clean abstraction layer for publishing events to Kafka,
allowing for easy swapping of implementations or adding retry logic, metrics, etc.
Uses confluent-kafka library.
"""
import json
import logging
from confluent_kafka import Producer, KafkaException
from django.conf import settings

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():
    """Lazy initialization of Kafka producer."""
    global _producer
    if _producer is None:
        bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        if isinstance(bootstrap_servers, list):
            bootstrap_servers = ','.join(bootstrap_servers)
        
        config = {
            'bootstrap.servers': bootstrap_servers,
            'retries': 5,
            'acks': 'all',
        }
        
        _producer = Producer(config)
    return _producer


def _delivery_callback(err, msg):
    """Callback for message delivery confirmation."""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.debug(
            f"Message delivered to {msg.topic()} [{msg.partition()}] "
            f"at offset {msg.offset()}"
        )


def publish(topic: str, key: str, message: dict):
    """
    Publish event to Kafka topic.
    
    Args:
        topic: Kafka topic name
        key: Message key (used for partitioning)
        message: Event payload dictionary
        
    Returns:
        None (fire-and-forget operation)
        
    Note:
        Errors are logged but not raised to avoid breaking Django save operations.
        This is a fire-and-forget operation. The producer handles delivery
        asynchronously via the delivery callback.
    """
    event_id = message.get('event_id', 'unknown')
    event_type = message.get('event_type', 'unknown')
    
    logger.info(
        f"Publishing to Kafka - Topic: {topic}, Key: {key}, "
        f"Event Type: {event_type}, Event ID: {event_id}"
    )
    
    try:
        producer = _get_producer()
        
        value = json.dumps(message).encode('utf-8')
        key_bytes = key.encode('utf-8') if key else None
        
        producer.produce(
            topic=topic,
            key=key_bytes,
            value=value,
            callback=_delivery_callback
        )
        
        producer.poll(0)
        
        logger.info(
            f"Successfully queued message to Kafka - Topic: {topic}, "
            f"Event Type: {event_type}, Event ID: {event_id}"
        )
        return None
    except KafkaException as e:
        logger.error(
            f"Failed to publish to Kafka topic {topic} - "
            f"Event Type: {event_type}, Event ID: {event_id}, Error: {e}",
            exc_info=True
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error publishing to Kafka - "
            f"Event Type: {event_type}, Event ID: {event_id}, Error: {e}",
            exc_info=True
        )
        return None
