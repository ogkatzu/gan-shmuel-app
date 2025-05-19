from flask import Flask, request, jsonify,render_template
from flask_sqlalchemy import SQLAlchemy
import pymysql
import os
from datetime import datetime
from sqlalchemy import text
import auxillary_functions 
import csv ,json

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
    transactions = auxillary_functions.get_transactions_by_time_range(db.session,Transaction,from_time, to_time, filter_directions)

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


@app.route("/")
def index():
    return render_template("index.html")

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
        return jsonify("OK"), 200

@app.route("/batch-weight", methods=["POST"])
def batch_weight():
    # Debug print to check received JSON payload
    print('Received JSON:', request.get_json())
    # Extract ‘file’ parameter from the JSON request body
    filename = request.json.get('file')
    if not filename:
        return jsonify({'error': 'Missing file parameter'}), 400
    # Construct the full file path
    filepath = os.path.join('in', filename)
    # Check if the file exists
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 400
    added = 0  # Counter for how many records were added/updated
    try:
        # Handle CSV file
        if filename.endswith('.csv'):
            with open(filepath, newline='') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, None)  # Read the header row
                if not headers or len(headers) < 2:
                    return jsonify({'error': 'Invalid CSV headers'}), 400
                unit = headers[1].lower()  # Get unit from header
                for row in reader:
                    if len(row) < 2:
                        continue  # Skip malformed rows
                    cid = row[0].strip()
                    try:
                        w = float(row[1])
                    except ValueError:
                        continue  # Skip rows with invalid weight
                    if not cid:
                        continue  # Skip empty container ID
                    # Check if container already exists
                    existing = Container.query.get(cid)
                    if existing:
                        # Update existing container
                        existing.weight = w
                        existing.unit = unit
                    else:
                        # Create new container
                        new = Container(container_id=cid, weight=w, unit=unit)
                        db.session.add(new)
                    added += 1
        # Handle JSON file
        elif filename.endswith('.json'):
            with open(filepath) as jsonfile:
                data = json.load(jsonfile)
                if not isinstance(data, list):
                    return jsonify({'error': 'JSON format must be a list'}), 400
                for item in data:
                    cid = item.get('id')
                    w = item.get('weight')
                    unit = item.get('unit', '').lower()
                    # Validate required fields
                    if not cid or w is None or not unit:
                        continue
                    try:
                        w = float(w)
                    except ValueError:
                        continue  # Skip invalid weights
                    # Check if container already exists
                    existing = Container.query.get(cid)
                    if existing:
                        # Update existing container
                        existing.weight = w
                        existing.unit = unit
                    else:
                        # Create new container
                        new = Container(container_id=cid, weight=w, unit=unit)
                        db.session.add(new)
                    added += 1
        # Unsupported file type
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        # Commit all changes to the database
        db.session.commit()
        return jsonify({'status': 'ok', 'added': added})
    # Catch and return any unexpected errors
    except Exception as e:
        return jsonify({'error': 'An error occurred', 'details': str(e)}), 500

@app.route("/containers", methods=["GET"])
def get_containers():
    containers = Container.query.all()
    containers_list = [
        {
            "container_id": c.container_id,
            "weight": c.weight,
            "unit": c.unit
        }
        for c in containers
    ]
    return jsonify({
        "count": len(containers_list),
        "containers": containers_list
    })


@app.route("/transactions", methods=["GET"])
def get_transactions():
    transactions = Transaction.query.all()
    transactions_list = [
        {
            "id": t.id,
            "datetime": t.datetime,
            "direction": t.direction,
            "truck": t.truck,
            "containers": t.containers,
            "bruto": t.bruto,
            "truckTara": t.truckTara,
            "neto": t.neto,
            "produce": t.produce
        }
        for t in transactions
    ]
    return jsonify({
        "count": len(transactions_list),
        "transactions": transactions_list
    })






if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True,host="0.0.0.0", port=5000)