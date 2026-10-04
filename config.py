import os

# Project root path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database settings
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Secret key for sessions (for local use only)
SECRET_KEY = 'iPrent-Helpdisk-Local-Secret-Key-2024'

