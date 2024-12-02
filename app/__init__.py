import os
from flask import Flask
from flask_wtf import CSRFProtect
from flask_admin import Admin
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_principal import Principal

admin = Admin()
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
principal = Principal()
csrf_protect = CSRFProtect()


def create_app():
    app = Flask(__name__)

    from app.main import main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/main')

    from app.auth import auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from app.lab import lab_blueprint
    app.register_blueprint(lab_blueprint, url_prefix='/lab')

    from app.doc import doc_blueprint
    app.register_blueprint(doc_blueprint, url_prefix='/doc')

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('://', 'ql://', 1)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

    db.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    login_manager.init_app(app)
    principal.init_app(app)
    csrf_protect.init_app(app)

    return app
