from flask import Flask

from .config import Config
from .extensions import db


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)

    from .auth import bp as auth_bp
    from .applications import bp as applications_bp
    from .errors import register_error_handlers

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(applications_bp, url_prefix="/api/applications")
    register_error_handlers(app)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    with app.app_context():
        db.create_all()

    return app
