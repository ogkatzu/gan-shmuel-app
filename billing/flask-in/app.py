import os
from flask import Flask, request, jsonify, send_file
import mysql.connector
from mysql.connector import Error
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
import openpyxl

app = Flask(__name__)

# both used by "rates" functions:
XL_DB_IN = "./flask-in/rates.xlsx"
# XL_DB_OUT = os.path.join(os.getcwd(), 'temp_rates.xlsx') # cant be use - as it create new excell file.

# ready Macros still not in use:
# DB_IN = "db/in/"
# DB_OUT = "db/out/"
# APP_IN_NETWORK = "flask/in/"  # will use for network between docker
# APP_OUT_NETWORK = "flask/out/"


def get_db_connection():
    """ "connector" to mysql DB"""
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
    """Admin registers a new provider. System validates uniqueness and stores in billdb."""
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
    """Admin updates provider details. Requires valid existing ID."""
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
    """Admin links a truck to a provider ID in the system."""
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
    """BONUS (we didnt required to) - historical of all tracks"""
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
    """Used by producer to query historical data for a truck."""
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
    """2nd implemantation for that function (we have it implemented above)"""
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


@app.route("/truck/<id>", methods=["PUT"])
def update_truck_provider(id):
    """Admin updates provider linkage for a truck already in the system."""
    try:
        data = request.json
        new_provider_id = data.get("provider")

        # validation
        if not new_provider_id:
            return jsonify({"error": "Missing 'provider' field"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # check truck exists
        cursor.execute("SELECT 1 FROM Trucks WHERE id = %s", (id,))
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({"error": f"Truck ID {id} does not exist"}), 404

        # check new provider exists
        cursor.execute("SELECT 1 FROM Provider WHERE id = %s", (new_provider_id,))
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({"error": f"Provider ID {new_provider_id} does not exist"}), 404

        # update provider_id
        cursor.execute("UPDATE Trucks SET provider_id = %s WHERE id = %s", (new_provider_id, id))
        conn.commit()
        conn.close()

        return jsonify({"status": "provider updated"}), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route('/post_rates', methods=['POST'])
def load_rates():
    """take "rates.xlsx" and convert to mysqlDB"""

    if not os.path.exists(XL_DB_IN):
        return jsonify({"error": f"File not found: {XL_DB_IN}"}), 404

    try:
        df = pd.read_excel(XL_DB_IN, engine='openpyxl')

        # Validate columns
        expected_columns = {'Product', 'Rate', 'Scope'}
        if not expected_columns.issubset(df.columns):
            return jsonify({"error": f"Missing columns. Required: {expected_columns}"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO Rates (product_id, rate, scope)
                VALUES (%s, %s, %s)
            """, (row['Product'], int(row['Rate']), row['Scope']))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": f"Inserted {len(df)} rows from {XL_DB_IN}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/rates', methods=['GET'])
def export_to_excel():
    """take mysqlDB and convert it to "outer.xlsx" """

    try:
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch data using cursor
        def fetch_table(query):
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame(rows, columns=columns)

        provider_df = fetch_table("SELECT * FROM Provider")
        rates_df = fetch_table("SELECT * FROM Rates")
        trucks_df = fetch_table("SELECT * FROM Trucks")

        # File path to save the Excel file
        file_path = os.path.join(os.getcwd(), 'temp_rates.xlsx')

        # Write to Excel
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            provider_df.to_excel(writer, sheet_name='Provider', index=False)
            rates_df.to_excel(writer, sheet_name='Rates', index=False)
            trucks_df.to_excel(writer, sheet_name='Trucks', index=False)

        # Cleanup
        cursor.close()
        conn.close()

        return f"Excel file saved at {file_path}"
        # replace above line, use later to download excel from website:
        # return send_file(file_path, as_attachment=True)
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
