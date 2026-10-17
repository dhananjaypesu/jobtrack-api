# JobTrack API

A REST API for tracking job and internship applications, built with Flask and SQLAlchemy.
Each user signs in with a JWT, logs their applications, moves them through a hiring
pipeline, and gets a summary of how their search is going.

## Features

- **JWT authentication** — register, log in, and access protected routes with a Bearer token
- **Per-user data isolation** — users can only read or change their own applications
- **Full CRUD** for applications with input validation and consistent JSON errors
- **Status pipeline** — `wishlist → applied → oa → interview → offer` (plus `rejected`, `withdrawn`)
- **Status history** — every status change is recorded with a timestamp
- **Filtering, search, sorting and pagination** on the list endpoint
- **Stats endpoint** — counts by status, active applications, response rate and offer rate
- **Test suite** with pytest covering auth, validation, ownership and stats

## Tech stack

Python 3.10+, Flask 3, Flask-SQLAlchemy, PyJWT, SQLite (any SQLAlchemy-supported database works), pytest

## Getting started

```bash
git clone https://github.com/<your-username>/jobtrack-api.git
cd jobtrack-api
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                      # serves on http://127.0.0.1:5000
```

Configuration is read from environment variables:

| Variable            | Default                  | Purpose                        |
|---------------------|--------------------------|--------------------------------|
| `SECRET_KEY`        | `dev-secret-change-me`   | Signs JWTs — set this in production |
| `DATABASE_URL`      | `sqlite:///jobtrack.db`  | SQLAlchemy database URL        |
| `JWT_EXPIRES_HOURS` | `24`                     | Token lifetime                 |

## Running tests

```bash
pytest -q
```

## API reference

All application routes require the header `Authorization: Bearer <token>`.

### Auth

| Method | Endpoint             | Description                    |
|--------|----------------------|--------------------------------|
| POST   | `/api/auth/register` | Create an account, returns a token |
| POST   | `/api/auth/login`    | Log in, returns a token        |
| GET    | `/api/auth/me`       | Current user                   |

### Applications

| Method | Endpoint                   | Description                         |
|--------|----------------------------|-------------------------------------|
| GET    | `/api/applications`        | List with filters (see below)       |
| POST   | `/api/applications`        | Create an application               |
| GET    | `/api/applications/<id>`   | Get one, including status history   |
| PATCH  | `/api/applications/<id>`   | Update any fields                   |
| DELETE | `/api/applications/<id>`   | Delete                              |
| GET    | `/api/applications/stats`  | Pipeline summary                    |

**List query parameters**

- `status` — one or more comma-separated statuses, e.g. `?status=interview,offer`
- `q` — search company, role and notes
- `sort` — `applied_on`, `company`, `updated_at` or `status`; prefix `-` for descending (default `-applied_on`)
- `page`, `per_page` — pagination (max 100 per page)

### Example

```bash
# Register
curl -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","name":"Me","password":"password123"}'

# Create an application
curl -X POST http://127.0.0.1:5000/api/applications \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"company":"Acme","role":"Backend Intern","location":"Bengaluru","applied_on":"2026-10-01"}'

# Move it to the interview stage
curl -X PATCH http://127.0.0.1:5000/api/applications/1 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"status":"interview"}'

# See your stats
curl http://127.0.0.1:5000/api/applications/stats -H "Authorization: Bearer $TOKEN"
```

Example stats response:

```json
{
  "total": 5,
  "by_status": {"wishlist": 1, "applied": 1, "oa": 0, "interview": 1, "offer": 1, "rejected": 1, "withdrawn": 0},
  "active": 3,
  "response_rate": 0.75,
  "offer_rate": 0.25
}
```

`response_rate` is the share of submitted applications (everything except wishlist) that ever
reached an OA, interview or offer — even if later rejected.

## Project structure

```
jobtrack-api/
├── app/
│   ├── __init__.py       # app factory
│   ├── config.py         # settings
│   ├── extensions.py     # SQLAlchemy instance
│   ├── models.py         # User, Application, StatusChange
│   ├── auth.py           # register/login + login_required decorator
│   ├── applications.py   # CRUD, filters, stats
│   └── errors.py         # JSON error handling
├── tests/
├── run.py
└── requirements.txt
```

## Ideas for next steps

- Interview reminders and follow-up dates
- Rate limiting on auth routes
- Docker setup and deployment to Render or Railway
- A small React or HTML front end
