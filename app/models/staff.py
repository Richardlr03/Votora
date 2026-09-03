from sqlalchemy.sql import func

from app.extensions import db


class Flag(db.Model):
    __tablename__ = "flags"

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    flagged_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolution_note = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    flagger = db.relationship("User", foreign_keys=[flagged_by])
    resolver = db.relationship("User", foreign_keys=[resolved_by])


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(30), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    flag_id = db.Column(db.Integer, db.ForeignKey("flags.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    actor = db.relationship("User", foreign_keys=[actor_id])
