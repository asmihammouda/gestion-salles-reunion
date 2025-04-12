from kafka import KafkaConsumer
import json
import logging
from datetime import datetime
from .extensions import db
from .models import Reservation

def start_reservation_consumer(app):
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                'reservation-events',
                bootstrap_servers=app.config['KAFKA_BOOTSTRAP_SERVERS'].split(','),
                group_id='reservation-service-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest'
            )
            
            app.logger.info("Kafka consumer connected successfully")
            
            for message in consumer:
                with app.app_context():
                    try:
                        event = message.value
                        app.logger.info(f"Processing event: {event['type']}")
                        
                        if event['type'] == 'reservation-created':
                            # Handle reservation creation
                            reservation = Reservation(
                                user_id=event['data']['user_id'],
                                salle_id=event['data']['salle_id'],
                                date_debut=datetime.fromisoformat(event['data']['start_time']),
                                date_fin=datetime.fromisoformat(event['data']['end_time']),
                                status='confirmed'
                            )
                            db.session.add(reservation)
                            db.session.commit()
                            app.logger.info(f"Reservation created: {reservation.id}")
                            
                    except Exception as e:
                        app.logger.error(f"Error processing message: {str(e)}")
                        db.session.rollback()
                        
        except Exception as e:
            retry_count += 1
            app.logger.error(f"Kafka connection failed (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count < max_retries:
                time.sleep(5)
            else:
                app.logger.error("Max retries reached for Kafka connection")
                raise
