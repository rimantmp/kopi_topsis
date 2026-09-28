from datetime import datetime, timezone
import uuid

from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(191), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active_flag = db.Column("is_active", db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime)
    role = db.relationship("Role", backref="users")

    @property
    def is_active(self):
        return self.is_active_flag

    @property
    def is_admin(self):
        return self.role and self.role.name == "admin"

    @property
    def is_farmer(self):
        return self.role and self.role.name in {"petani", "user"}

    @property
    def is_department_head(self):
        return self.role and self.role.name == "kepala_dinas"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Criterion(TimestampMixin, db.Model):
    __tablename__ = "criteria"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), unique=True, nullable=False)
    weight = db.Column(db.Numeric(12, 10), nullable=False)
    attribute_type = db.Column(db.String(10), nullable=False, default="benefit")
    unit = db.Column(db.String(50))
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    subcriteria = db.relationship("Subcriterion", backref="criterion", cascade="all, delete-orphan")


class Subcriterion(TimestampMixin, db.Model):
    __tablename__ = "subcriteria"
    __table_args__ = (UniqueConstraint("criterion_id", "name"),)
    id = db.Column(db.Integer, primary_key=True)
    criterion_id = db.Column(db.Integer, db.ForeignKey("criteria.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    technical_range = db.Column(db.String(191), nullable=False)
    score = db.Column(db.Numeric(10, 4), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Variety(TimestampMixin, db.Model):
    __tablename__ = "varieties"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    scores = db.relationship("VarietyScore", backref="variety", cascade="all, delete-orphan")


class Location(TimestampMixin, db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(191), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class VarietyScore(TimestampMixin, db.Model):
    __tablename__ = "variety_scores"
    __table_args__ = (UniqueConstraint("variety_id", "criterion_id"),)
    id = db.Column(db.Integer, primary_key=True)
    variety_id = db.Column(db.Integer, db.ForeignKey("varieties.id"), nullable=False, index=True)
    criterion_id = db.Column(db.Integer, db.ForeignKey("criteria.id"), nullable=False, index=True)
    score = db.Column(db.Numeric(14, 6), nullable=False)
    source_note = db.Column(db.String(255))
    criterion = db.relationship("Criterion")


class RecommendationSession(db.Model):
    __tablename__ = "recommendation_sessions"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True, index=True)
    location_name = db.Column(db.String(191))
    status = db.Column(db.String(20), nullable=False, default="processing")
    model_version = db.Column(db.String(50), nullable=False, default="TOPSIS-1.0")
    criteria_snapshot = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    completed_at = db.Column(db.DateTime)
    user = db.relationship("User", backref="recommendation_sessions")
    location = db.relationship("Location")
    inputs = db.relationship("RecommendationInput", backref="session", cascade="all, delete-orphan")
    results = db.relationship("RecommendationResult", backref="session", cascade="all, delete-orphan")
    calculation = db.relationship("TopsisCalculation", backref="session", uselist=False, cascade="all, delete-orphan")


class RecommendationInput(db.Model):
    __tablename__ = "recommendation_inputs"
    __table_args__ = (UniqueConstraint("session_id", "criterion_id"),)
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("recommendation_sessions.id"), nullable=False)
    criterion_id = db.Column(db.Integer, db.ForeignKey("criteria.id"), nullable=False)
    raw_value = db.Column(db.String(191), nullable=False)
    mapped_score = db.Column(db.Numeric(14, 6), nullable=False)
    mapping_snapshot = db.Column(db.JSON, nullable=False)
    criterion = db.relationship("Criterion")


class RecommendationResult(db.Model):
    __tablename__ = "recommendation_results"
    __table_args__ = (UniqueConstraint("session_id", "variety_id"),)
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("recommendation_sessions.id"), nullable=False)
    variety_id = db.Column(db.Integer, db.ForeignKey("varieties.id"), nullable=False)
    rank_no = db.Column(db.Integer, nullable=False)
    distance_positive = db.Column(db.Numeric(20, 12), nullable=False)
    distance_negative = db.Column(db.Numeric(20, 12), nullable=False)
    preference_score = db.Column(db.Numeric(20, 12), nullable=False)
    variety = db.relationship("Variety")


class TopsisCalculation(db.Model):
    __tablename__ = "topsis_calculations"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("recommendation_sessions.id"), unique=True, nullable=False)
    decision_matrix = db.Column(db.JSON, nullable=False)
    normalization_matrix = db.Column(db.JSON, nullable=False)
    weighted_matrix = db.Column(db.JSON, nullable=False)
    positive_ideal = db.Column(db.JSON, nullable=False)
    negative_ideal = db.Column(db.JSON, nullable=False)
    calculated_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(64), nullable=False)
    before_data = db.Column(db.JSON)
    after_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
