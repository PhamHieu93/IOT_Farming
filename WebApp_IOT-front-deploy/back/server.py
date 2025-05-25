import psycopg2
import json
import time
import random
from datetime import datetime
from config import config
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("IOT_server")

# Initialize Flask and SocketIO
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    path='/socket.io/',
    logger=True,  # Enable logging
    engineio_logger=True  # Enable Engine.IO logging
)
# Keep track of connected clients
connected_clients = set()

# Keep track of device states
device_states = {}

def connect_db():
    """Connect to the PostgreSQL database server"""
    conn = None
    try:
        # read connection parameters
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()

        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to database: {error}")
        return None


def send_telemetry_data(device_id, data_value, data_unit, data_status="normal"):
    """Send telemetry data to the Data table"""
    conn = None
    data_id = None
    
    try:
        conn = connect_db()
        cur = conn.cursor()
        # with open('create.sql', 'r') as f:
        #     sql = f.read()
        #     cur.execute(sql)
        # Get the next DataID (this assumes you're not using SERIAL for DataID)
        cur.execute("SELECT COALESCE(MAX(DataID), 0) + 1 FROM Data")
        data_id = cur.fetchone()[0]
        
        # Insert telemetry data into Data table
        cur.execute(
            """
            INSERT INTO Data (DataID, DID, Value, Unit, Status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (data_id, device_id, data_value, data_unit, data_status)
        )
        
        conn.commit()
        print(f"Telemetry data sent - Device: {device_id}, Value: {data_value} {data_unit}, Status: {data_status}")
        return data_id
    
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error sending telemetry data: {error}")
        return None
    finally:
        if conn is not None:
            conn.close()

def update_device_status(device_id, device_name, device_type, current_value, unit):
    """Update device status in JSON format"""
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        # Get current device status if exists
        cur.execute("SELECT status FROM Device WHERE DID = %s", (device_id,))
        result = cur.fetchone()
        
        # Set thresholds based on device type
        if device_type == "temperature":
            thresholds = {
                "min": 18, "max": 28, 
                "warningMin": 20, "warningMax": 26,
                "criticalMin": 15, "criticalMax": 30
            }
            location = {"zone": "Greenhouse", "area": "North", "position": "Wall"}
        elif device_type == "humidity":
            thresholds = {
                "min": 40, "max": 80,
                "warningMin": 45, "warningMax": 75,
                "criticalMin": 30, "criticalMax": 85
            }
            location = {"zone": "Greenhouse", "area": "Center", "position": "Ceiling"}
        elif device_type == "soil_moisture":
            thresholds = {
                "min": 20, "max": 60,
                "warningMin": 25, "warningMax": 55,
                "criticalMin": 15, "criticalMax": 65
            }
            location = {"zone": "Field", "area": "East", "position": "Ground"}
        else:
            thresholds = {
                "min": 0, "max": 100,
                "warningMin": 10, "warningMax": 90,
                "criticalMin": 5, "criticalMax": 95
            }
            location = {"zone": "Unknown", "area": "Unknown", "position": "Unknown"}
        
        # Determine status based on current value and thresholds
        if current_value < thresholds["criticalMin"] or current_value > thresholds["criticalMax"]:
            status = "critical"
        elif current_value < thresholds["warningMin"] or current_value > thresholds["warningMax"]:
            status = "warning"
        else:
            status = "normal"
            
        # Battery level simulation (decreases over time)
        battery_level = random.randint(75, 100)
        
        # Create status JSON
        status_json = {
            "id": f"{device_type}{device_id:03}",
            "name": device_name,
            "type": device_type,
            "model": "IOT Farming Sensor v2",
            "serialNumber": f"IOT-2025-{device_id:04}",
            "location": location,
            "status": status,
            "lastValue": current_value,
            "unit": unit,
            "lastUpdated": datetime.now().isoformat(),
            "installDate": "2024-01-15",
            "threshold": thresholds,
            "readingInterval": 5,
            "batteryLevel": battery_level,
            "firmwareVersion": "2.1.0",
            "indicColor": "#FF9733" if status == "normal" else "#FF3333"
        }
        
        # Insert or update device status
        if result is None:
            # Device doesn't exist, insert new record
            cur.execute(
                """
                INSERT INTO Device (DID, Dname, Location, Type, status)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (device_id, device_name, location["zone"], device_type, json.dumps(status_json))
            )
        else:
            # Update existing device
            cur.execute(
                """
                UPDATE Device
                SET Dname = %s, Location = %s, Type = %s, status = %s::jsonb
                WHERE DID = %s
                """,
                (device_name, location["zone"], device_type, json.dumps(status_json), device_id)
            )
        
        conn.commit()
        print(f"Device status updated - Device: {device_id}, Status: {status}")
        return True
    
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error updating device status: {error}")
        return False
    finally:
        if conn is not None:
            conn.close()

def simulate_telemetry():
    """Simulate telemetry data from different devices"""
    devices = [
        {"id": 1, "name": "Greenhouse Temperature Sensor", "type": "temperature", "unit": "°C"},
        {"id": 2, "name": "Humidity Monitor", "type": "humidity", "unit": "%"},
        {"id": 3, "name": "Soil Moisture Sensor", "type": "soil_moisture", "unit": "%"}
    ]
    
    print("Starting telemetry simulation...")
    print("-" * 50)
    
    try:
        # Generate 5 readings for each device
        for _ in range(5):
            for device in devices:
                # Generate realistic values based on device type
                if device["type"] == "temperature":
                    value = round(random.uniform(15.0, 32.0), 1)  # °C
                elif device["type"] == "humidity":
                    value = round(random.uniform(35.0, 85.0), 1)  # %
                elif device["type"] == "soil_moisture":
                    value = round(random.uniform(15.0, 70.0), 1)  # %
                else:
                    value = round(random.uniform(0.0, 100.0), 1)
                
                # Send data to standard SQL table
                data_id = send_telemetry_data(device["id"], value, device["unit"])
                
                # Update device status JSON
                update_device_status(
                    device["id"], 
                    device["name"], 
                    device["type"], 
                    value,
                    device["unit"]
                )
                
                print(f"Data point ID: {data_id} sent successfully")
                print("-" * 50)
                
            # Wait before next batch of readings
            time.sleep(2)
            
    except Exception as e:
        print(f"Error in telemetry simulation: {e}")
    
    print("Telemetry simulation completed")

def add_device_activity(device_id, action, status="Active"):
    """Record device activity in the Device_Activity table"""
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        # Get next activity ID
        cur.execute("SELECT COALESCE(MAX(ActivityID), 0) + 1 FROM Device_Activity")
        activity_id = cur.fetchone()[0]
        
        # Insert activity record
        cur.execute(
            """
            INSERT INTO Device_Activity (ActivityID, DID, Action, Status)
            VALUES (%s, %s, %s, %s)
            """,
            (activity_id, device_id, action, status)
        )
        
        conn.commit()
        print(f"Device activity recorded - Device: {device_id}, Action: {action}, Status: {status}")
        return True
    
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error recording device activity: {error}")
        return False
    finally:
        if conn is not None:
            conn.close()
# Enhanced WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    sid = request.sid
    connected_clients.add(sid)
    logger.info(f"Client connected: {sid}")
    emit('connection_status', {
        'status': 'connected', 
        'message': 'Connected to IOT Farming WebSocket server',
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in connected_clients:
        connected_clients.remove(sid)
    logger.info(f"Client disconnected: {sid}")

@socketio.on('message')
def handle_message(data):
    logger.info(f"Received message: {data}")
    emit('message', {
        'status': 'received', 
        'data': data,
        'timestamp': datetime.now().isoformat(),
        'received': True
    })

@socketio.on('ping')
def handle_ping():
    logger.info(f"Ping received from client: {request.sid}")
    emit('pong', {
        'data': 'Pong from server!',
        'timestamp': datetime.now().isoformat(),
        'received': True
    })

@socketio.on('device_command')
def handle_device_command(command):
    """Handle device control commands from frontend with enhanced logging and acknowledgment"""
    try:
        # Get current timestamp
        timestamp = datetime.now().isoformat()
        
        # Log detailed information about the command
        logger.info(f"Device command received at {timestamp}")
        logger.info(f"Command details - Sector: {command.get('sector')}, Device: {command.get('device')}, Status: {command.get('status')}, Type: {command.get('type')}")
        logger.info(f"Additional data: {command}")
        
        sector = command.get('sector')
        device = command.get('device')
        status = command.get('status')
        control_type = command.get('type')
        
        # Update device state
        device_key = f"{sector}_{device}"
        device_states[device_key] = {
            'status': status,
            'type': control_type,
            'last_updated': timestamp
        }
        
        # Save to database or send to actual device here
        
        # Send detailed acknowledgment back to client
        emit('command_response', {
            'success': True,
            'device': device_key,
            'status': status,
            'received': True,
            'timestamp': timestamp,
            'message': f"Command for {device} in sector {sector} processed successfully"
        })
        
        # Broadcast to all clients that a device state has changed
        socketio.emit('device_update', {
            'device': device_key,
            'status': status,
            'timestamp': timestamp
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error handling device command: {error_msg}")
        emit('command_response', {
            'success': False,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })

@socketio.on('control_type_change')
def handle_control_type_change(command):
    """Handle control type changes from frontend with enhanced logging"""
    try:
        # Get current timestamp
        timestamp = datetime.now().isoformat()
        
        # Log the type change request
        logger.info(f"Control type change received at {timestamp}")
        logger.info(f"Type change details - Sector: {command.get('sector')}, Device: {command.get('device')}, Type: {command.get('type')}")
        
        sector = command.get('sector')
        device = command.get('device')
        control_type = command.get('type')
        additionalData = {k: v for k, v in command.items() if k not in ['sector', 'device', 'type', 'status']}
        
        # Update device control type
        device_key = f"{sector}_{device}"
        if device_key in device_states:
            device_states[device_key]['type'] = control_type
            device_states[device_key]['last_updated'] = timestamp
            # Add any additional data like schedule settings
            if additionalData:
                device_states[device_key].update(additionalData)
        else:
            device_states[device_key] = {
                'type': control_type,
                'last_updated': timestamp
            }
            # Add any additional data
            if additionalData:
                device_states[device_key].update(additionalData)
            
        logger.info(f"Control type change - Device: {device_key}, Type: {control_type}, Additional data: {additionalData}")
        
        # Send success response back to client
        emit('type_change_response', {
            'success': True,
            'device': device_key,
            'type': control_type,
            'received': True,
            'timestamp': timestamp,
            'message': f"Control type for {device} in sector {sector} changed to {control_type}"
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error handling control type change: {error_msg}")
        emit('type_change_response', {
            'success': False,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })

@app.route('/')
def index():
    """Serve a simple welcome page at the root URL"""
    return jsonify({
        'name': 'IOT Farming System API',
        'version': '1.0',
        'status': 'online',
        'time': datetime.now().isoformat(),
        'endpoints': {
            'status': '/api/status',
            'websocket': 'socket.io connection'
        },
        'connected_clients': len(connected_clients)
    })

# HTTP Routes
@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'online',
        'time': datetime.now().isoformat(),
        'clients_connected': len(connected_clients)
    })

# Add a new route to get the current state of all devices
@app.route('/api/device-states')
def get_device_states():
    return jsonify({
        'status': 'success',
        'time': datetime.now().isoformat(),
        'device_states': device_states
    })

def start_simulation_thread():
    # Record device activities for simulation
    for device_id in [1, 2, 3]:
        add_device_activity(device_id, "Start Telemetry")
    
    # Start simulation
    simulate_telemetry()
    
    # This won't be reached as the simulation runs indefinitely
    for device_id in [1, 2, 3]:
        add_device_activity(device_id, "End Telemetry")

if __name__ == "__main__":
    # Record device activities for simulation
    simulation_thread = threading.Thread(target=start_simulation_thread)
    simulation_thread.daemon = True  # This makes the thread exit when the main program exits
    simulation_thread.start()
    
    # Start the Flask/SocketIO server
    print("Starting WebSocket server on port 3000")
    socketio.run(app, host='0.0.0.0', port=3000, debug=True, allow_unsafe_werkzeug=True)