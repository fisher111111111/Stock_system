from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = '8a758850e'  # To prevent attacks.

# Database connection.
DRIVER_NAME = 'ODBC Driver 17 for SQL Server'
SERVER_NAME = 'localhost\\SQLEXPRESS'   # или 'WIN-VIK827QHRC6\\SQLEXPRESS'
DATABASE_NAME = 'stock_db'
DB_USER = 'user'
DB_PASSWORD = 'password1'

app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{SERVER_NAME}/{DATABASE_NAME}?driver={DRIVER_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # This prevents warnings.
#app.config['SQLALCHEMY_ECHO'] = True  # For SQL debugging.

db = SQLAlchemy(model_class=Base)
db.init_app(app)

from . import routes