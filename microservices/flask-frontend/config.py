# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

    # URLs for your microservices (from docker-compose.yml)
    USER_SERVICE_URL = "http://user-service:5000"
    SALLE_SERVICE_URL = "http://salle-service:5000"
    RESERVATION_SERVICE_URL = "http://reservation-service:5000"
