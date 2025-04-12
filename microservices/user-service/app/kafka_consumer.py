from kafka import KafkaConsumer
import json
import time
import logging
from .extensions import db

def start_user_consumer(app):
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                'reservation-events',
                bootstrap_servers=app.config['KAFKA_BOOTSTRAP_SERVERS'].split(','),
                group_id='user-service-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest'
            )
            app.logger.info("Connected to Kafka")
            
            for message in consumer:
                with app.app_context():
                    try:
                        event = message.value
                        if event['type'] == 'reservation-created':
                            app.logger.info(f"New reservation: {event}")
                            # Process your event here
                    except Exception as e:
                        app.logger.error(f"Error processing message: {str(e)}")
                        
        except Exception as e:
            if attempt < max_retries - 1:
                app.logger.warning(f"Kafka connection failed (attempt {attempt + 1}), retrying...")
                time.sleep(retry_delay)
            else:
                app.logger.error("Max retries reached, Kafka consumer stopped")
                raise
