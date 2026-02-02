from app.extensions import db


class Voter(db.Model):
    __tablename__ = "voters"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)

    votes = db.relationship("Vote", backref="voter", lazy=True)
