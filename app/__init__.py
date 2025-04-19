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
        from app.models import User, Student, Admin, Subject, Mark, Attendance, Announcement, ChatHistory, Settings
        
        # Log database info for debugging
        app.logger.info(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        try:
            # Create all tables
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Error creating database tables: {str(e)}")
            
            # If there was an error creating tables, try to connect to the database
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                existing_tables = inspector.get_table_names()
                app.logger.info(f"Existing tables in database: {existing_tables}")
            except Exception as db_err:
                app.logger.error(f"Error inspecting database: {str(db_err)}")
    
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    return app
