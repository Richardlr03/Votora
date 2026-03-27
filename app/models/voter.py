from app.extensions import db


class Voter(db.Model):
    __tablename__ = "voters"
    __table_args__ = (
        db.UniqueConstraint(
            "meeting_id", "student_id", name="uq_voters_meeting_id_student_id"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), nullable=False)
    student_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)

    yes_no_votes = db.relationship("YesNoVote", backref="voter", lazy=True)
    candidate_votes = db.relationship("CandidateVote", backref="voter", lazy=True)
    preference_votes = db.relationship("PreferenceVote", backref="voter", lazy=True)
    score_votes = db.relationship("ScoreVote", backref="voter", lazy=True)
    cumulative_votes = db.relationship("CumulativeVote", backref="voter", lazy=True)
