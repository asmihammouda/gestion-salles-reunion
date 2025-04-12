from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import requests
from .models import Reservation
from .extensions import db

reservation_bp = Blueprint('reservation', __name__)

@reservation_bp.route('/reservations', methods=['GET', 'POST'])
def reservations():
    if request.method == 'GET':
        # Récupérer toutes les réservations avec pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        reservations = Reservation.query.paginate(page=page, per_page=per_page)
        
        return jsonify({
            'reservations': [r.to_dict() for r in reservations.items],
            'total': reservations.total,
            'pages': reservations.pages,
            'current_page': reservations.page
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Validation des champs obligatoires
        required_fields = ['user_id', 'salle_id', 'start_time', 'end_time']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Champs manquants"}), 400

        # Validation des dates
        try:
            start_time = datetime.fromisoformat(data['start_time'])
            end_time = datetime.fromisoformat(data['end_time'])
            if start_time >= end_time:
                return jsonify({"error": "La date de fin doit être après la date de début"}), 400
        except ValueError:
            return jsonify({"error": "Format de date invalide. Utilisez le format ISO (ex: 2025-04-10T14:00:00)"}), 400

        # Vérification de l'existence de l'utilisateur
        try:
            user_response = requests.get(
                f"{current_app.config['USER_SERVICE_URL']}/users/{data['user_id']}"
            )
            if user_response.status_code != 200:
                return jsonify({"error": "Utilisateur non trouvé"}), 404
        except requests.RequestException as e:
            current_app.logger.error(f"Erreur de connexion au user-service: {str(e)}")
            return jsonify({"error": "Service utilisateur indisponible"}), 503

        # Vérification de l'existence de la salle
        try:
            salle_response = requests.get(
                f"{current_app.config['SALLE_SERVICE_URL']}/salles/{data['salle_id']}"
            )
            if salle_response.status_code != 200:
                return jsonify({"error": "Salle non trouvée"}), 404
        except requests.RequestException as e:
            current_app.logger.error(f"Erreur de connexion au salle-service: {str(e)}")
            return jsonify({"error": "Service salle indisponible"}), 503

        # Vérification des conflits de réservation
        conflicting_reservation = Reservation.query.filter(
            Reservation.salle_id == data['salle_id'],
            Reservation.date_debut < end_time,
            Reservation.date_fin > start_time
        ).first()
        
        if conflicting_reservation:
            return jsonify({
                "error": "Conflit de réservation",
                "conflicting_reservation": conflicting_reservation.to_dict()
            }), 409

        # Création de la réservation
        try:
            new_reservation = Reservation(
                user_id=data['user_id'],
                salle_id=data['salle_id'],
                date_debut=start_time,
                date_fin=end_time,
                status='confirmed'
            )

            db.session.add(new_reservation)
            db.session.commit()

            # Publication d'un événement Kafka
            if current_app.kafka_producer:
                event = {
                    "type": "reservation-created",
                    "data": {
                        "reservation_id": new_reservation.id,
                        "user_id": new_reservation.user_id,
                        "salle_id": new_reservation.salle_id,
                        "start_time": data['start_time'],
                        "end_time": data['end_time']
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                current_app.kafka_producer.send('reservation-events', event)

            return jsonify(new_reservation.to_dict()), 201

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur lors de la création de réservation: {str(e)}")
            return jsonify({"error": "Erreur interne du serveur"}), 500

@reservation_bp.route('/reservations/<int:reservation_id>', methods=['GET', 'PUT', 'DELETE'])
def reservation_detail(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    if request.method == 'GET':
        return jsonify(reservation.to_dict())
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Validation des données
        if not data:
            return jsonify({"error": "Aucune donnée fournie"}), 400
            
        # Mise à jour des champs modifiables
        try:
            if 'start_time' in data:
                reservation.date_debut = datetime.fromisoformat(data['start_time'])
            if 'end_time' in data:
                reservation.date_fin = datetime.fromisoformat(data['end_time'])
            if 'status' in data:
                reservation.status = data['status']
                
            db.session.commit()
            
            return jsonify(reservation.to_dict())
            
        except ValueError:
            return jsonify({"error": "Format de date invalide"}), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur lors de la mise à jour: {str(e)}")
            return jsonify({"error": "Erreur lors de la mise à jour"}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(reservation)
            db.session.commit()
            return jsonify({"message": "Réservation supprimée avec succès"}), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur lors de la suppression: {str(e)}")
            return jsonify({"error": "Erreur lors de la suppression"}), 500

@reservation_bp.route('/reservations/user/<int:user_id>', methods=['GET'])
def user_reservations(user_id):
    try:
        reservations = Reservation.query.filter_by(user_id=user_id).all()
        return jsonify([r.to_dict() for r in reservations])
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération: {str(e)}")
        return jsonify({"error": "Erreur lors de la récupération"}), 500

@reservation_bp.route('/reservations/salle/<int:salle_id>', methods=['GET'])
def salle_reservations(salle_id):
    try:
        reservations = Reservation.query.filter_by(salle_id=salle_id).all()
        return jsonify([r.to_dict() for r in reservations])
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération: {str(e)}")
        return jsonify({"error": "Erreur lors de la récupération"}), 500
