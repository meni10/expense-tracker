# In app/__init__.py

import os
from flask import Flask, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from user_agents import parse
import datetime

# --- Create the db and migrate instances at the module level ---
# This is the standard pattern. They are created but not yet connected to an app.
db = SQLAlchemy()
migrate = Migrate(render_as_batch=True)


def create_app():
    """The Application Factory."""
    app = Flask(__name__)

    # --- Configuration ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "NOTHING_IS_SECRET")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI", "sqlite:///master.sqlite3")
    app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=7)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- Initialize extensions with the app ---
    db.init_app(app)
    migrate.init_app(app, db)

    @app.after_request
    def after_request_(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    # --- Import Blueprints inside the function ---
    from .views.auth import auth
    from .views.home import home
    from .views.settings import settings
    from .views.admin import admin
    blueprints = [auth, home, settings, admin]

    # --- Import models and commands INSIDE the function ---
    # This is the key to breaking the circular import.
    from .db import VisitorStats
    from .commands import create_admin_user

    # --- Register the before_request function ---
    @app.before_request
    def app_before_data():
        if request.endpoint != "static":
            user_agent = parse(request.user_agent.string)
            browser = user_agent.browser.family
            device = user_agent.get_device()
            operating_system = user_agent.get_os()
            bot = user_agent.is_bot

            stat = VisitorStats(
                browser=browser,
                device=device,
                operating_system=operating_system,
                is_bot=bot
            )
            # Now 'db' is the correct SQLAlchemy object, so this will work
            db.session.add(stat)
            db.session.commit()

    # --- Register Blueprints ---
    for bp in blueprints:
        app.register_blueprint(bp)

    # --- Register CLI Commands ---
    app.cli.add_command(create_admin_user)

    return app