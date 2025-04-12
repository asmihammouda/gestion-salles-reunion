from kafka import KafkaConsumer
import json
import time
from .extensions import db
from .models import Disponibilite
from datetime import datetime 

def start_salle_consumer(app):
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                'reservation-events',
                bootstrap_servers=app.config['KAFKA_BOOTSTRAP_SERVERS'].split(','),
                group_id='salle-service-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                api_version=(2, 8, 0)
            )
            
            app.logger.info("Connected to Kafka for salle updates")
            
            for message in consumer:
                with app.app_context():
                    try:
                        event = message.value
                        if event['type'] == 'reservation-created':
                            salle_id = event['data']['salle_id']
                            # Mettre à jour la disponibilité
                            dispo = Disponibilite(
                                salle_id=salle_id,
                                date_debut=datetime.fromisoformat(event['data']['start_time']),
                                date_fin=datetime.fromisoformat(event['data']['end_time']),
                                status='reserve'
                            )
                            db.session.add(dispo)
                            db.session.commit()
                            app.logger.info(f"Disponibilité mise à jour pour salle {salle_id}")
                            
                    except Exception as e:
                        app.logger.error(f"Error processing message: {str(e)}")
                        
        except Exception as e:
            retry_count += 1
            app.logger.error(f"Kafka connection failed (attempt {retry_count}): {str(e)}")
            if retry_count < max_retries:
                time.sleep(5)
            else:
                app.logger.error("Max retries reached for Kafka connection")
                raise
