import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from sqlalchemy.orm import DeclarativeBase

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Initialize extensions
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_pyfile('config.py')
    app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key")
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    mail.init_app(app)
    jwt.init_app(app)
    
    # Import and register blueprints
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    
    # Create database tables
    with app.app_context():
        from app.models import User, Student, Admin, Attendance, Announcement
        db.create_all()
    
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    return app
