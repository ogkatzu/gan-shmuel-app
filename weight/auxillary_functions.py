from datetime import datetime
import csv
from sqlalchemy import text, or_, and_
import sys
import json
from flask import jsonify

from classes_db import Container, Transaction, db

def id_exists(_id):
    already_exists = db.session.query(Transaction).filter(Transaction.id==_id).first()
    ret = False
    if already_exists is not None:
        ret = True   
    return ret

def in_json_and_extras_to_transaciotn(in_json: json, truck_tara, neto, exact_time, id):
    new_transaction = Transaction()
    new_transaction.id = id
    new_transaction.bruto = in_json['bruto']
    new_transaction.containers = json.dumps(in_json['containers'])
    new_transaction.datetime = exact_time
    new_transaction.direction = 'out'
    new_transaction.produce = in_json['produce']
    new_transaction.truck = in_json['truck']
    new_transaction.session_id = in_json['session_id']
    new_transaction.neto = neto
    new_transaction. truckTara = truck_tara
    return new_transaction

def handle_json_in_file(filepath, added):
    with open(filepath) as jsonfile:
                    data = json.load(jsonfile)
                    if not isinstance(data, list):
                        return jsonify({'error': 'JSON format must be a list'}), 400
                    for item in data:
                        cid = item.get('id')
                        weight = item.get('weight')
                        unit = item.get('unit', '').lower()
                        if not cid or weight is None or not unit:
                            continue
                        try:
                            weight = float(weight)
                        except ValueError:
                            continue  # Skip invalid weights
                        existing = Container.query.get(cid)
                        if existing:
                            existing.weight = weight
                            existing.unit = unit
                        else:
                            new = Container(container_id=cid, weight=weight, unit=unit)
                            db.session.add(new)
                        added += 1
    return added

def handle_csv_in_file(filepath, added):
    with open(filepath, newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    headers = next(reader, None)  
                    if not headers or len(headers) < 2:
                        return jsonify({'error': 'Invalid CSV headers'}), 400
                    unit = headers[1].lower()  
                    for row in reader:
                        if len(row) < 2:
                            continue  # Skip malformed rows
                        cid = row[0].strip()
                        try:
                            weight = float(row[1])
                        except ValueError:
                            continue  # Skip rows with invalid weight
                        if not cid:
                            continue  # Skip empty container ID
                        existing = Container.query.get(cid)
                        if existing:
                            existing.weight = weight
                            existing.unit = unit
                        else:
                            new = Container(container_id=cid, weight=weight, unit=unit)
                            db.session.add(new)
                        added += 1
    return added

def get_item_data(date_from, date_to, id):
    default_from = datetime.now().replace(day=1, hour=00, minute=00, second=00, microsecond=00)
    default_to = datetime.now()

    final_from = parse_date(date_string=date_from, default_date=default_from)
    final_to = parse_date(date_string=date_to, default_date=default_to)

    tara, transctions = find_transactions_by_id_and_time(id=id, start_time=final_from, end_time=final_to)
    if transctions is None:
        transctions = find_transactions_by_container(container_id=id, start_time=final_from, end_time=final_to)
        container: Container = db.session.query(Container).filter(Container.container_id == id).first()
        if container:
            unit, tara = lb_to_kg(unit=container.unit, weight=container.weight)
    
    if transctions is None:
        return f"ID {id} not found in requested time range.", 404
    
    session_ids = []
    
    for transaction in transctions:
        session_ids.append(transaction.session_id)
    
    list(set(session_ids))
    for _item in session_ids:
        if _item is None:
            session_ids.remove(_item)
    
    ret = {"id": id, "tara": tara if tara else 'na', 'sessions': session_ids, 'unit': 'kg'}
    return ret

def find_transactions_by_id_and_time(id, start_time, end_time):
    transactions = db.session.query(Transaction).filter(
        and_(
            Transaction.datetime >= start_time,
            Transaction.datetime <= end_time,
            or_(
                Transaction.truck == id,
            )
        )
    ).all()

    if not transactions:
        return None, None

    latest_out_tara = None
    for tx in sorted(transactions, key=lambda t: t.datetime, reverse=True):
        if tx.direction == "out" and isinstance(tx.truckTara, int):
            latest_out_tara = tx.truckTara
            break

    return latest_out_tara, transactions

def find_transactions_by_container(container_id, start_time, end_time):
    transactions = db.session.query(Transaction).filter(
        and_(
            Transaction.datetime >= start_time,
            Transaction.datetime <= end_time,
        )
    ).all()

    matching = []
    for tx in transactions:
        try:
            container_list = json.loads(tx.containers)
            if container_id in container_list:
                matching.append(tx)
        except (TypeError, json.JSONDecodeError):
            continue  # skip if containers field is invalid

    return matching if matching else None

def transaction_to_dict(transaction):
    if not isinstance(transaction.datetime, datetime):
        transaction.datetime = datetime.strptime(transaction.datetime, '%Y%m%d%H%M%S')
    return {
        'id': transaction.id,           
        'datetime': transaction.datetime.isoformat() if transaction.datetime else None,
        'direction': transaction.direction,
        'truck': transaction.truck,
        'containers': json.loads(transaction.containers) if transaction.containers else [],
        'bruto': transaction.bruto,
        'truckTara': transaction.truckTara,
        'neto': transaction.neto,
        'produce': transaction.produce,
        'session_id': transaction.session_id,
    }

def create_session_id(transaction_time):
    time_as_obj = datetime.fromisoformat(transaction_time)
    return int(time_as_obj.timestamp())

def create_transaction_from_data_and_session_id(data: json, session_id: int):
    new_transaction = Transaction()
    new_transaction.id = new_transaction.session_id = session_id
    new_transaction.bruto = data['weight']
    new_transaction.containers = json.dumps(data['containers'])
    new_transaction.datetime = data['datetime']
    new_transaction.direction = data['direction']
    new_transaction.produce = data['produce']
    new_transaction.truck = data['truck']
    new_transaction.truckTara = None
    new_transaction.neto = None
    return new_transaction


def insert_transaction(new_transaction, exists: bool):
    if exists:
        tx = Transaction.query.get(new_transaction.id)
        tx.bruto = new_transaction.bruto
    else:
        db.session.add(new_transaction)
    db.session.commit()

def print_debug(msg: str):
    print(msg, file=sys.stdout, flush=True)

def lb_to_kg(unit, weight):
    if unit == 'lb' and isinstance(weight, int) :
        weight_in_kg = int(weight /  2.205)
        unit = 'kg'
        weight = weight_in_kg
    return unit, weight


# Function to convert a date string to the expected format  ('yyyymmddhhmmss') ==>  ('20250518143000') in object datetime
def parse_date(date_string, default_date=None):
    if not date_string: # check if date_string is empty
        return default_date
    try:
        return datetime.strptime(date_string, '%Y%m%d%H%M%S')
    except ValueError:
        print(f"Invalid date format: {date_string}")
        return default_date
   

# Function to get transactions in a time range
def get_transactions_by_time_range(db_session,Transaction_model,from_time, to_time, directions=None):  
    
    # Default values
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Convert in datetime  |  if invalid use default
    from_datetime = parse_date(from_time, today_start)
    to_datetime = parse_date(to_time, now)
    

    # Prepare directions
    if not directions:   #If no direction is specified use all
        directions = "in,out,none"
    direction_list = directions.split(',')
    
    try:  # try/except block to handle database errors

         
        # Query transactions matching the criteria
        query = db_session.query(Transaction_model).filter(
            Transaction_model.datetime.between(from_datetime, to_datetime),
            Transaction_model.direction.in_(direction_list)
        ).all()

        #print_debug("PRINT QUERY")
        #print_debug(query)

        
        # Format results
        result = []
        for t in query:
            containers_list = []
            if t.containers and t.containers != 'na':  # na if some of containers have unknown tara
                containers_list = t.containers.split(',')
            
            transaction_obj = {
                "id": str(t.session_id),
                "direction": t.direction,  
                "bruto": t.bruto,          
                "neto": t.neto if t.neto is not None else "na",  
                "produce": t.produce,      
                "containers": containers_list
            }
            result.append(transaction_obj)   # [
                                             #     {"id": "101", ..., "containers": ["C001", "C002"]},
                                             #     {"id": "102", ..., "containers": ["C003"]},
                                             #     {"id": "103", ..., "containers": []}
                                             # ] 

        return result
        

    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    
class truck_direction():


    def truck_in(data: json):
        session_id = None
        already_exists = False
        try:
            prev_record = json.loads(data['prev_record'])
            if prev_record['direction'] == 'in':
                if not data['force']:
                    return 'Two in in a row without an out.', 400
                elif prev_record['truck'] != data['truck']:
                        return 'Bad Request', 400 # better text, unsure can happen
                else:
                    session_id = prev_record['session_id']
                    already_exists = True
        except KeyError:
            session_id = create_session_id(data['datetime'])
            if id_exists(session_id):
                return "ID already exists, can't have two entries at the same second.", 400
        data['unit'], data['weight'] = lb_to_kg(data['unit'], data['weight'])
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
        neto = 0
        container_ids = entrance['containers']
        containers = db.session.query(Container).filter(Container.container_id.in_(container_ids)).all()
        for container in containers:
            if isinstance(container.weight, int) and container.weight > 0:
                container.unit, container.weight = lb_to_kg(container.unit, container.weight)
                containers_tara += container.weight
            else:
                containers_tara = 'na'
                neto = 'na'
                break
        if neto == 0:
            neto = bruto - truck_tara - containers_tara
        _id = create_session_id(data['datetime']) #this is also the id - not session id - for out
        if id_exists(_id):
            return "ID already exists, can't have two entries at the same second.", 400
        new_transaction = in_json_and_extras_to_transaciotn(in_json=entrance, truck_tara=truck_tara, neto=neto, exact_time=data['datetime'], id=_id)
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
        unit, container_tara = lb_to_kg(container.unit ,container.weight)
        new_tansaction.truckTara = container_tara #should this be the case?
        new_tansaction.containers = [container]
        new_tansaction.neto = new_tansaction.bruto - container_tara
        new_tansaction.id = new_tansaction.session_id = create_session_id(data['datetime'])
        if id_exists(new_tansaction.id):
            return "ID already exists, can't have two entries at the same second.", 400
        new_tansaction.direction = 'none'
        new_tansaction.produce = data['produce']
        new_tansaction.truck = 'na'
        new_tansaction.datetime = data['datetime']
        db.session.add(new_tansaction)
        db.session.commit()
        ret = {'id': new_tansaction.id, 'truck': new_tansaction.truck, 'bruto': new_tansaction.bruto, 'truckTara': new_tansaction.truckTara, 'neto': new_tansaction.neto}
        return ret, 200
    
truck_direction_handler = {'in': truck_direction.truck_in, 'out': truck_direction.truck_out, 'none': truck_direction.truck_none}
