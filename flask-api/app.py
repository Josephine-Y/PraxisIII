from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import time
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("API_KEY")

# Initialize feeds
FEEDS = ["picow14", "picow141", "picow142", "picow42"]

# latest_cache = {node: {"temperature": None, "timestamp": None} for node in FEEDS}

# Database Connection
def get_db():
    return psycopg2.connect(os.getenv("SUPABASE_DB_URL"))

@app.route("/")
def index():
    return render_template("webpage.html")

@app.route("/data", methods=["POST"])
def receive_data():
    if request.headers.get("X-Api-Key") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    node = data.get("node")
    temp = data.get("temp")
    unix_time = data.get("time")

    # convert unix timestamp to datetime for Supabase
    timestamp = datetime.fromtimestamp(unix_time, tz=timezone.utc)

    if node not in FEEDS:
        return jsonify({"error": "Unknown node"}), 400
    
    try:
        # latest_cache[node] = {"temperature": temp, "timestamp": str(timestamp)}

        connection = get_db()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO data (node, temperature, timestamp) VALUES (%s, %s, %s)",
            (node, temp, timestamp)
        )
        connection.commit()
        cursor.close()
        connection.close()
        print(f"Sent to database {node} = {temp}°C, {timestamp}")
        return jsonify({"status": "ok"})
    
    except Exception as e:
        print(f"Receive Data Error: {e}")
        return jsonify({"error": "Receive Data Error"}), 500

# @app.route("/latest", methods=["GET"])
# def get_latest_data():
#     return jsonify(latest_cache)

@app.route("/latest", methods=["GET"])
def get_latest_data():
    try:
        connection = get_db()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT node, temperature, timestamp
            FROM data
            WHERE (node, timestamp) IN (
                SELECT node, MAX(timestamp)
                FROM data
                GROUP BY node
            )
        """)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        latest_data = {node: {"temperature": None, "timestamp": None} for node in FEEDS}
        for row in rows:
            latest_data[row[0]] = {"temperature": row[1], "timestamp": row[2]}
        return jsonify(latest_data)
    
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database Error"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host = "0.0.0.0", port=port)