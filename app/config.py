import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///jobtrack.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "24"))
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-that-is-long-enough-for-hs256"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
