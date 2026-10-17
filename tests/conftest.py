import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, email="dev@example.com", name="Dev", password="password123"):
    return client.post(
        "/api/auth/register",
        json={"email": email, "name": name, "password": password},
    )


@pytest.fixture
def auth_headers(client):
    token = register(client).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}
