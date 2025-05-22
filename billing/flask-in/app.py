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

# Weight service URL configuration
WEIGHT_URL = f"http://{os.environ.get('WEIGHT_DOCKER_HOST', 'localhost')}:5000"

# Global variable for mock mode
MOCK_WEIGHT_MODE = False

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


def get_date_range():
    """Parse date range from query parameters or use defaults"""
    now = datetime.now()
    default_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    default_to = now

    from_str = request.args.get("from") or default_from.strftime("%Y%m%d%H%M%S")
    to_str = request.args.get("to") or default_to.strftime("%Y%m%d%H%M%S")
    return from_str, to_str


def get_trucks_for_provider(provider_id):
    """Get all trucks for a given provider"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Trucks WHERE provider_id = %s", (provider_id,))
        trucks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return trucks
    except Error:
        return []


def get_sessions_for_truck(truck_id, from_str, to_str):
    """Get session IDs for a truck from Weight service"""
    try:
        resp = requests.get(
            f"{WEIGHT_URL}/item/{truck_id}",
            params={"from": from_str, "to": to_str},
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json().get("sessions", [])
    except Exception:
        pass
    return []


def get_sessions_for_truck_mock(truck_id, from_str, to_str):
    """Mock version that returns test sessions"""
    if MOCK_WEIGHT_MODE:
        return ["sess-001", "sess-002", "sess-003"]
    else:
        return get_sessions_for_truck(truck_id, from_str, to_str)


def get_valid_out_session_data(session_id):
    """Get session data from Weight service for billing calculation"""
    try:
        resp = requests.get(f"{WEIGHT_URL}/session/{session_id}", timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        # Only process 'out' sessions with valid neto values
        if "truckTara" in data and data.get("neto") not in [None, "na"]:
            return {
                "produce": data.get("produce"),
                "neto": int(data["neto"])
            }
    except Exception:
        pass
    return None


def get_valid_out_session_data_mock(session_id):
    """Mock version that returns test session data"""
    if MOCK_WEIGHT_MODE:
        mock_sessions = {
            "sess-001": {"produce": "orange", "neto": 500},
            "sess-002": {"produce": "apple", "neto": 300}, 
            "sess-003": {"produce": "tomato", "neto": 400}
        }
        return mock_sessions.get(session_id, None)
    else:
        return get_valid_out_session_data(session_id)


def get_rate_for_product(product, provider_id):
    """Get rate for a product, checking provider-specific first, then ALL"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First try specific provider
        cursor.execute("SELECT rate FROM Rates WHERE product_id = %s AND scope = %s", 
                      (product, str(provider_id)))
        result = cursor.fetchone()
        
        if not result:
            # Then try ALL
            cursor.execute("SELECT rate FROM Rates WHERE product_id = %s AND scope = %s", 
                          (product, "ALL"))
            result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else "unknown"
    except Error:
        return "unknown"


def aggregate_product_stats(session_data_list, provider_id):
    """Aggregate product statistics for billing"""
    product_stats = {}
    total_pay = 0
    session_count = 0

    for entry in session_data_list:
        product = entry["produce"]
        neto = entry["neto"]
        rate = get_rate_for_product(product, provider_id)
        
        pay = rate * neto if isinstance(rate, int) else "unknown"

        if product not in product_stats:
            product_stats[product] = {
                "product": product,
                "count": 0,
                "amount": 0,
                "rate": rate,
                "pay": 0 if isinstance(rate, int) else "unknown"
            }

        product_stats[product]["count"] += 1
        product_stats[product]["amount"] += neto

        if isinstance(pay, int):
            product_stats[product]["pay"] += pay
            total_pay += pay

        session_count += 1

    return list(product_stats.values()), session_count, total_pay

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

    # item_url = f"http://weight-weight_app-1:5000/item/{truck_id}"

    host_weight=os.environ.get('WEIGHT_DOCKER_HOST','localhost')
    item_url = f"http://{host_weight}:5000/item/{truck_id}"

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


@app.route("/test-setup", methods=["POST"])
def setup_test_data():
    """Setup test data for billing demonstration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert test rates
        test_rates = [
            ("orange", 15, "ALL"),
            ("apple", 12, "ALL"), 
            ("tomato", 18, "10001"),
            ("banana", 10, "ALL")
        ]
        
        # Clear existing rates and insert test rates
        cursor.execute("DELETE FROM Rates")
        for product, rate, scope in test_rates:
            cursor.execute("INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)", 
                          (product, rate, scope))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Test data setup complete",
            "rates_added": len(test_rates)
        }), 200
        
    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route("/mock-weight-mode", methods=["POST"])
def enable_mock_weight_mode():
    """Enable mock mode for Weight service calls"""
    global MOCK_WEIGHT_MODE
    MOCK_WEIGHT_MODE = True
    return jsonify({"message": "Mock Weight mode enabled"}), 200


@app.route("/mock-weight-mode", methods=["DELETE"])
def disable_mock_weight_mode():
    """Disable mock mode for Weight service calls"""
    global MOCK_WEIGHT_MODE
    MOCK_WEIGHT_MODE = False
    return jsonify({"message": "Mock Weight mode disabled"}), 200


@app.route("/mock-status", methods=["GET"])
def get_mock_status():
    """Get current mock mode status"""
    return jsonify({"mock_mode": MOCK_WEIGHT_MODE}), 200

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

        # Clear existing rates
        cursor.execute("DELETE FROM Rates")

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
    """Generate billing report for a provider (with mock support)"""
    try:
        # Check if provider exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Provider WHERE id = %s", (provider_id,))
        provider = cursor.fetchone()
        conn.close()
        
        if not provider:
            return jsonify({"error": "Provider not found"}), 404

        from_str, to_str = get_date_range()
        trucks = get_trucks_for_provider(provider_id)
        truck_ids = trucks

        used_trucks = set()
        all_sessions_data = []

        for truck_id in truck_ids:
            # Use mock or real function based on mode
            if MOCK_WEIGHT_MODE:
                session_ids = get_sessions_for_truck_mock(truck_id, from_str, to_str)
            else:
                session_ids = get_sessions_for_truck(truck_id, from_str, to_str)
                
            if session_ids:
                used_trucks.add(truck_id)

            for sid in session_ids:
                if MOCK_WEIGHT_MODE:
                    session_data = get_valid_out_session_data_mock(sid)
                else:
                    session_data = get_valid_out_session_data(sid)
                    
                if session_data:
                    all_sessions_data.append(session_data)

        products, session_count, total_pay = aggregate_product_stats(all_sessions_data, provider_id)

        result = {
            "id": provider[0],
            "name": provider[1],
            "from": from_str,
            "to": to_str,
            "truckCount": len(used_trucks),
            "sessionCount": session_count,
            "products": products,
            "total": total_pay,
            "mock_mode": MOCK_WEIGHT_MODE
        }

        return jsonify(result), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500


@app.route("/test-full-billing", methods=["GET"])
def test_full_billing():
    """Complete test of billing system with mock data"""
    try:
        # Setup test data
        setup_response = setup_test_data()
        if setup_response[1] != 200:
            return setup_response
            
        # Enable mock mode
        global MOCK_WEIGHT_MODE
        MOCK_WEIGHT_MODE = True
        
        # Test billing for provider 10001
        provider_id = 10001
        bill_response = get_bill(provider_id)
        
        return jsonify({
            "test_status": "completed",
            "setup": "success",
            "mock_mode": "enabled",
            "bill_data": bill_response[0].get_json() if hasattr(bill_response[0], 'get_json') else bill_response[0]
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)