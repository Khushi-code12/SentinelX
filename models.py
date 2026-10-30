from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Alert(db.Model):
    __tablename__ = 'alerts'
    id            = db.Column(db.Integer, primary_key=True)
    # Local time, matching the timestamps written by camera.py
    timestamp     = db.Column(db.DateTime, default=datetime.now, index=True)
    message       = db.Column(db.String(256), nullable=False)
    # Stored relative to the project root, e.g. "static/alerts/alert_....jpg"
    snapshot_path = db.Column(db.String(256), nullable=False)

    def classes(self):
        """Class names from a message like 'Suspicious activity: guns, Violence at <ts>'."""
        head, sep, _ = self.message.rpartition(' at ')
        body = (head if sep else self.message).partition(': ')[2]
        return [c.strip() for c in body.split(',') if c.strip()]

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
            'classes': self.classes(),
            'snapshot': '/' + self.snapshot_path.replace('\\', '/').lstrip('/')
        }
