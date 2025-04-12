from datetime import datetime
from .extensions import db

class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    salle_id = db.Column(db.Integer, nullable=False)
    date_debut = db.Column(db.DateTime, nullable=False)
    date_fin = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='confirmed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "salle_id": self.salle_id,
            "start_time": self.date_debut.isoformat(),
            "end_time": self.date_fin.isoformat(),
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }
