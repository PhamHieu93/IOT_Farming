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
import atexit
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log", mode='w'),
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

# Add this to track connected hardware devices
connected_hardware = {}

def connect_db():
    """Connect to the PostgreSQL database server and initialize tables if needed"""
    conn = None
    try:
        # read connection parameters
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()            
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to database: {error}")
        if conn:
            conn.rollback()
        return None
    # Don't close connection here as it's used by the caller

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
    # Send latest temperature data on connect
    temp_data = get_latest_temperature_data()
    if temp_data:
        emit('temperature_data', {
            'success': True,
            'data': temp_data,
            'timestamp': datetime.now().isoformat(),
            'initial': True
        })
    # Send latest humidity data
    humidity_data = get_latest_humidity_data()
    if humidity_data:
        emit('humidity_data', {
            'success': True,
            'data': humidity_data,
            'timestamp': datetime.now().isoformat(),
            'initial': True
        })
    
    # Send latest light data
    light_data = get_latest_light_data()
    if light_data:
        emit('light_data', {
            'success': True,
            'data': light_data,
            'timestamp': datetime.now().isoformat(),
            'initial': True
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

def save_device_command(sector, device, status, command_type, additional_data=None):
    """Save device command to database"""
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        # Convert status to boolean and additional data to JSON string
        status_bool = bool(status)
        command_data = json.dumps(additional_data) if additional_data else '{}'
          # For threshold type, save to Device_Thresholds table
        if command_type == "Thresholds":
            threshold_data = additional_data or {}
            
            # Ensure we have valid values for mandatory fields
            min_threshold = threshold_data.get('minThreshold')
            if min_threshold is None:
                min_threshold = 0  # Default value
                logger.warning(f"No minThreshold provided for {sector}:{device}, using default value 0")
                
            max_threshold = threshold_data.get('maxThreshold')
            if max_threshold is None:
                max_threshold = 100  # Default value
                logger.warning(f"No maxThreshold provided for {sector}:{device}, using default value 100")
                
            unit = threshold_data.get('unit')
            if unit is None:
                unit = ''  # Default empty string
                logger.warning(f"No unit provided for {sector}:{device}, using empty string")
            
            cur.execute(
                """
                INSERT INTO Device_Thresholds (Sector, Device, MinThreshold, MaxThreshold, Unit, Status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (Sector, Device) 
                DO UPDATE SET
                    MinThreshold = EXCLUDED.MinThreshold,
                    MaxThreshold = EXCLUDED.MaxThreshold,
                    Unit = EXCLUDED.Unit,
                    Status = EXCLUDED.Status,
                    Timestamp = CURRENT_TIMESTAMP
                RETURNING ThresholdID
                """,
                (sector, device, min_threshold, max_threshold, unit, status_bool)
            )
            threshold_id = cur.fetchone()[0]
            command_data = json.dumps({'threshold_id': threshold_id})

        # Insert command record using string format for JSONB
        cur.execute(
            """
            INSERT INTO Device_Commands (Sector, Device, Status, Type, Command_Data) 
            VALUES (%s, %s, %s, %s, %s::jsonb)
            RETURNING CommandID
            """,
            (sector, device, status_bool, command_type, command_data)
        )
        
        command_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"Command saved to database - ID: {command_id}")
        return command_id
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error saving command to database: {error}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn is not None:
            conn.close()

def get_command_history(limit=100):
    """Get command history from database"""
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        # Query commands with proper JSON handling
        cur.execute(
            """
            SELECT CommandID, Sector, Device, Status, Type, 
                   Command_Data::text, -- Convert JSONB to text
                   Timestamp 
            FROM Device_Commands 
            ORDER BY Timestamp DESC 
            LIMIT %s
            """,
            (limit,)
        )
        
        columns = ['command_id', 'sector', 'device', 'status', 'type', 
                  'command_data', 'timestamp']
        results = []
        
        for row in cur.fetchall():
            result = dict(zip(columns, row))
            # Parse text JSON to dict
            result['command_data'] = json.loads(result['command_data'])
            result['timestamp'] = result['timestamp'].isoformat()
            results.append(result)
            
        return results
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error getting command history: {error}")
        return []
    finally:
        if conn is not None:
            conn.close()

@socketio.on('device_command')
def handle_device_command(command):
    try:
        timestamp = datetime.now().isoformat()
        
        # Extract command data
        sector = command.get('sector')
        device = command.get('device')
        status = command.get('status')
        control_type = command.get('type')
        
        # Log full command data for debugging
        logger.info(f"Received command data: {json.dumps(command)}")
        
        # Handle threshold type separately
        if control_type == "Threshold":
            # Direct access to fields for Threshold commands
            threshold_value = command.get('thresholdValue')
            min_threshold = command.get('minThreshold')
            max_threshold = command.get('maxThreshold')
            error_percentage = command.get('errorPercentage')
            unit = command.get('unit')
            
            logger.info(f"Threshold command received - Device: {device}, Value: {threshold_value}, " 
                      f"Min: {min_threshold}, Max: {max_threshold}, Unit: {unit}")
                
            # Save threshold data with validated parameters
            threshold_id = save_threshold_data(
                sector,
                device,
                threshold_value,
                min_threshold,
                max_threshold,
                error_percentage,
                unit
            )
            if threshold_id is None:
                raise Exception("Failed to save threshold data")
                
            # Command data for device command table
            command_data = {
                'command': command.get('command'),
                'threshold_id': threshold_id,
                'threshold_value': threshold_value,
                'min_threshold': min_threshold,
                'max_threshold': max_threshold,
                'unit': unit
            }
        else:
            # Get additional data for non-threshold commands
            command_data = {k:v for k,v in command.items() 
                          if k not in ['sector', 'device', 'status', 'type']}

        # Save command and get ID
        command_id = save_device_command(
            sector, device, status, control_type, command_data
        )

        if command_id is None:
            raise Exception("Failed to save command")

        # Update device state
        device_key = f"{sector}_{device}"
        device_states[device_key] = {
            'status': status,
            'type': control_type,
            'last_updated': timestamp,
            'command_id': command_id
        }
        
        # Log command details
        logger.info(f"Device command received at {timestamp}")
        logger.info(f"Command details - ID: {command_id}, Sector: {sector}, Device: {device}")
        logger.info(f"Status: {status}, Type: {control_type}")
        
        # Send success response
        emit('command_response', {
            'success': True,
            'command_id': command_id,
            'device': device_key,
            'status': status,
            'received': True,
            'timestamp': timestamp,
            'message': f"Command for {device} in sector {sector} processed successfully"
        })
        
        # Broadcast update
        socketio.emit('device_update', {
            'device': device_key,
            'status': status,
            'timestamp': timestamp,
            'command_id': command_id
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error handling device command: {error_msg}")
        emit('command_response', {
            'success': False,
            'error': error_msg,
            'received': True,
            'timestamp': datetime.now().isoformat()
        })

def save_threshold_data(sector, device, threshold_value, min_threshold, max_threshold, error_percentage, unit):
    """Save threshold data to database"""
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        # Ensure we have valid values for mandatory fields to avoid NULL constraint violations
        if min_threshold is None:
            min_threshold = 0  # Default value
            logger.warning(f"No minThreshold provided for {sector}:{device}, using default value 0")
            
        if max_threshold is None:
            max_threshold = 100  # Default value
            logger.warning(f"No maxThreshold provided for {sector}:{device}, using default value 100")
            
        if unit is None:
            unit = ''  # Default empty string
            logger.warning(f"No unit provided for {sector}:{device}, using empty string")
        
        logger.info(f"Saving threshold data - Sector: {sector}, Device: {device}, " 
                   f"Min: {min_threshold}, Max: {max_threshold}, Unit: {unit}")
        
        cur.execute(
            """
            INSERT INTO Device_Thresholds (Sector, Device, MinThreshold, MaxThreshold, Unit, Status)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (Sector, Device) 
            DO UPDATE SET
                MinThreshold = EXCLUDED.MinThreshold,
                MaxThreshold = EXCLUDED.MaxThreshold,
                Unit = EXCLUDED.Unit,
                Status = TRUE,
                Timestamp = CURRENT_TIMESTAMP
            RETURNING ThresholdID
            """,
            (sector, device, min_threshold, max_threshold, unit)
        )
        
        threshold_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"Threshold data saved - ID: {threshold_id}")
        return threshold_id
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error saving threshold data: {error}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn is not None:
            conn.close()

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

def get_command_history(limit=100):
    """Get command history from database"""
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        # Query commands with proper JSON handling
        cur.execute(
            """
            SELECT CommandID, Sector, Device, Status, Type, 
                   Command_Data::text, -- Convert JSONB to text
                   Timestamp 
            FROM Device_Commands 
            ORDER BY Timestamp DESC 
            LIMIT %s
            """,
            (limit,)
        )
        
        columns = ['command_id', 'sector', 'device', 'status', 'type', 
                  'command_data', 'timestamp']
        results = []
        
        for row in cur.fetchall():
            result = dict(zip(columns, row))
            # Parse text JSON to dict
            result['command_data'] = json.loads(result['command_data'])
            result['timestamp'] = result['timestamp'].isoformat()
            results.append(result)
            
        return results
        
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error getting command history: {error}")
        return []
    finally:
        if conn is not None:
            conn.close()

# Add new route to get command history
@app.route('/api/command-history')
def api_command_history():
    try:
        history = get_command_history()
        return jsonify({
            'status': 'success',
            'time': datetime.now().isoformat(),
            'count': len(history),
            'commands': history
        })
    except Exception as e:
        logger.error(f"Error in command history API: {e}")
        return jsonify({
            'status': 'error',
            'time': datetime.now().isoformat(),
            'error': str(e)
        }), 500

def clear_device_commands():
    """Clear all device commands when the server shuts down"""
    conn = None
    try:
        logger.info("Server shutting down - clearing device commands table")
        conn = connect_db()
        if conn:
            cur = conn.cursor()
            # First try with DELETE instead of TRUNCATE for better compatibility
            cur.execute("DELETE FROM Device_Commands")
            cur.execute("ALTER SEQUENCE Device_Commands_CommandID_seq RESTART WITH 1")

            # Explicitly commit the transaction
            conn.commit()
            logger.info(f"Device commands table cleared successfully - Removed {cur.rowcount} records")
        else:
            logger.error("Failed to connect to database during shutdown")
    except Exception as e:
        logger.error(f"Error clearing device commands table: {e}")
        # If there's an error, try to log the details
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if conn is not None:
            try:
                conn.close()
                logger.info("Database connection closed during shutdown")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
        print("Device commands cleanup complete")  # Print to console as a fallback


def get_latest_temperature_data():
    """Get the latest temperature data from the Data_Temperature table"""
    conn = None
    try:
        conn = connect_db()
        if not conn:
            logger.error("Database connection returned None")
            return None
        
        cur = conn.cursor()
        
        # Query to get the latest temperature reading and threshold
        cur.execute("""
            WITH LatestTemp AS (
                SELECT dt.DataID, dt.DID, d.Dname, dt.Value, dt.Unit, dt.Status, dt.Timestamp,
                       ROW_NUMBER() OVER (PARTITION BY d.DID ORDER BY dt.Timestamp DESC) as rn
                FROM Data_Temperature dt
                JOIN Device d ON dt.DID = d.DID
            ),
            ThresholdData AS (
                SELECT MinThreshold, MaxThreshold, Unit
                FROM Device_Thresholds
                WHERE Device = 'Temperature'
                ORDER BY Timestamp DESC
                LIMIT 1
            )
            SELECT lt.*, t.MinThreshold, t.MaxThreshold
            FROM LatestTemp lt
            LEFT JOIN ThresholdData t ON true
            WHERE lt.rn = 1;
        """)
        
        result = cur.fetchone()
        
        if result:
            # Format the data as a dictionary with threshold info
            data = {
                'data_id': result[0],
                'device_id': result[1],
                'device_name': result[2],
                'value': float(result[3]),
                'unit': result[4],
                'status': result[5],
                'timestamp': result[6].isoformat(),
                'min_threshold': float(result[8]) if result[8] else None,
                'max_threshold': float(result[9]) if result[9] else None
            }
            return data
        else:
            logger.warning("No temperature data found in database")
            return None
            
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error retrieving latest temperature data: {error}")
        return None
    finally:
        if conn is not None:
            conn.close()

def get_latest_humidity_data():
    """Get the latest humidity data from the Data_Humidity table"""
    conn = None
    try:
        conn = connect_db()
        if not conn:
            logger.error("Database connection returned None")
            return None
        
        cur = conn.cursor()
        
        # Query to get the latest humidity reading and threshold
        cur.execute("""
            WITH LatestHumidity AS (
                SELECT dh.DataID, dh.DID, d.Dname, dh.Value, dh.Unit, dh.Status, dh.Timestamp,
                       ROW_NUMBER() OVER (PARTITION BY d.DID ORDER BY dh.Timestamp DESC) as rn
                FROM Data_Humidity dh
                JOIN Device d ON dh.DID = d.DID
            ),
            ThresholdData AS (
                SELECT MinThreshold, MaxThreshold, Unit
                FROM Device_Thresholds
                WHERE Device = 'Humidity'
                ORDER BY Timestamp DESC
                LIMIT 1
            )
            SELECT lh.*, t.MinThreshold, t.MaxThreshold
            FROM LatestHumidity lh
            LEFT JOIN ThresholdData t ON true
            WHERE lh.rn = 1;
        """)
        
        result = cur.fetchone()
        
        if result:
            # Format the data as a dictionary
            data = {
                'data_id': result[0],
                'device_id': result[1],
                'device_name': result[2],
                'value': float(result[3]),
                'unit': result[4],
                'status': result[5],
                'timestamp': result[6].isoformat(),
                'min_threshold': float(result[8]) if result[8] else None,
                'max_threshold': float(result[9]) if result[9] else None
            }
            return data
        else:
            logger.warning("No humidity data found in database")
            return None
            
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error retrieving latest humidity data: {error}")
        return None
    finally:
        if conn is not None:
            conn.close()

def get_latest_light_data():
    """Get the latest light data from the Data_Light table"""
    conn = None
    try:
        conn = connect_db()
        if not conn:
            logger.error("Database connection returned None")
            return None
        
        cur = conn.cursor()
        
        # Query to get the latest light reading and threshold
        cur.execute("""
            WITH LatestLight AS (
                SELECT dl.DataID, dl.DID, d.Dname, dl.Value, dl.Unit, dl.Status, dl.Timestamp,
                       ROW_NUMBER() OVER (PARTITION BY d.DID ORDER BY dl.Timestamp DESC) as rn
                FROM Data_Light dl
                JOIN Device d ON dl.DID = d.DID
            ),
            ThresholdData AS (
                SELECT MinThreshold, MaxThreshold, Unit
                FROM Device_Thresholds
                WHERE Device = 'Light' 
                ORDER BY Timestamp DESC
                LIMIT 1
            )
            SELECT ll.*, t.MinThreshold, t.MaxThreshold
            FROM LatestLight ll
            LEFT JOIN ThresholdData t ON true
            WHERE ll.rn = 1;
        """)
        
        result = cur.fetchone()
        
        if result:
            # Format the data as a dictionary
            data = {
                'data_id': result[0],
                'device_id': result[1],
                'device_name': result[2],
                'value': float(result[3]),
                'unit': result[4],
                'status': result[5],
                'timestamp': result[6].isoformat(),
                'min_threshold': float(result[8]) if result[8] else None,
                'max_threshold': float(result[9]) if result[9] else None
            }
            return data
        else:
            logger.warning("No light data found in database")
            return None
            
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error retrieving latest light data: {error}")
        return None
    finally:
        if conn is not None:
            conn.close()

def broadcast_temperature_updates():
    """Periodically broadcast temperature updates to all clients"""
    while True:
        try:
            temp_data = get_latest_temperature_data()
            if temp_data and connected_clients:
                socketio.emit('temperature_data', {
                    'success': True,
                    'data': temp_data,
                    'timestamp': datetime.now().isoformat()
                })
            time.sleep(10)  # Update every 10 seconds
        except Exception as e:
            logger.error(f"Error in temperature broadcast thread: {e}")
            time.sleep(5)  # Wait before retrying

def broadcast_humidity_updates():
    """Periodically broadcast humidity updates to all clients"""
    while True:
        try:
            humidity_data = get_latest_humidity_data()
            if humidity_data and connected_clients:
                socketio.emit('humidity_data', {
                    'success': True,
                    'data': humidity_data,
                    'timestamp': datetime.now().isoformat()
                })
            time.sleep(10)  # Update every 10 seconds
        except Exception as e:
            logger.error(f"Error in humidity broadcast thread: {e}")
            time.sleep(5)  # Wait before retrying

def broadcast_light_updates():
    """Periodically broadcast light updates to all clients"""
    while True:
        try:
            light_data = get_latest_light_data()
            if light_data and connected_clients:
                socketio.emit('light_data', {
                    'success': True,
                    'data': light_data,
                    'timestamp': datetime.now().isoformat()
                })
            time.sleep(10)  # Update every 10 seconds
        except Exception as e:
            logger.error(f"Error in light broadcast thread: {e}")
            time.sleep(5)  # Wait before retrying  

def signal_handler(sig, frame):
    print(f"Received shutdown signal {sig}, cleaning up...")
    clear_device_commands()
    atexit._run_exitfuncs()# Register signal handlers

for sig in [signal.SIGINT, signal.SIGTERM]:
    signal.signal(sig, lambda sig, frame: atexit._run_exitfuncs())

if __name__ == "__main__":
    # Record device activities for simulation
    clear_device_commands()

    # Start temperature broadcast thread
    temp_thread = threading.Thread(target=broadcast_temperature_updates)
    temp_thread.daemon = True
    temp_thread.start()
    
    # Start humidity broadcast thread
    humidity_thread = threading.Thread(target=broadcast_humidity_updates)
    humidity_thread.daemon = True
    humidity_thread.start()
    
    # Start light broadcast thread
    light_thread = threading.Thread(target=broadcast_light_updates)
    light_thread.daemon = True
    light_thread.start()
    
    # Start the Flask/SocketIO server
    print("Starting WebSocket server on port 3000")
    socketio.run(app, host='0.0.0.0', port=3000, debug=True, allow_unsafe_werkzeug=True)