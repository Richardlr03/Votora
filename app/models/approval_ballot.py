from app.extensions import db


class ApprovalBallot(db.Model):
    __tablename__ = "approval_ballots"
    __table_args__ = (
        db.UniqueConstraint(
            "voter_id", "motion_id", name="uq_approval_ballots_voter_motion"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey("voters.id"), nullable=False)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), nullable=False)
    none_above = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="active")

