import os

from flask import Flask, render_template
from dotenv import load_dotenv

from .config import Config
from .extensions import csrf, db, login_manager, migrate


UNIT_DESCRIPTIONS = {
    "mdpl": "meter di atas permukaan laut",
    "°c": "derajat Celsius",
    "mm/tahun": "milimeter per tahun",
    "kg/ha/tahun": "kilogram per hektare per tahun",
    "skor": "skor penilaian",
}


def unit_description(unit):
    if not unit:
        return None
    # MySQL lama bisa menyimpan "°C" sebagai "�C" (karakter replacement).
    key = unit.strip().lower().replace("�", "°")
    return UNIT_DESCRIPTIONS.get(key)


def create_app(config_object=Config):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .models import User
    from .routes.auth import bp as auth_bp
    from .routes.main import bp as main_bp
    from .routes.master import bp as master_bp
    from .routes.recommendation import bp as recommendation_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(master_bp)
    app.register_blueprint(recommendation_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_helpers():
        return {"unit_description": unit_description}

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(422)
    @app.errorhandler(500)
    def handle_error(error):
        if getattr(error, "code", 500) == 500:
            db.session.rollback()
        return render_template("errors/error.html", error=error), getattr(error, "code", 500)

    from .cli import register_commands
    register_commands(app)
    return app
