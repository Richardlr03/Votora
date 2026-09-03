from flask_login import UserMixin
from sqlalchemy.sql import func

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    is_staff = db.Column(db.Boolean, nullable=False, default=False)
    staff_role = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    meetings = db.relationship("Meeting", backref="admin", lazy=True)
