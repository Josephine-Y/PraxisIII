# app.py
# Flask API subscribed to MQTT --> Database (Supabase)

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import paho.mqtt.client as MQTT
import threading
import json

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

def save_to_db(node, temp, unix_time):
    # convert unix timestamp to datetime for Supabase
    timestamp = datetime.fromtimestamp(unix_time, tz=timezone.utc)

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
    
    except Exception as e:
        print(f"Receive Data Error: {e}")

# MQTT Callback Methods
# app.py
@app.route("/mqtt-config")
def mqtt_config():
    return jsonify({
        "username": os.getenv("MQTT_USERNAME"),
        "password": os.getenv("MQTT_PASSWORD"),
        "broker": "wss://339f0d63410548358f66c3cb882ec424.s1.eu.hivemq.cloud:8884/mqtt"
    })

def on_message(client, userdata, message):
    topic = message.topic # nodes/{node}/jsonify(data)
    node = topic.split("/")[1] # {node}
    data = json.loads(message.payload.decode())
    temp = data["temp"]
    unix_time = data["timestamp"]
    save_to_db(node, temp, unix_time)

def on_connect(client, userdata, flags, rc):
    client.subscribe("nodes/+/data")

def start_mqtt():
    try:
        client = MQTT.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(os.getenv("MQTT_USERNAME"), os.getenv("MQTT_PASSWORD"))
        client.tls_set() # SSL/TLS encryption
        client.connect("339f0d63410548358f66c3cb882ec424.s1.eu.hivemq.cloud", 8883)
        client.loop_forever()
    except Exception as e:
        print(f"MQTT Client Error: {e}")

# Start MQTT client in a separate thread
threading.Thread(target=start_mqtt, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host = "0.0.0.0", port=port)
