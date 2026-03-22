from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import os
from dotenv import load_dotenv

load_dotenv()

class Base(DeclarativeBase):
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = '8a758850e'  # To prevent attacks.  

# Database connection.
DRIVER_NAME = os.getenv('DRIVER_NAME')
SERVER_NAME = os.getenv('SERVER_NAME')   # или 'WIN-VIK827QHRC6\\SQLEXPRESS'
DATABASE_NAME = os.getenv('DATABASE_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')


app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{SERVER_NAME}/{DATABASE_NAME}?driver={DRIVER_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # This prevents warnings.
#app.config['SQLALCHEMY_ECHO'] = True  # For SQL debugging.

db = SQLAlchemy(model_class=Base)
db.init_app(app)

from . import routes