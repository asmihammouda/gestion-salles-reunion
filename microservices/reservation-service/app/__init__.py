from flask import Flask
from .extensions import db, init_kafka
from threading import Thread
import os
from datetime import datetime

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        KAFKA_BOOTSTRAP_SERVERS=os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        USER_SERVICE_URL=os.getenv('USER_SERVICE_URL'),
        SALLE_SERVICE_URL=os.getenv('SALLE_SERVICE_URL')
    )

    # Initialize extensions
    db.init_app(app)
    init_kafka(app)  # Initialize Kafka producer

    # Register blueprints
    from . import routes
    app.register_blueprint(routes.reservation_bp)

    # Create tables
    with app.app_context():
        db.create_all()

    # Start Kafka consumer in background
    if app.config.get('KAFKA_BOOTSTRAP_SERVERS'):
        try:
            from .kafka_consumer import start_reservation_consumer
            Thread(target=start_reservation_consumer, args=(app,), daemon=True).start()
            app.logger.info("Started Kafka consumer thread")
        except Exception as e:
            app.logger.error(f"Failed to start Kafka consumer: {str(e)}")

    return app
