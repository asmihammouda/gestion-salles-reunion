from datetime import datetime
from .extensions import db

class Salle(db.Model):
    __tablename__ = 'salles'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), unique=True, nullable=False)
    capacite = db.Column(db.Integer, nullable=False)
    equipements = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    disponibilites = db.relationship('Disponibilite', backref='salle', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "capacite": self.capacite,
            "equipements": self.equipements,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Disponibilite(db.Model):
    __tablename__ = 'disponibilites'
    
    id = db.Column(db.Integer, primary_key=True)
    salle_id = db.Column(db.Integer, db.ForeignKey('salles.id'), nullable=False)
    date_debut = db.Column(db.DateTime, nullable=False)
    date_fin = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='libre')  # libre/reserve/maintenance

    def to_dict(self):
        return {
            "id": self.id,
            "salle_id": self.salle_id,
            "date_debut": self.date_debut.isoformat(),
            "date_fin": self.date_fin.isoformat(),
            "status": self.status
        }
