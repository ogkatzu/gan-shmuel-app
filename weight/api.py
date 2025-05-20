from flask import Flask, request, jsonify,render_template
from flask_sqlalchemy import SQLAlchemy
import os
import json
from datetime import datetime
from sqlalchemy import text, or_, and_
import csv
import os

import auxillary_functions 
from classes_db import db
from routes import register_routes


def create_app():
    app = Flask(__name__, template_folder='templates')
    # enviromental/global vars go here
    user = os.environ.get('MYSQL_USER')
    password = os.environ.get('MYSQL_PASSWORD')
    host = os.environ.get('MYSQL_HOST')
    db = os.environ.get('MYSQL_DATABASE')
    #set db uri from environment
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}/{db}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    _truck_direction = truck_direction
    direction_handler = {'in': _truck_direction.truck_in, 'out': _truck_direction.truck_out, 'none': _truck_direction.truck_none}


    db.init_app(app)
    register_routes(app)
    with app.app_context():
        from classes_db import Container, Transaction 
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)

