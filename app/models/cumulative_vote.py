from app.extensions import db


class CumulativeVote(db.Model):
    __tablename__ = "cumulative_votes"
    __table_args__ = (
        db.UniqueConstraint(
            "voter_id",
            "motion_id",
            "option_id",
            name="uq_cumulative_votes_voter_motion_option",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey("voters.id"), nullable=False)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey("options.id"), nullable=False)
    points = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")

    option = db.relationship("Option", backref="cumulative_votes")
