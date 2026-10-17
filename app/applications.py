from datetime import date

from flask import Blueprint, current_app, g, request
from sqlalchemy import func, or_

from .auth import login_required
from .errors import APIError
from .extensions import db
from .models import STATUSES, Application, StatusChange

bp = Blueprint("applications", __name__)

EDITABLE_FIELDS = ("company", "role", "status", "location", "job_url", "notes", "applied_on")
SORTABLE_FIELDS = {
    "applied_on": Application.applied_on,
    "company": Application.company,
    "updated_at": Application.updated_at,
    "status": Application.status,
}


def validate_payload(data, partial=False):
    errors = {}
    cleaned = {}

    for field in EDITABLE_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if isinstance(value, str):
            value = value.strip()
        cleaned[field] = value if value != "" else None

    if not partial:
        for required in ("company", "role"):
            if not cleaned.get(required):
                errors[required] = f"{required.capitalize()} is required"
    else:
        for required in ("company", "role"):
            if required in cleaned and not cleaned[required]:
                errors[required] = f"{required.capitalize()} cannot be empty"

    status = cleaned.get("status")
    if status is not None and status not in STATUSES:
        errors["status"] = f"Status must be one of: {', '.join(STATUSES)}"

    if cleaned.get("applied_on"):
        try:
            cleaned["applied_on"] = date.fromisoformat(cleaned["applied_on"])
        except (TypeError, ValueError):
            errors["applied_on"] = "Use YYYY-MM-DD format"

    if errors:
        raise APIError("Validation failed", 422, errors)
    return cleaned


def get_owned_application(app_id):
    application = Application.query.filter_by(
        id=app_id, user_id=g.current_user.id
    ).first()
    if application is None:
        raise APIError("Application not found", 404)
    return application


def record_status_change(application, old_status, new_status):
    if old_status != new_status:
        application.history.append(
            StatusChange(from_status=old_status, to_status=new_status)
        )


@bp.get("")
@login_required
def list_applications():
    query = Application.query.filter_by(user_id=g.current_user.id)

    status = request.args.get("status")
    if status:
        wanted = [s.strip() for s in status.split(",") if s.strip()]
        invalid = [s for s in wanted if s not in STATUSES]
        if invalid:
            raise APIError(f"Unknown status filter: {', '.join(invalid)}", 400)
        query = query.filter(Application.status.in_(wanted))

    search = request.args.get("q")
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Application.company.ilike(like),
                Application.role.ilike(like),
                Application.notes.ilike(like),
            )
        )

    sort = request.args.get("sort", "-applied_on")
    descending = sort.startswith("-")
    column = SORTABLE_FIELDS.get(sort.lstrip("-"))
    if column is None:
        raise APIError(f"Cannot sort by '{sort.lstrip('-')}'", 400)
    query = query.order_by(column.desc() if descending else column.asc(), Application.id.desc())

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = request.args.get(
        "per_page", current_app.config["DEFAULT_PAGE_SIZE"], type=int
    )
    per_page = min(max(per_page, 1), current_app.config["MAX_PAGE_SIZE"])
    result = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "items": [a.to_dict() for a in result.items],
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
    }


@bp.post("")
@login_required
def create_application():
    data = validate_payload(request.get_json(silent=True) or {})
    data.setdefault("status", "applied")
    if data["status"] is None:
        data["status"] = "applied"

    application = Application(user_id=g.current_user.id, **data)
    record_status_change(application, None, application.status)
    db.session.add(application)
    db.session.commit()
    return application.to_dict(include_history=True), 201


@bp.get("/<int:app_id>")
@login_required
def get_application(app_id):
    return get_owned_application(app_id).to_dict(include_history=True)


@bp.patch("/<int:app_id>")
@login_required
def update_application(app_id):
    application = get_owned_application(app_id)
    data = validate_payload(request.get_json(silent=True) or {}, partial=True)

    if "status" in data and data["status"] is None:
        raise APIError("Validation failed", 422, {"status": "Status cannot be empty"})

    old_status = application.status
    for field, value in data.items():
        setattr(application, field, value)
    record_status_change(application, old_status, application.status)

    db.session.commit()
    return application.to_dict(include_history=True)


@bp.delete("/<int:app_id>")
@login_required
def delete_application(app_id):
    application = get_owned_application(app_id)
    db.session.delete(application)
    db.session.commit()
    return "", 204


@bp.get("/stats")
@login_required
def stats():
    rows = (
        db.session.query(Application.status, func.count(Application.id))
        .filter(Application.user_id == g.current_user.id)
        .group_by(Application.status)
        .all()
    )
    by_status = {status: 0 for status in STATUSES}
    by_status.update({status: count for status, count in rows})
    total = sum(by_status.values())

    submitted = total - by_status["wishlist"]
    progressed = by_status["oa"] + by_status["interview"] + by_status["offer"]
    ever_progressed = (
        db.session.query(func.count(func.distinct(StatusChange.application_id)))
        .join(Application)
        .filter(
            Application.user_id == g.current_user.id,
            StatusChange.to_status.in_(("oa", "interview", "offer")),
        )
        .scalar()
    )

    return {
        "total": total,
        "by_status": by_status,
        "active": by_status["applied"] + progressed,
        "response_rate": round(ever_progressed / submitted, 3) if submitted else 0.0,
        "offer_rate": round(by_status["offer"] / submitted, 3) if submitted else 0.0,
    }
