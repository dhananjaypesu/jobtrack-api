from datetime import date, datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

STATUSES = ("wishlist", "applied", "oa", "interview", "offer", "rejected", "withdrawn")


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    applications = db.relationship(
        "Application", backref="owner", cascade="all, delete-orphan", lazy="dynamic"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "name": self.name}


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    company = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="applied")
    location = db.Column(db.String(120))
    job_url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    applied_on = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    history = db.relationship(
        "StatusChange",
        backref="application",
        cascade="all, delete-orphan",
        order_by="StatusChange.changed_at",
    )

    def to_dict(self, include_history=False):
        data = {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "status": self.status,
            "location": self.location,
            "job_url": self.job_url,
            "notes": self.notes,
            "applied_on": self.applied_on.isoformat() if self.applied_on else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_history:
            data["history"] = [h.to_dict() for h in self.history]
        return data


class StatusChange(db.Model):
    __tablename__ = "status_changes"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True
    )
    from_status = db.Column(db.String(20))
    to_status = db.Column(db.String(20), nullable=False)
    changed_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "from": self.from_status,
            "to": self.to_status,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }
