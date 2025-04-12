from flask_sqlalchemy import SQLAlchemy
from kafka import KafkaProducer
import json
import os

db = SQLAlchemy()
kafka_producer = None

def init_kafka(app):
    global kafka_producer
    if os.environ.get('KAFKA_BOOTSTRAP_SERVERS'):
        try:
            kafka_producer = KafkaProducer(
                bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'].split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                api_version=(2, 8, 1)
            )
            app.logger.info("Kafka producer initialized")
        except Exception as e:
            app.logger.error(f"Failed to initialize Kafka: {str(e)}")
