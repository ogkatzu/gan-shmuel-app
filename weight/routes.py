import json
from flask import request, jsonify
from flask import Flask, request, jsonify,render_template
import os
from sqlalchemy import text
import csv

from classes_db import db
import auxillary_functions


def register_routes(app):
   
    @app.route("/")
    def index():
        return render_template("index.html")
    

    # if session has both in and out - return only from the out
    @app.route('/session/<int:session_id>', methods=['GET'])
    def get_session(session_id):
        tx = Transaction.query.get(session_id).all()
        if not tx:
            return jsonify({'error': 'Not found'}), 404
        result = {
            'id': tx.id,
            'truck': tx.truck,
            'bruto': tx.bruto
        }
        if tx.direction == 'out':
            result['truckTara'] = tx.truckTara
            result['neto'] = tx.neto if tx.neto is not None else 'na'
        return jsonify(result)


@app.route('/db-check', methods=['GET'])
def db_check():
    try:
        db.session.execute(text('SELECT 1'))
        return {'db': 'connected'}, 200
    except Exception as e:
        return {'db': 'error', 'detail': str(e)}, 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"}), 200

@app.route('/weight', methods=['POST'])
def post_weight():
    data = request.get_json()
    if not data['direction'] == 'none':
        prev_record = db.session.query(Transaction).filter(Transaction.truck == data.get('truck')).order_by(Transaction.datetime.desc()).first()
        if prev_record:
            prev_record = transaction_to_dict(prev_record)
            prev_record = json.dumps(prev_record)
            data['prev_record'] = prev_record
    data['unit'], data['weight'] = auxillary_functions.lb_to_kg(data.get('unit'), data.get('weight'))
    
    ret = direction_handler[data['direction']](data)
    return ret


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

# only for show containers db in html
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
    
@app.route("/unknown", methods=["GET"])  
def get_unknown():
    unknown = Transaction.query.all()  
    # Retrieves all records from the Transaction table in the database
    ids = set()  
    # Initializes an empty set to store container IDs that are considered "unknown" (i.e., not found in the Container table).
    # A set is used to automatically avoid duplicates.
    for tx in unknown:  
        # Iterates over all transactions
        if tx.containers:  
            # Checks if the transaction has any container IDs listed
            for cid in json.loads(tx.containers):  
                if cid and not Container.query.get(cid):  
                    # Checks if the ID is non-empty AND does NOT exist in the Container table
                    ids.add(cid)  
                    # Adds the container ID to the set of unknown containers
  
    return jsonify(list(ids))  
    # Converts the set of unknown IDs into a list and returns it as a JSON response

# only for show transactions db in html
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

    @app.route('/item/<id>', methods=['GET'])
    def get_item(id):
        
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        
        item_data = get_item_data(date_from=from_date, date_to=to_date, id=id)
        
        if item_data is None:
            return jsonify({"error": "Item not found"}), 404
        
        return jsonify(item_data), 200




class truck_direction():

    def truck_in(data: json):
        session_id = None
        already_exists = False
        try:
            prev_record = json.loads(data['prev_record'])
            if prev_record['direction'] == 'in':
                if not data['force']:
                    return 'Bad Request', 400
                elif prev_record['truck'] != data['truck']:
                        return 'Bad Request', 400 # better text, unsure can happen
                else:
                    session_id = prev_record['session_id']
                    already_exists = True
        except KeyError:
            session_id = create_session_id(data['datetime'])
        data['unit'], data['weight'] = auxillary_functions.lb_to_kg(data['unit'], data['weight'])
        data['bruto'] = data['weight']
        new_transaction = create_transaction_from_data_and_session_id(data=data, session_id=session_id)
        insert_transaction(new_transaction=new_transaction, exists=already_exists)
        ret_json = {'id': new_transaction.id, 'truck': new_transaction.truck, 'bruto': new_transaction.bruto}
        return ret_json, 200
            

    def truck_out(data: json):
        try:
            entrance = json.loads(data['prev_record'])
        except KeyError:
            return "No in for this out", 400
        if entrance['direction'] == 'out':
            if not data['force']:
                    return 'Two outs is a row without force', 400
            elif entrance['truck'] != data['truck']:
                return 'Bad Request', 400 # better text
        bruto = entrance['bruto']
        truck_tara = data['weight']
        containers_tara = 0
        container_ids = entrance['containers']
        containers = db.session.query(Container).filter(Container.container_id.in_(container_ids)).all()
        for container in containers:
            if isinstance(container.weight, int) and container.weight > 0:
                container.unit, container.weight = auxillary_functions.lb_to_kg(container.unit, container.weight)
                containers_tara += container.weight
            else:
                containers_tara = 'NA'
                break
        neto = bruto - truck_tara - containers_tara
        id = create_session_id(data['datetime']) #this is also the id - not session id - for out
        new_transaction = in_json_and_extras_to_transaciotn(in_json=entrance, truck_tara=truck_tara, neto=neto, exact_time=data['datetime'], id=id)
        db.session.add(new_transaction)
        db.session.commit()
        ret = {'id': new_transaction.id, 'truck': new_transaction.truck, 'bruto': new_transaction.bruto, 'truckTara': new_transaction.truckTara, 'neto': new_transaction.neto}
        return ret, 200
    
    def truck_none(data: json):
                # none after in should generate an error. Why? What does it mean?
        new_tansaction = Transaction()
        new_tansaction.bruto = data['weight']
        container_id = data['containers'][0] # אthis implementation of none only accepts single container
        container = containers = db.session.query(Container).filter_by(container_id=container_id).first()
        unit, container_tara = auxillary_functions.lb_to_kg(container.unit ,container.weight)
        new_tansaction.truckTara = container_tara #should this be the case?
        new_tansaction.containers = [container]
        new_tansaction.neto = new_tansaction.bruto - container_tara
        new_tansaction.id = new_tansaction.session_id = create_session_id(data['datetime'])
        new_tansaction.direction = 'none'
        new_tansaction.produce = data['produce']
        new_tansaction.truck = 'na'
        new_tansaction.datetime = data['datetime']
        db.session.add(new_tansaction)
        db.session.commit()
        ret = {'id': new_tansaction.id, 'truck': new_tansaction.truck, 'bruto': new_tansaction.bruto, 'truckTara': new_tansaction.truckTara, 'neto': new_tansaction.neto}
        return ret, 200
    

