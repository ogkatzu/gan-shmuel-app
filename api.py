from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import json
from datetime import datetime
from sqlalchemy import text

from auxillary_functions import transaction_to_dict, create_session_id, create_transaction_from_data_and_session_id, insert_transaction, in_json_and_extras_to_transaciotn

def insert_transaction(new_transaction, exists: bool):
    if exists:
        # Fetch and update the existing object
        tx = Transaction.query.get(new_transaction.id)
        tx.bruto = new_transaction.bruto
    else:
        db.session.add(new_transaction)

    db.session.commit()

class truck_direction():

    def truck_in(data: json):
        session_id = create_session_id(data['datetime'])
        already_exists = False
        if data['prev_record']:
            if data['prev_record']['directiom'] == 'in':
                if not data['force']:
                    return 400, 'Bad Request'
                elif data['prev_record']['truck'] != data['truck']:
                        return 400, 'Bad Request' # better text
                else:
                    session_id = data['prev_record']['session_id']
                    already_exists = True
        new_transaction = create_transaction_from_data_and_session_id(data=data, session_id=session_id)
        insert_transaction(new_transaction=new_transaction, exists=already_exists)
        ret_json = {"id": new_transaction.id, "truck": new_transaction.truck, "bruto": new_transaction.bruto}
        return ret_json
            

    def truck_out(data: json):
        if data['prev_record']['directiom'] == 'out':
            if not data['force']:
                return 400, 'Bad Request'
            else:
                if data['prev_record']['truck'] != data['truck']:
                    return 400, 'Bad Request' # better text
        entrance = data['prev_record']
        bruto = entrance['bruto']
        truck_tara = data['truckTara']
        containers_tara = 0
        container_ids = entrance['containers']
        containers = db.session.query(Container).filter(Container.container_id.in_(container_ids)).all()
        for container in containers:
            if isinstance(container.weight, int) and container.weight > 0:
                containers_tara += container.weight
            else:
                containers_tara = 'NA'
                break
        neto = bruto - truck_tara - containers_tara
        new_transaction = in_json_and_extras_to_transaciotn(in_json=entrance, truck_tara=truck_tara, neto=neto, exact_time=data['datetime'])
        db.session.add(new_transaction)
        ret = {"id": new_transaction.id, "truck": new_transaction.truck, "bruto": new_transaction.bruto, "truckTara": new_transaction.truckTara, "neto": new_transaction.neto}
        return ret



    def truck_none(data: json):
        pass


app = Flask(__name__, template_folder='templates')
# enviromental/global vars go here
user = os.environ.get("MYSQL_USER")
password = os.environ.get("MYSQL_PASSWORD")
host = os.environ.get("MYSQL_HOST")
db = os.environ.get("MYSQL_DATABASE")
#set db uri from environment
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}/{db}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
_truck_direction = truck_direction
direction_handler = {'in': _truck_direction.truck_in, 'out': _truck_direction.truck_out, 'none': _truck_direction.truck_none}

db = SQLAlchemy(app)

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
    session_id = db.Column(db.Integer)


@app.route('/weight', methods=['GET'])
def get_weight():
    return "some value"
    
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

@app.route('/weight', methods=['POST'])
def post_weight(self):
    data = request.json()
    prev_record = db.session.query(Transaction).filter(Transaction.truck == data['truck']).order_by(Transaction.datetime.desc()).first()
    if prev_record:
        data['prev_record'] = transaction_to_dict(prev_record)
    if data['unit'] == 'lb' and isinstance(data['weight'], int) :
        weight_in_kg = int(data['weight'] /  2.205)
        data['unit'] = 'kg'
        data['weight'] = weight_in_kg
    
    ret = self.direction_handler[data['direction']](data)

  

    # -direction=in/out/none (none could be used, for example, when weighing a standalone container)
    # - truck=<license> (If weighing a truck. Otherwise "na")
    # - containers=str1,str2,... comma delimited list of container ids
    # - weight=<int>
    # - unit=kg/lbs {precision is ~5kg, so dropping decimal is a non-issue}
    # - force=true/false { see logic below }
    # - produce=<str> {id of produce, e.g. "orange", "tomato", ... OR "na" if empty}
    # Records data and server date-time and returns a json object with a unique weight.
    # Note that "in" & "none" will generate a new session id, and "out" will return session id of previous "in" for the truck.
    # "in" followed by "in" OR "out" followed by "out":
    # - if force=false will generate an error
    # - if force=true will over-write previous weigh of same truck
    # "out" without an "in" will generate error
    # "none" after "in" will generate error
    # Return value on success is:
    # { "id": <str>,
    #   "truck": <license> or "na",
    #   "bruto": <int>,
    #   ONLY for OUT:
    #   "truckTara": <int>,
    #   "neto": <int> or "na" // na if some of containers have unknown tara
    # }    
    


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)



