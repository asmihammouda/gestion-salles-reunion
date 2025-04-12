from flask import Blueprint, request, jsonify, current_app
from .extensions import db, kafka_producer
from .models import User
from datetime import datetime

# Définir le Blueprint
user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        # Récupérer tous les utilisateurs (avec pagination pour les grandes collections)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        users = User.query.paginate(page=page, per_page=per_page)
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': users.page
        })
    
    elif request.method == 'POST':
        # Créer un nouvel utilisateur
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({"error": "Email is required"}), 400
            
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "User already exists"}), 409
            
        new_user = User(
            email=data['email'],
            username=data.get('username'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        if kafka_producer:
            try:
                kafka_producer.send('user-events', {
                    'event_type': 'user-created',
                    'user_id': new_user.id,
                    'email': new_user.email,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                current_app.logger.error(f"Erreur Kafka: {str(e)}")
        
        return jsonify(new_user.to_dict()), 201

@user_bp.route('/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'GET':
        return jsonify(user.to_dict())
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Validation des données
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Mise à jour de l'email
        if 'email' in data:
            if User.query.filter(User.email == data['email'], User.id != user_id).first():
                return jsonify({"error": "Email already in use"}), 400
            user.email = data['email']
        
        # Mise à jour du username
        if 'username' in data:
            user.username = data['username']
            
        # Mise à jour du statut
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
            
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        if kafka_producer:
            try:
                kafka_producer.send('user-events', {
                    'event_type': 'user-updated',
                    'user_id': user.id,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                current_app.logger.error(f"Erreur Kafka: {str(e)}")
        
        return jsonify(user.to_dict())
    
    elif request.method == 'DELETE':
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200

@user_bp.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de santé du service"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
