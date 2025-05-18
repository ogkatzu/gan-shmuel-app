import json
from api import Transaction

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

def insert_transaction(new_transaction, exists: bool):
    if exists:
        # Fetch and update the existing object
        tx = Transaction.query.get(new_transaction.id)
        tx.bruto = new_transaction.bruto
    else:
        db.session.add(new_transaction)

    db.session.commit()



