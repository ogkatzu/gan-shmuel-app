from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import pymysql
import os
from datetime import datetime
from sqlalchemy import text
from auxillary_functions import get_transactions_by_time_range

app = Flask(__name__, template_folder='templates')
# enviromental/global vars go here
user = os.environ.get("MYSQL_USER")
password = os.environ.get("MYSQL_PASSWORD")
host = os.environ.get("MYSQL_HOST")
db = os.environ.get("MYSQL_DATABASE")
#set db uri from environment
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}/{db}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
@app.route('/weight', methods=['GET'])
def get_weight():
    # get request parameters
    from_time = request.args.get('from')
    to_time = request.args.get('to')
    filter_directions = request.args.get('filter')

    #Call auxiliary function to get data
    transactions = get_transactions_by_time_range(from_time, to_time, filter_directions)

    #Return results in JSON format
    return jsonify(transactions)



#container db model
class Container(db.Model):
    __tablename__ = 'containers_registered'
    container_id = db.Column(db.String(15), primary_key=True)
    weight = db.Column(db.Integer)
    unit = db.Column(db.String(10))

#transaction db model
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    direction = db.Column(db.String(10))
    truck = db.Column(db.String(50))
    containers = db.Column(db.String(10000))
    bruto = db.Column(db.Integer)
    truckTara = db.Column(db.Integer)
    neto = db.Column(db.Integer)
    produce = db.Column(db.String(50))

    
@app.route('/weight', methods=['POST'])
def post_weight():
    return "some value"

@app.route("/session/<int:session_id>", methods=["GET"])
def get_session(session_id):
    tx = Transaction.query.get(session_id)
    if not tx:
        return jsonify({"error": "Not found"}), 404
    result = {
        "id": tx.id,
        "truck": tx.truck,
        "bruto": tx.bruto
    }
    if tx.direction == "out":
        result["truckTara"] = tx.truckTara
        result["neto"] = tx.neto if tx.neto is not None else "na"
    return jsonify(result)

@app.route("/db-check", methods=["GET"])
def db_check():
    try:
        db.session.execute(text('SELECT 1'))
        return {"db": "connected"}, 200
    except Exception as e:
        return {"db": "error", "detail": str(e)}, 500

@app.route("/health", methods=["GET"])
def health():
        return "OK", 200




if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
