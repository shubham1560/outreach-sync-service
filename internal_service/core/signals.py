"""
Django signals for emitting events to Kafka on model changes.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Customer
from .events.builders import build_customer_event
from .kafka.publisher import publish

logger = logging.getLogger(__name__)

TOPIC_NAME = "internal.customer.events"


@receiver(post_save, sender=Customer)
def customer_post_save(sender, instance, created, **kwargs):
    """
    Emit event to Kafka when a Customer is created or updated.
    
    """
    event_type = "record.created" if created else "record.updated"
    
    logger.info(
        f"Signal fired: Customer {event_type} - "
        f"ID: {instance.id}, Email: {instance.email}, Status: {instance.status}"
    )
    
    event = build_customer_event(event_type, instance)
    
    logger.info(
        f"Event built: {event_type} - "
        f"Event ID: {event['event_id']}, Entity ID: {event['entity']['id']}"
    )

    publish(
        topic=TOPIC_NAME,
        key=str(instance.id),
        message=event,
    )
