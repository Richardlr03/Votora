from app.extensions import db


class YesNoVote(db.Model):
    __tablename__ = "yes_no_votes"
    __table_args__ = (
        db.UniqueConstraint(
            "voter_id", "motion_id", name="uq_yes_no_votes_voter_motion"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey("voters.id"), nullable=False)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey("options.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
