from app.extensions import db


class Meeting(db.Model):
    __tablename__ = "meetings"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    motions = db.relationship("Motion", backref="meeting", lazy=True)
    voters = db.relationship("Voter", backref="meeting", lazy=True)
