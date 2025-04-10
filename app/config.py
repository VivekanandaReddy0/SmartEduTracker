import os

# Flask Configuration
DEBUG = True
TESTING = False

# Database
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Handle special case for postgres:// URLs
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
else:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///smartedu.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20
}

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour

# Mail Configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.environ.get('EMAIL_USER')
MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
MAIL_DEFAULT_SENDER = os.environ.get('EMAIL_USER')

# Google Sheets Configuration
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')

# AI Chatbot Configuration
AI_API_KEY = os.environ.get('AI_API_KEY')
AI_API_URL = 'https://api.openai.com/v1/chat/completions'
