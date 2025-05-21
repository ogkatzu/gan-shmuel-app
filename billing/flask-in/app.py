import os
from flask import Flask, request, jsonify, send_file
import mysql.connector
from mysql.connector import Error
import pandas as pd
# from flask_sqlalchemy import SQLAlchemy
import openpyxl
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# both used by "rates" functions:
XL_DB_IN = "./in/rates.xlsx"
XL_DB_OUT = os.path.join(os.getcwd(), 'temp_rates.xlsx')

# ready Macros still not in use:
# DB_IN = "db/in/"
# DB_OUT = "db/out/"
# APP_IN_NETWORK = "flask/in/"  # will use for network between docker
# APP_OUT_NETWORK = "flask/out/"

# ########## helper methods ########### #
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
# #########f helper methods ########### #


def get_db_connection():
    """ "connector" to mysql DB"""
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST"),
        user=os.environ.get("MYSQL_USER"),
        password=os.environ.get("MYSQL_PASSWORD"),
        database=os.environ.get("MYSQL_DATABASE")
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
    """Admin registers a new provider. System validates uniqueness and stores in billdb.
    usage: curl -X POST http://127.0.0.1:5500/provider \
            -H "Content-Type: application/json" \
            -d '{"name": "MyProvider"}' """
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


@app.route("/truck", methods=["POST"])
def register_truck():
    """Admin links a truck to a provider ID in the system."""
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


@app.route("/truck/<truck_id>", methods=["GET"])
def get_truck_info(truck_id):
    """Returns the last known tara and all sessions for a truck, via mock Weight service"""
    try:
        item_url = f"http://localhost:5500/mock/item/{truck_id}"  # mocked endpoint
        res = requests.get(item_url, timeout=5)

        if res.status_code == 404:
            return jsonify({"error": "Truck not found"}), 404
        elif res.status_code != 200:
            return jsonify({"error": "Failed to fetch truck data"}), 502

        data = res.json()
        return jsonify({
            "id": data["id"],
            "tara": data["tara"],
            "sessions": data["sessions"]
        }), 200
    except requests.RequestException as e:
        return jsonify({"error": "External request failed", "details": str(e)}), 500


# ############ mock testing helpers ############## #
@app.route("/mock/item/<truck_id>")
def mock_item(truck_id):
    """Mocked response for GET /item/<id> from Weight service"""
    return jsonify({
        "id": truck_id,
        "tara": 543,
        "sessions": ["sess-001", "sess-002", "sess-003"]
    })


@app.route("/mock/session/<session_id>")
def mock_session(session_id):
    """Mocked response for GET /session/<id> from Weight service"""
    return jsonify({
        "id": session_id,
        "truck": "T-12345",
        "bruto": 1200,
        "truckTara": 600,
        "neto": 600
    })
# ###########f mock testing helpers ############## #


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

        # Write to Excel
        with pd.ExcelWriter(XL_DB_OUT, engine='openpyxl') as writer:
            provider_df.to_excel(writer, sheet_name='Provider', index=False)
            rates_df.to_excel(writer, sheet_name='Rates', index=False)
            trucks_df.to_excel(writer, sheet_name='Trucks', index=False)

        # Cleanup
        cursor.close()
        conn.close()

        return f"Excel file saved at {XL_DB_OUT}"
        # replace above line, use later to download excel from website:
        # return send_file(file_path, as_attachment=True)
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


@app.route('/bill/<int:provider_id>', methods=['GET'])
def get_bill(provider_id):
    """Endpoint to generate billing report for a specific provider within a time range.
    - URL params: t1 (start datetime), t2 (end datetime) in format yyyymmddhhmmss
    - t1 default: first day of current month at 00:00:00
    - t2 default: current datetime"""

    # set default time "t1==from" "t2==to"
    def parse_time(ts_str, label):
        try:
            return datetime.strptime(ts_str, "%Y%m%d%H%M%S")
        except ValueError:
            raise ValueError(f"Invalid format for {label}. Expected yyyymmddhhmmss.")
    try:
        # Parse arguments
        t1_str = request.args.get('t1')
        t2_str = request.args.get('t2')
        now = datetime.now()

        # Default t1: first of current month at 00:00:00
        if not t1_str:
            t1 = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            t1 = parse_time(t1_str, 't1')

        # Default t2: current time
        if not t2_str:
            t2 = now
        else:
            t2 = parse_time(t2_str, 't2')

        if t1 > t2:
            return jsonify({"error": "t1 must be before t2"}), 400

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    total_bill = 0

    # DB query to count trucks for this provider
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Trucks WHERE provider_id = %s", (provider_id,))
    truck_ids = [row[0] for row in cursor.fetchall()]
    truck_count = len(truck_ids)
    # above line can be replace with:
    # truck_count = cursor.fetchone()[0]
    conn.close()

    # Use mock API to count total sessions
    session_count = 0
    for truck_id in truck_ids:
        try:
            item_url = f"http://localhost:5500/mock/item/{truck_id}"
            res = requests.get(item_url, timeout=5)

            if res.status_code == 200:
                data = res.json()
                session_count += len(data.get("sessions", []))
            elif res.status_code == 404:
                continue  # skip if truck not found
            else:
                continue  # skip if other error
        except requests.RequestException:
            continue  # skip failed requests

    return jsonify({
            "provider_id": provider_id,
            "from": t1.strftime("%Y-%m-%d %H:%M:%S"),
            "to": t2.strftime("%Y-%m-%d %H:%M:%S"),
            "truck_count": truck_count,
            "sessionCount": session_count,

            "message": "Time range parsed successfully",
            "total": total_bill
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
