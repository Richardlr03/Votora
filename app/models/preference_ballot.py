from app.extensions import db


class PreferenceBallot(db.Model):
    __tablename__ = "preference_ballots"
    __table_args__ = (
        db.UniqueConstraint(
            "voter_id",
            "motion_id",
            name="uq_preference_ballots_voter_motion",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey("voters.id"), nullable=False)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    submitted_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )
