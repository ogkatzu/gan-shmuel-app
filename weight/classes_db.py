from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, or_, and_
from datetime import datetime

db = SQLAlchemy()

class Container(db.Model):
    __tablename__ = 'containers_registered'
    container_id = db.Column(db.String(15), primary_key=True)
    weight = db.Column(db.Integer)
    unit = db.Column(db.String(10))

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(db.DateTime, default=datetime)
    direction = db.Column(db.String(10))
    truck = db.Column(db.String(50))
    containers = db.Column(db.String(10000))
    bruto = db.Column(db.Integer)
    truckTara = db.Column(db.Integer)
    neto = db.Column(db.Integer)
    produce = db.Column(db.String(50))
    session_id = db.Column(db.Integer)