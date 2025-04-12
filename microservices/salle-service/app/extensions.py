from flask_sqlalchemy import SQLAlchemy
from kafka import KafkaProducer
import json
import os

db = SQLAlchemy()
kafka_producer = None

def init_kafka(app):
    global kafka_producer
    try:
        kafka_producer = KafkaProducer(
            bootstrap_servers=app.config['KAFKA_BOOTSTRAP_SERVERS'].split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(2, 8, 0),
            retries=3
        )
        app.logger.info("Kafka producer initialized")
    except Exception as e:
        app.logger.error(f"Failed to initialize Kafka: {str(e)}")
        kafka_producer = None
