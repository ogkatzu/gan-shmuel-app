import json
from api import Transaction

def in_json_and_extras_to_transaciotn(in_json: json, truck_tara, neto, exact_time):
    new_transaction = Transaction()
    new_transaction.id = create_session_id(exact_time)
    new_transaction.bruto = in_json['bruto']
    new_transaction.containers = in_json['containers']
    new_transaction.datetime = exact_time
    new_transaction.direction = 'out'
    new_transaction.produce = in_json['produce']
    new_transaction.truck = in_json['truck']
    new_transaction.session_id = in_json['session_id']
    new_transaction.neto = neto
    new_transaction. truckTara = truck_tara
    return new_transaction

def transaction_to_dict(transaction):
    return {
        "id": transaction.id,
        "datetime": transaction.datetime.isoformat() if transaction.datetime else None,
        "direction": transaction.direction,
        "truck": transaction.truck,
        "containers": transaction.containers,
        "bruto": transaction.bruto,
        "truckTara": transaction.truckTara,
        "neto": transaction.neto,
        "produce": transaction.produce,
        "session_id": transaction.session_id,
    }

def create_session_id(transaction_time):
    return int(transaction_time.strftime("%y%m%d%H%M%S"))

def create_transaction_from_data_and_session_id(data: json, session_id: int):
    new_transaction = Transaction()
    new_transaction.id = new_transaction.session_id = session_id
    new_transaction.bruto = data['bruto']
    new_transaction.containers = data['containers']
    new_transaction.datetime = data['datetime']
    new_transaction.direction = data['direction']
    new_transaction.produce = data['produce']
    new_transaction.truck = data['truck']
    return new_transaction



