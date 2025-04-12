from flask import Blueprint, request, jsonify, current_app
from .extensions import db, kafka_producer
from .models import Salle, Disponibilite
from datetime import datetime

salle_bp = Blueprint('salle', __name__)

@salle_bp.route('/salles', methods=['GET', 'POST'])
def salles():
    if request.method == 'GET':
        salles = Salle.query.all()
        return jsonify([salle.to_dict() for salle in salles])
    
    elif request.method == 'POST':
        data = request.get_json()
        
        if Salle.query.filter_by(nom=data['nom']).first():
            return jsonify({"error": "Salle already exists"}), 409
            
        new_salle = Salle(
            nom=data['nom'],
            capacite=data['capacite'],
            equipements=data.get('equipements', '')
        )
        
        db.session.add(new_salle)
        db.session.commit()
        
        return jsonify(new_salle.to_dict()), 201

@salle_bp.route('/salles/<int:salle_id>', methods=['GET', 'PUT', 'DELETE'])
def salle_detail(salle_id):
    salle = Salle.query.get_or_404(salle_id)
    
    if request.method == 'GET':
        return jsonify(salle.to_dict())
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        if 'nom' in data:
            if Salle.query.filter(Salle.nom == data['nom'], Salle.id != salle_id).first():
                return jsonify({"error": "Salle name already in use"}), 400
            salle.nom = data['nom']
        
        if 'capacite' in data:
            salle.capacite = data['capacite']
            
        if 'equipements' in data:
            salle.equipements = data['equipements']
            
        db.session.commit()
        
        if kafka_producer:
            try:
                kafka_producer.send('salle-events', {
                    'event_type': 'salle-updated',
                    'salle_id': salle_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                current_app.logger.error(f"Erreur Kafka: {str(e)}")
        
        return jsonify(salle.to_dict())
    
    elif request.method == 'DELETE':
        db.session.delete(salle)
        db.session.commit()
        return jsonify({"message": "Salle deleted"}), 200

@salle_bp.route('/salles/<int:salle_id>/disponibilites', methods=['GET', 'POST'])
def gestion_disponibilites(salle_id):
    if request.method == 'GET':
        disponibilites = Disponibilite.query.filter_by(salle_id=salle_id).all()
        return jsonify([d.to_dict() for d in disponibilites])
    
    elif request.method == 'POST':
        data = request.get_json()
        
        conflit = Disponibilite.query.filter(
            Disponibilite.salle_id == salle_id,
            Disponibilite.date_debut < data['date_fin'],
            Disponibilite.date_fin > data['date_debut']
        ).first()
        
        if conflit:
            return jsonify({
                "error": "Conflit de réservation",
                "conflit": conflit.to_dict()
            }), 409
            
        new_dispo = Disponibilite(
            salle_id=salle_id,
            date_debut=datetime.fromisoformat(data['date_debut']),
            date_fin=datetime.fromisoformat(data['date_fin']),
            status=data.get('status', 'reserve')
        )
        
        db.session.add(new_dispo)
        db.session.commit()
        
        return jsonify(new_dispo.to_dict()), 201
