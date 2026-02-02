from app.extensions import db


class Motion(db.Model):
    __tablename__ = "motions"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False, default="YES_NO")
    num_winners = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="DRAFT")

    options = db.relationship("Option", backref="motion", lazy=True)
    votes = db.relationship("Vote", backref="motion", lazy=True)
