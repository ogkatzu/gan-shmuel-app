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
    """Returns the last known tara and all sessions for a truck, via mock Weight service."""
    # when testing - comment that 2 lines:
    # if truck_id == "na":
    #     return jsonify({"error": "Invalid truck ID"}), 400

    item_url = f"http://weight-weight_app-1:5000/item/{truck_id}"
    
    # item_url = f"http://weight-weight_app-1:5000/item/na"
    # hardcoded - for testing

    try:
        res = requests.get(item_url, timeout=5)
        if res.status_code == 404:
            return jsonify({"error": "Truck not found"}), 404
        elif res.status_code != 200:
            return jsonify({"error": "Failed to fetch truck data"}), 502

        data = res.json()
        return jsonify({
            "id": data.get("id", truck_id),
            "tara": data.get("tara", "na"),
            "sessions": data.get("sessions", [])
        }), 200

    except requests.ConnectionError:
        return jsonify({
            "error": "Connection error to weight service",
            "details": f"Could not connect to {item_url}"
        }), 503

    except requests.Timeout:
        return jsonify({
            "error": "Weight service timeout",
            "details": f"Request to {item_url} timed out"
        }), 504

    except requests.RequestException as e:
        return jsonify({
            "error": "External request failed",
            "details": str(e)
        }), 500



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
    # Parse optional from/to query params (format: YYYYMMDDHHMMSS)
    now = datetime.now()
    default_from = datetime(now.year, now.month, 1, 0, 0, 0)
    default_to = now

    def parse_dt(dt_str):
        try:
            return datetime.strptime(dt_str, "%Y%m%d%H%M%S")
        except:
            return None

    from_str = request.args.get("from")
    to_str = request.args.get("to")

    date_from = parse_dt(from_str) or default_from
    date_to = parse_dt(to_str) or default_to

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get provider info
        cursor.execute("SELECT id, name FROM Provider WHERE id = %s", (provider_id,))
        provider = cursor.fetchone()
        if not provider:
            conn.close()
            return jsonify({"error": f"Provider ID {provider_id} not found"}), 404

        # Get trucks for provider
        cursor.execute("SELECT id FROM Trucks WHERE provider_id = %s", (provider_id,))
        trucks = [row['id'] for row in cursor.fetchall()]
        truck_count = len(trucks)

        # Get sessions associated with these trucks within date range
        # Assuming there's a Sessions table with truck_id, session_date columns
        # Adjust table and column names as per your schema
        if trucks:
            format_from = date_from.strftime("%Y-%m-%d %H:%M:%S")
            format_to = date_to.strftime("%Y-%m-%d %H:%M:%S")

            # Get session IDs and count
            format_strings = ','.join(['%s'] * len(trucks))  # placeholders for trucks
            query_sessions = f"""
                SELECT id FROM Sessions
                WHERE truck_id IN ({format_strings})
                  AND session_date BETWEEN %s AND %s
            """
            params = trucks + [format_from, format_to]
            cursor.execute(query_sessions, params)
            sessions = [row['id'] for row in cursor.fetchall()]
            session_count = len(sessions)
        else:
            sessions = []
            session_count = 0

        # Get product rates / totals - example
        # Assuming Rates table and linking with sessions or trucks
        # This depends on your schema, so this is a generic example:
        # We'll just fetch all Rates for the provider's products as demo

        cursor.execute("""
            SELECT product_id, rate, scope FROM Rates
            WHERE product_id IN (
                SELECT DISTINCT product_id FROM SessionsProducts
                WHERE session_id IN (%s)
            )
        """ % (','.join(['%s']*session_count) if session_count > 0 else 'NULL'), tuple(sessions) if session_count > 0 else ())
        )
        rates = cursor.fetchall()

        conn.close()

        return jsonify({
            "id": provider['id'],
            "name": provider['name'],
            "from": date_from.strftime("%Y%m%d%H%M%S"),
            "to": date_to.strftime("%Y%m%d%H%M%S"),
            "truckCount": truck_count,
            "trucks": trucks,
            "sessionCount": session_count,
            "sessions": sessions,
            "rates": rates
        })

    except Error as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
