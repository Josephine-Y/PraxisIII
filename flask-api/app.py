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
import math
import numpy as np
import ssl

load_dotenv()

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("API_KEY")

# Initialize feeds
FEEDS = ["picow14", "picow141", "picow142", "picow42", "anemometer"]

# latest_cache = {node: {"temperature": None, "timestamp": None} for node in FEEDS}

# Database Connection
def get_db():
    return psycopg2.connect(os.getenv("SUPABASE_DB_URL"))

# ---------------------------------------------------
# Serve webpage
@app.route("/")
def index():
    return render_template("webpage.html")
# ---------------------------------------------------
# Get latest data JSON from Supabase
@app.route("/latest", methods=["GET"])
def get_latest_data():
    try:
        connection = get_db()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT node, temperature, wind_speed, timestamp
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

        latest_data = {node: {"temperature": None, "wind_speed": None, "timestamp": None} for node in FEEDS}
        for row in rows:
            latest_data[row[0]] = {"temperature": row[1], "wind_speed": row[2], "timestamp": row[3]}
        return jsonify(latest_data)
    
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database Error"}), 500

def save_to_db(node, temp, wind_speed, unix_time):
    # convert unix timestamp to datetime for Supabase
    timestamp = datetime.fromtimestamp(unix_time, tz=timezone.utc)

    try:
        # latest_cache[node] = {"temperature": temp, "wind_speed": wind_speed, "timestamp": str(timestamp)}

        connection = get_db()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO data (node, temperature, wind_speed, timestamp) VALUES (%s, %s, %s, %s)",
            (node, temp, wind_speed, timestamp)
        )
        connection.commit()
        cursor.close()
        connection.close()
        print(f"Sent to database {node} = {temp}°C, {wind_speed} m/s, {timestamp}")
    
    except Exception as e:
        print(f"Receive Data Error: {e}")
# ---------------------------------------------------
# Calculate rate of spread

# ROS Variables
TEMP_THRESHOLD = 25.0 # potentially change # Threshold of node before indicating a fire spread
last_hot_time = {}

# Node locations: We'll need to place the nodes at specific locations and input their respective coordinates here before running the code
def get_node_location(node):
    if node == "picow14":
        return (0.0, 0.0)
    elif node == "picow141":
        return (1.0, 0.0)
    elif node == "picow142":
        return (0.0, 1.0)
    elif node == "picow42":
        return (1.0, 1.0)
    else:
        return (0.0, 0.0)

# Update last hot times
def update_last_hot_times():
    latest_data = get_latest_data()
    if latest_data.status_code != 200:
        print("Error fetching latest data")
        return
    latest_data = latest_data.get_json()

    global last_hot_time
    for node, values in latest_data.items():
        temp = values["temperature"]

        if temp is None:
            continue
        if temp >= TEMP_THRESHOLD:
            last_hot_time[node] = values["timestamp"]

# Calculate ROS
def calculate_ros():
    global last_hot_time
    triggered_nodes = [(node, last_hot_time[node]) for node in last_hot_time if last_hot_time[node] > 0]
    
    if len(triggered_nodes) < 2:
        return 0.0, len(triggered_nodes)
    elif len(triggered_nodes) == 2:
        node1, t1 = triggered_nodes[0]
        node2, t2 = triggered_nodes[1]
        x1, y1 = get_node_location(node1)
        x2, y2 = get_node_location(node2)
        d = math.hypot(x2 - x1, y2 - y1)
        dt = abs(t2 - t1)
        if dt == 0:
            return 0.0, 2
        ros = d / dt
        return ros, 2
    else:
        X = []
        t_vec = []
        for node, t in triggered_nodes:
            x, y = get_node_location(node)
            X.append([x, y, 1])
            t_vec.append(t)
        a, b, c = np.linalg.lstsq(np.array(X), np.array(t_vec), rcond=None)[0]
        ros = 1 / math.sqrt(a**2 + b**2)
        return ros, len(triggered_nodes)
    
@app.route("/rateofspread", methods=["GET"])
def get_rate_of_spread():
    update_last_hot_times()
    rate_of_spread, hot_nodes_count = calculate_ros()
    return jsonify({"rate_of_spread": rate_of_spread, "hot_nodes_count": hot_nodes_count})

# MQTT Callback Methods
@app.route("/mqtt-config")
def mqtt_config():
    return jsonify({
        # "username": os.getenv("MQTT_USERNAME"),
        # "password": os.getenv("MQTT_PASSWORD"),
        # "broker": "wss://339f0d63410548358f66c3cb882ec424.s1.eu.hivemq.cloud:8884/mqtt"

        "username": None,
        "password": None,
        "broker": "wss://broker.emqx.io:8084/mqtt"
    })

def on_message(client, userdata, message):
    topic = message.topic # nodes/{node}/jsonify(data)
    node = topic.split("/")[1] # {node}
    data = json.loads(message.payload.decode())
    if node == "anemometer":
        wind_speed = data.get("wind_speed")
        temp = None
    else:
        temp = data.get("temp")
        wind_speed = None
    unix_time = data.get("timestamp")

    save_to_db(node, temp, wind_speed, unix_time)

def on_connect(client, userdata, flags, rc):
    client.subscribe("nodes/+/data")

def start_mqtt():
    try:
        # client = MQTT.Client(transport="websockets")
        client = MQTT.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        # client.tls_set(cert_reqs=ssl.CERT_NONE)

        client.connect("broker.emqx.io", port=1883)
        client.loop_forever()

    except Exception as e:
        print(f"MQTT Client Error: {e}")

# Start MQTT client in a separate thread
threading.Thread(target=start_mqtt, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host = "0.0.0.0", port=port)
