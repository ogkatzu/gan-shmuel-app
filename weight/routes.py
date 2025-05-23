import json
from flask import Flask, request, jsonify,render_template
import os
from sqlalchemy import text
import csv

from classes_db import Container, Transaction, db
import auxillary_functions
from auxillary_functions import print_debug

def register_routes(app):
   
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route('/session/<int:session_id>', methods=['GET'])
    def get_session(session_id):
        auxillary_functions.print_debug("Entered route func")
        tx_list = Transaction.query.filter_by(session_id=session_id).all()
        if not tx_list:
            return jsonify({'error': 'Not found'}), 404
        tx = next((t for t in tx_list if t.direction == 'out'), tx_list[0])
        result = {
            'id': tx.id,
            'truck': tx.truck,
            'bruto': tx.bruto,
            'produce': tx.produce
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
                prev_record = auxillary_functions.transaction_to_dict(prev_record)
                prev_record = json.dumps(prev_record)
                data['prev_record'] = prev_record
        data['unit'], data['weight'] = auxillary_functions.lb_to_kg(data.get('unit'), data.get('weight'))
        
        ret = auxillary_functions.truck_direction_handler[data['direction']](data)
        return ret

    @app.route("/batch-weight", methods=["POST"])
    def batch_weight():
        filename = request.json.get('file')
        if not filename:
            return jsonify({'error': 'Missing file parameter'}), 400
        filepath = os.path.join('in', filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 400
        added = 0 
        invalid_weight_field = 0
        try:
            if filename.endswith('.csv'):
                added, invalid_weight_field = auxillary_functions.handle_csv_in_file(filepath, added, invalid_weight_field)
            elif filename.endswith('.json'):
                added, invalid_weight_field = auxillary_functions.handle_json_in_file(filepath, added, invalid_weight_field)
            else:
                return jsonify({'error': 'Unsupported file format'}), 400
            db.session.commit()
            msg =  f"Added {added}."
            msg_invalid = f"Added {added}, didn't upload {invalid_weight_field} due to invalid weight field."
            return jsonify({'status': 'ok', 'added': msg if invalid_weight_field == 0 else msg_invalid })
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
        ids = set()  
        for tx in unknown:  
            try:
                if tx.containers and tx.containers != "":
                    for cid in json.loads(tx.containers):  
                        if (cid and not Container.query.get(cid)) or not auxillary_functions.container_has_weight_in_table(cid):
                            ids.add(cid)
            except json.JSONDecodeError:
                print(f"Invalid JSON in tx.containers (tx id {tx.id}):", tx.containers)
                continue
  
        return jsonify(list(ids))  
    
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
                "produce": t.produce,
                "session_id": t.session_id

            }
            for t in transactions
        ]
        return jsonify({
            "count": len(transactions_list),
            "transactions": transactions_list
        })


    @app.route('/weight', methods=['GET'])
    def get_weight():
        from_time = request.args.get('from')
        to_time = request.args.get('to')
        filter_directions = request.args.get('filter')

        transactions = auxillary_functions.get_transactions_by_time_range(db.session,Transaction,from_time, to_time, filter_directions)

        return jsonify(transactions)

    @app.route('/item/<id>', methods=['GET'])
    def get_item(id):
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        
        item_data = auxillary_functions.get_item_data(date_from=from_date, date_to=to_date, id=id)
        
        if item_data is None:
            return jsonify({"error": "Item not found within time range."}), 404
        
        return jsonify(item_data)


