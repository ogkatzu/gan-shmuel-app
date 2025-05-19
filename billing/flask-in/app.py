import os
from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import pandas as pd
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)


def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "billdb")
    )


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "OK"}), 200
    except Error:
        return jsonify({"status": "Failure"}), 500


@app.route("/provider", methods=["POST"])
def create_provider():
    try:
        data = request.get_json()
        name = data.get("name")
        if not name:
            return jsonify({"error": "Missing 'name' field"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Provider (name) VALUES (%s)", (name,))
        conn.commit()
        provider_id = cursor.lastrowid
        conn.close()

        return jsonify({"provider_id": provider_id}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route("/provider/<int:provider_id>", methods=["PUT"])
def update_provider(provider_id):
    try:
        data = request.get_json()
        name = data.get("name")
        if not name:
            return jsonify({"error": "Missing 'name' field"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Provider SET name = %s WHERE id = %s", (name, provider_id))
        conn.commit()

        if cursor.rowcount == 0:
            # Check if the provider exists (but value is unchanged)
            cursor.execute("SELECT 1 FROM Provider WHERE id = %s", (provider_id,))
            if cursor.fetchone() is None:
                conn.close()
                return jsonify({"error": f"No provider found with id {provider_id}"}), 404

        conn.close()
        return jsonify({"updated_name": name}), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route('/post_truck', methods=['POST'])
def post_truck():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Missing or invalid JSON'}), 400

    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list of truck items'}), 400

    for entry in data:
        if not all(k in entry for k in ['Product', 'Rate', 'Scope']):
            return jsonify({'error': f'Missing keys in entry: {entry}'}), 400

    return jsonify({
        'message': 'Truck data received successfully',
        'entries_received': len(data)
    }), 200


@app.route('/get_truck', methods=['GET'])
def get_truck():
    product = request.args.get('Product')
    rate = request.args.get('Rate')
    scope = request.args.get('Scope')

    return jsonify({
        'Product': product,
        'Rate': rate,
        'Scope': scope,
        'message': 'GET request received'
    })


@app.route('/get_truck/<truck_id>', methods=['GET'])
def get_truck_id(truck_id):
    # You can still get optional query params if needed
    product = request.args.get('Product')
    rate = request.args.get('Rate')
    scope = request.args.get('Scope')

    return jsonify({
        'TruckID': truck_id,
        'Product': product,
        'Rate': rate,
        'Scope': scope,
        'message': f'GET request received for truck {truck_id}'
    })


@app.route("/truck", methods=["POST"])
def register_truck():
    try:
        data = request.json
        truck_id = data.get("id")
        provider_id = data.get("provider")

        # Check for required fields in request
        if not truck_id or not provider_id:
            return jsonify({"error": "Missing 'id' or 'provider' field"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if provider exists
        cursor.execute("SELECT 1 FROM Provider WHERE id = %s", (provider_id,))
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({"error": f"Provider ID {provider_id} does not exist"}), 404

        # Check if truck ID already exists
        cursor.execute("SELECT 1 FROM Trucks WHERE id = %s", (truck_id,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": f"Truck with ID {truck_id} already exists"}), 409

        # Insert new truck
        cursor.execute("INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", (truck_id, provider_id))
        conn.commit()
        conn.close()

        return jsonify({"status": "registered"}), 201

    except Error as e:
        return jsonify({"error": str(e)}), 500

    except Error as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
