from flask import Flask, redirect, url_for, render_template, session, request, flash
from authlib.integrations.flask_client import OAuth
import requests
import random
import string
from config import Config
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Initialize OAuth
oauth = OAuth(app)

# Register Google OAuth
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account'  # Force la sélection de compte
    }
)

def generate_nonce(length=16):
    """Génère un nonce sécurisé pour la validation OAuth"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def fetch_microservice_data(url, service_name):
    """Fonction helper pour récupérer les données des microservices"""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {service_name}: {str(e)}")
        return {"error": f"Service {service_name} unavailable"}

@app.route('/')
def home():
    session.clear()  # Nettoie la session à chaque accès à la home
    return render_template('home.html')

@app.route('/login')
def login():
    try:
        # Store the intended role (admin or user) in the session
        role = request.args.get('role')
        if role not in ['admin', 'user']:
            role = 'user'  # Default to user if role is invalid
        session['intended_role'] = role

        nonce = generate_nonce()
        session['nonce'] = nonce
        session.modified = True
        
        redirect_uri = url_for('authorize', _external=True)
        return google.authorize_redirect(redirect_uri, nonce=nonce)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        flash("An error occurred during login", "error")
        return redirect(url_for('error'))

@app.route('/authorize')
def authorize():
    try:
        token = google.authorize_access_token()
        if not token:
            raise ValueError("No token received from Google")
            
        user_info = google.parse_id_token(token, session.get('nonce'))
        if not user_info.get('email_verified', False):
            raise ValueError("Email not verified by Google")
        
        # Normalisation des données utilisateur
        session['user'] = {
            'id': user_info.get('sub'),
            'name': user_info.get('name', 'Anonymous'),
            'email': user_info.get('email'),
            'picture': user_info.get('picture')
        }
        session.modified = True
        
        # Check if the user exists in user-service; if not, add them
        users_data = fetch_microservice_data(app.config['USER_SERVICE_URL'] + '/users', 'users')
        user_exists = False
        if not users_data.get('error'):
            for user in users_data.get('users', []):
                if user['email'] == session['user']['email']:
                    user_exists = True
                    break
        
        if not user_exists:
            # Add the user to user-service
            data = {
                'email': session['user']['email'],
                'username': session['user']['name']
            }
            try:
                response = requests.post(f"{app.config['USER_SERVICE_URL']}/users", json=data)
                if response.status_code != 201:
                    logger.error("Failed to add user to user-service")
                    flash("Failed to register your account in the system.", "error")
            except Exception as e:
                logger.error(f"Error adding user to user-service: {str(e)}")
                flash("Error registering your account in the system.", "error")
        
        # Check if the user is an admin based on email
        if session['user']['email'] == 'asmihammouda76@gmail.com' and session.get('intended_role') == 'admin':
            return redirect(url_for('dashboard'))  # Admin dashboard
        else:
            return redirect(url_for('user_dashboard'))  # User dashboard for others
    except Exception as e:
        logger.error(f"Authorization error: {str(e)}")
        session.clear()
        flash("Failed to authenticate with Google", "error")
        return redirect(url_for('error'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    # Only allow access if the user is an admin
    if session['user']['email'] != 'asmihammouda76@gmail.com':
        flash("You do not have admin privileges", "error")
        return redirect(url_for('user_dashboard'))

    # Récupération des données des microservices
    services = {
        'users': app.config['USER_SERVICE_URL'] + '/users',
        'salles': app.config['SALLE_SERVICE_URL'] + '/salles',
        'reservations': app.config['RESERVATION_SERVICE_URL'] + '/reservations'
    }
    
    data = {name: fetch_microservice_data(url, name) for name, url in services.items()}
    
    # Handle salles data separately since it's a list
    salles = [] if isinstance(data['salles'], dict) and data['salles'].get('error') else data['salles']
    
    return render_template(
        'dashboard.html',
        user=session['user'],
        users=data['users'],
        salles=salles,
        reservations=data['reservations']
    )

@app.route('/user_dashboard')
def user_dashboard():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    # Fetch user's reservations (filter by user_id)
    user_id = None
    users_data = fetch_microservice_data(app.config['USER_SERVICE_URL'] + '/users', 'users')
    if not users_data.get('error'):
        for user in users_data.get('users', []):
            if user['email'] == session['user']['email']:
                user_id = user['id']
                break

    reservations = []
    if user_id:
        reservations_data = fetch_microservice_data(app.config['RESERVATION_SERVICE_URL'] + '/reservations', 'reservations')
        if not reservations_data.get('error'):
            reservations = [
                res for res in reservations_data.get('reservations', [])
                if res['user_id'] == user_id
            ]

    # Fetch all rooms
    salles_data = fetch_microservice_data(app.config['SALLE_SERVICE_URL'] + '/salles', 'salles')
    
    # Check if salles_data has an error; if not, it's already a list of rooms
    salles = [] if isinstance(salles_data, dict) and salles_data.get('error') else salles_data

    return render_template(
        'user_dashboard.html',
        user=session['user'],
        user_id=user_id,  # Pass the user_id to the template
        reservations=reservations,
        salles=salles
    )

# Routes for adding/updating/deleting users, salles, and reservations
@app.route('/add_user', methods=['POST'])
def add_user():
    email = request.form.get('email')
    username = request.form.get('username')

    data = {'email': email, 'username': username}

    try:
        response = requests.post(f"{app.config['USER_SERVICE_URL']}/users", json=data)
        if response.status_code == 201:
            flash("Utilisateur ajouté avec succès", "success")
        else:
            flash("Échec de l'ajout de l'utilisateur", "error")
    except Exception as e:
        logger.error(f"Erreur ajout utilisateur: {str(e)}")
        flash("Erreur lors de l'ajout de l'utilisateur", "error")
    return redirect(url_for('dashboard'))

@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    email = request.form.get('email')
    username = request.form.get('username')

    data = {'email': email, 'username': username}

    try:
        response = requests.put(f"{app.config['USER_SERVICE_URL']}/users/{user_id}", json=data)
        if response.status_code == 200:
            flash("Utilisateur mis à jour avec succès", "success")
        else:
            flash("Échec de la mise à jour de l'utilisateur", "error")
    except Exception as e:
        logger.error(f"Erreur mise à jour utilisateur: {str(e)}")
        flash("Erreur lors de la mise à jour", "error")
    return redirect(url_for('dashboard'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        response = requests.delete(f"{app.config['USER_SERVICE_URL']}/users/{user_id}")
        if response.status_code == 204:
            flash("Utilisateur supprimé avec succès", "success")
        else:
            flash("Échec de la suppression de l'utilisateur", "error")
    except Exception as e:
        logger.error(f"Erreur suppression utilisateur: {str(e)}")
        flash("Erreur lors de la suppression", "error")
    return redirect(url_for('dashboard'))

@app.route('/add_salle', methods=['POST'])
def add_salle():
    nom = request.form.get('nom')
    capacite = request.form.get('capacite')
    equipements = request.form.get('equipements', '')

    data = {
        'nom': nom,
        'capacite': int(capacite),
        'equipements': equipements
    }

    try:
        response = requests.post(f"{app.config['SALLE_SERVICE_URL']}/salles", json=data)
        if response.status_code == 201:
            flash("Salle ajoutée avec succès", "success")
        else:
            flash("Échec de l'ajout de la salle", "error")
    except Exception as e:
        logger.error(f"Erreur ajout salle: {str(e)}")
        flash("Erreur lors de l'ajout de la salle", "error")
    return redirect(url_for('dashboard'))

@app.route('/update_salle/<int:salle_id>', methods=['POST'])
def update_salle(salle_id):
    nom = request.form.get('nom')
    capacite = request.form.get('capacite')
    equipements = request.form.get('equipements')

    data = {
        'nom': nom,
        'capacite': int(capacite),
        'equipements': equipements
    }

    try:
        response = requests.put(f"{app.config['SALLE_SERVICE_URL']}/salles/{salle_id}", json=data)
        if response.status_code == 200:
            flash("Salle mise à jour avec succès", "success")
        else:
            flash("Échec de la mise à jour de la salle", "error")
    except Exception as e:
        logger.error(f"Erreur mise à jour salle: {str(e)}")
        flash("Erreur lors de la mise à jour de la salle", "error")
    return redirect(url_for('dashboard'))

@app.route('/delete_salle/<int:salle_id>', methods=['POST'])
def delete_salle(salle_id):
    try:
        response = requests.delete(f"{app.config['SALLE_SERVICE_URL']}/salles/{salle_id}")
        if response.status_code == 200:
            flash("Salle supprimée avec succès", "success")
        else:
            flash("Échec de la suppression de la salle", "error")
    except Exception as e:
        logger.error(f"Erreur suppression salle: {str(e)}")
        flash("Erreur lors de la suppression de la salle", "error")
    return redirect(url_for('dashboard'))

@app.route('/add_reservation', methods=['POST'])
def add_reservation():
    user_id = request.form.get('user_id')
    salle_id = request.form.get('salle_id')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    data = {
        'user_id': int(user_id),
        'salle_id': int(salle_id),
        'start_time': start_time.replace("T", " ") + ":00" if start_time else None,
        'end_time': end_time.replace("T", " ") + ":00" if end_time else None
    }

    try:
        response = requests.post(f"{app.config['RESERVATION_SERVICE_URL']}/reservations", json=data)
        if response.status_code == 201:
            flash("Réservation ajoutée avec succès", "success")
        else:
            flash("Échec de l'ajout de la réservation", "error")
    except Exception as e:
        logger.error(f"Erreur ajout réservation: {str(e)}")
        flash("Erreur lors de l'ajout de la réservation", "error")
    return redirect(url_for('user_dashboard'))

@app.route('/update_reservation/<int:reservation_id>', methods=['POST'])
def update_reservation(reservation_id):
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    data = {
        'start_time': start_time.replace("T", " ") + ":00" if start_time else None,
        'end_time': end_time.replace("T", " ") + ":00" if end_time else None
    }

    try:
        response = requests.put(f"{app.config['RESERVATION_SERVICE_URL']}/reservations/{reservation_id}", json=data)
        if response.status_code == 200:
            flash("Réservation mise à jour avec succès", "success")
        else:
            flash("Échec de la mise à jour de la réservation", "error")
    except Exception as e:
        logger.error(f"Erreur mise à jour réservation: {str(e)}")
        flash("Erreur lors de la mise à jour de la réservation", "error")
    return redirect(url_for('user_dashboard'))

@app.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
def delete_reservation(reservation_id):
    try:
        response = requests.delete(f"{app.config['RESERVATION_SERVICE_URL']}/reservations/{reservation_id}")
        if response.status_code == 200:
            flash("Réservation supprimée avec succès", "success")
        else:
            flash("Échec de la suppression de la réservation", "error")
    except Exception as e:
        logger.error(f"Erreur suppression réservation: {str(e)}")
        flash("Erreur lors de la suppression de la réservation", "error")
    return redirect(url_for('user_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/error')
def error():
    return render_template('error.html')

if __name__ == '__main__':
    app.run(
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 8000),
        debug=app.config.get('DEBUG', False)
    )
