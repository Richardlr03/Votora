from app.extensions import db

DEFAULT_MEMBER_ID_LABEL = "Member ID"


class Meeting(db.Model):
    __tablename__ = "meetings"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    meeting_date = db.Column(db.Date, nullable=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    join_token = db.Column(db.String(64), unique=True, nullable=True)
    registration_open = db.Column(db.Boolean, nullable=False, default=False)
    member_id_label = db.Column(
        db.String(100), nullable=False, default=DEFAULT_MEMBER_ID_LABEL
    )
    status = db.Column(db.String(20), nullable=False, default="active")

    motions = db.relationship("Motion", backref="meeting", lazy=True)
    voters = db.relationship("Voter", backref="meeting", lazy=True)
