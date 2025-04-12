from flask import Flask
from .extensions import db, kafka_producer
from threading import Thread
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:admin123@salle-db/salle_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['KAFKA_BOOTSTRAP_SERVERS'] = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    
    db.init_app(app)
    
    from . import routes
    app.register_blueprint(routes.salle_bp)
    
    with app.app_context():
        db.create_all()
    
    if app.config.get('KAFKA_BOOTSTRAP_SERVERS'):
        try:
            from .kafka_consumer import start_salle_consumer
            Thread(target=start_salle_consumer, args=(app,), daemon=True).start()
        except Exception as e:
            app.logger.error(f"Failed to start Kafka consumer: {str(e)}")
    
    return app
