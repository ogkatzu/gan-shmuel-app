import os
from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error

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
        data = request.json
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
        data = request.json
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
