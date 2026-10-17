import re
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, request

from .errors import APIError
from .extensions import db
from .models import User

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_token(user):
    payload = {
        "sub": str(user.id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=current_app.config["JWT_EXPIRES_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise APIError("Missing or malformed Authorization header", 401)
        token = header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            raise APIError("Token has expired", 401)
        except jwt.InvalidTokenError:
            raise APIError("Invalid token", 401)

        user = db.session.get(User, int(payload["sub"]))
        if user is None:
            raise APIError("User no longer exists", 401)
        g.current_user = user
        return view(*args, **kwargs)

    return wrapper


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""

    errors = {}
    if not EMAIL_RE.match(email):
        errors["email"] = "A valid email is required"
    if not name:
        errors["name"] = "Name is required"
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters"
    if errors:
        raise APIError("Validation failed", 422, errors)

    if User.query.filter_by(email=email).first():
        raise APIError("Email is already registered", 409)

    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return {"user": user.to_dict(), "token": create_token(user)}, 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        raise APIError("Invalid email or password", 401)
    return {"user": user.to_dict(), "token": create_token(user)}


@bp.get("/me")
@login_required
def me():
    return {"user": g.current_user.to_dict()}
