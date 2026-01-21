"""
Kafka consumer for processing internal system events.
"""
import json
import logging
from typing import Callable
from confluent_kafka import Consumer, KafkaException

from crm_services.servicenow import process_event
from publisher import publish

logger = logging.getLogger(__name__)




class EventConsumer:
    
    def __init__(self, handler: Callable[[dict], None]):
        self.handler = handler
        self.consumer = None
    
    def start(self):
        conf = {
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'sync-service',
            'auto.offset.reset': 'earliest',
        }

        self.consumer = Consumer(conf)
        self.consumer.subscribe(['internal.customer.events'])
        
        try:
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    raise KafkaException(msg.error())

                event = json.loads(msg.value().decode('utf-8'))
                
                self.handler(event)
                
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
        finally:
            if self.consumer:
                self.consumer.close()


def handle_event(event: dict):
    logger.info(f"Received message: {event}")
    try:
        response = process_event(event)
        logger.info(f"Successfully created incident: {response.get('status_code')}")
    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)
        
        try:
            publish(
                topic="internal.customer.events.dlq",
                key=event.get('event_id', ''),
                message=event
            )
            logger.info(f"Event sent to DLQ: {event.get('event_id')}")
        except Exception as dlq_error:
            logger.error(f"Failed to send event to DLQ: {dlq_error}", exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info("Starting Kafka consumer...")
    consumer = EventConsumer(handler=handle_event)
    consumer.start()
