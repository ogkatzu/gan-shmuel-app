from datetime import datetime
from sqlalchemy import text, or_, and_
import sys
   
def get_item_data(date_from, date_to, id):
    default_from = datetime.now().replace(day=1, hour=00, minute=00, second=00, microsecond=00)
    default_to = datetime.now()

    final_from = auxillary_functions.parse_date(date_string=date_from, default_date=default_from)
    final_to = auxillary_functions.parse_date(date_string=date_to, default_date=default_to)

    tara, transctions = find_transactions_by_id_and_time(id=id, start_time=final_from, end_time=final_to)
    if transctions is None:
        transctions = find_transactions_by_container(container_id=id, start_time=final_from, end_time=final_to)
        container: Container = db.session.query(Container).filter(Container.container_id == id).first()
        unit, tara = auxillary_functions.lb_to_kg(unit=container.unit, weight=container.weight)
    
    if transctions is None:
        return f"ID {id} not found in requested time range.", 404
    
    session_ids = []
    for transaction in transctions:
        session_ids.append(transaction.session_id)
    auxillary_functions.print_debug(f"len of sessions id list at first: {len(session_ids)}")
    auxillary_functions.print_debug(f"session id list is: {session_ids}")
    list(set(session_ids))
    auxillary_functions.print_debug(f"after set, list len is {len(session_ids)}")
    auxillary_functions.print_debug(f"after set, list is {session_ids}")
    for _item in session_ids:
        if _item is None:
            session_ids.remove(_item)
    auxillary_functions.print_debug(f"after None removal, list len is {len(session_ids)}")
    auxillary_functions.print_debug(f"after None remova, list is {session_ids}")
    
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
                "id": str(t.id),
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
    
    