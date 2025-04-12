from flask import Flask
from .extensions import db, init_kafka
from threading import Thread
import os  # Add this import

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI='postgresql://admin:admin123@user-db/user_db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    )
    
    # Initialize extensions
    db.init_app(app)
    init_kafka(app)
    
    # Register blueprints
    from . import routes
    app.register_blueprint(routes.user_bp)
    
    # Start Kafka consumer
    if app.config.get('KAFKA_BOOTSTRAP_SERVERS'):
        try:
            from .kafka_consumer import start_user_consumer
            Thread(target=start_user_consumer, args=(app,), daemon=True).start()
        except Exception as e:
            app.logger.error(f"Failed to start Kafka consumer: {str(e)}")
    
    return app
