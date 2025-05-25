import psycopg2
import json
import time
import random
import os
import logging
from datetime import datetime
from config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IOT_database")

# In-memory storage as fallback when database is unavailable
fallback_storage = {
    "telemetry_data": [],
    "device_status": {},
    "device_activity": []
}

# Maximum number of connection retries
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def connect_db(retries=MAX_RETRIES):
    """Connect to the PostgreSQL database server with retry logic"""
    conn = None
    attempt = 0
    
    while attempt < retries:
        try:
            # Read connection parameters
            params = config()
            logger.info(f"Connecting to database (attempt {attempt+1}/{retries})...")
            conn = psycopg2.connect(**params)
            logger.info("Database connection established successfully")
            return conn
        except psycopg2.OperationalError as error:
            attempt += 1
            logger.error(f"Database connection failed (attempt {attempt}/{retries}): {error}")
            if attempt < retries:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
        except Exception as error:
            logger.error(f"Unexpected database error: {error}")
            break
            
    logger.warning("All database connection attempts failed. Using fallback storage.")
    return None

def send_telemetry_data(device_id, data_value, data_unit, data_status="normal"):
    """Send telemetry data to the Data table"""
    conn = None
    data_id = None
    
    try:
        conn = connect_db()
        if conn is None:
            # Use fallback storage if database connection fails
            data_id = len(fallback_storage["telemetry_data"]) + 1
            data_record = {
                "DataID": data_id,
                "DID": device_id,
                "Value": data_value,
                "Unit": data_unit,
                "Status": data_status,
                "Timestamp": datetime.now().isoformat()
            }
            fallback_storage["telemetry_data"].append(data_record)
            logger.info(f"Telemetry data stored in fallback storage - Device: {device_id}, Value: {data_value} {data_unit}")
            return data_id
        
        cur = conn.cursor()
        # Get the next DataID
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
        logger.info(f"Telemetry data sent to database - Device: {device_id}, Value: {data_value} {data_unit}")
        return data_id
    
    except Exception as error:
        logger.error(f"Error sending telemetry data: {error}")
        # Try fallback storage on error
        if data_id is None:
            data_id = len(fallback_storage["telemetry_data"]) + 1
            
        data_record = {
            "DataID": data_id,
            "DID": device_id,
            "Value": data_value,
            "Unit": data_unit,
            "Status": data_status,
            "Timestamp": datetime.now().isoformat(),
            "Error": str(error)
        }
        fallback_storage["telemetry_data"].append(data_record)
        logger.info(f"Telemetry data stored in fallback storage after error - Device: {device_id}")
        return data_id
    finally:
        if conn is not None:
            conn.close()

def update_device_status(device_id, device_name, device_type, current_value, unit):
    """Update device status in JSON format"""
    conn = None
    try:
        conn = connect_db()
        
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
        
        if conn is None:
            # Use fallback storage if connection fails
            fallback_storage["device_status"][f"{device_id}"] = status_json
            logger.info(f"Device status updated in fallback storage - Device: {device_id}, Status: {status}")
            return True
        
        cur = conn.cursor()
        # Get current device status if exists
        cur.execute("SELECT status FROM Device WHERE DID = %s", (device_id,))
        result = cur.fetchone()
        
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
        logger.info(f"Device status updated in database - Device: {device_id}, Status: {status}")
        return True
    
    except Exception as error:
        logger.error(f"Error updating device status: {error}")
        # Use fallback storage if there's an error
        fallback_storage["device_status"][f"{device_id}"] = status_json
        logger.info(f"Device status updated in fallback storage after error - Device: {device_id}")
        return True
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
    
    logger.info("Starting telemetry simulation...")
    logger.info("-" * 50)
    
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
                
                logger.info(f"Data point ID: {data_id} sent successfully")
                logger.info("-" * 50)
                
            # Wait before next batch of readings
            time.sleep(2)
            
    except Exception as e:
        logger.error(f"Error in telemetry simulation: {e}")
    
    logger.info("Telemetry simulation completed")

def add_device_activity(device_id, action, status="Active"):
    """Record device activity in the Device_Activity table"""
    conn = None
    try:
        conn = connect_db()
        
        if conn is None:
            # Use fallback storage if database connection fails
            activity_id = len(fallback_storage["device_activity"]) + 1
            activity_record = {
                "ActivityID": activity_id,
                "DID": device_id,
                "Action": action,
                "Status": status,
                "Timestamp": datetime.now().isoformat()
            }
            fallback_storage["device_activity"].append(activity_record)
            logger.info(f"Device activity recorded in fallback storage - Device: {device_id}, Action: {action}")
            return True
        
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
        logger.info(f"Device activity recorded in database - Device: {device_id}, Action: {action}, Status: {status}")
        return True
    
    except Exception as error:
        logger.error(f"Error recording device activity: {error}")
        # Use fallback storage if there's an error
        activity_id = len(fallback_storage["device_activity"]) + 1
        activity_record = {
            "ActivityID": activity_id,
            "DID": device_id,
            "Action": action,
            "Status": status,
            "Timestamp": datetime.now().isoformat(),
            "Error": str(error)
        }
        fallback_storage["device_activity"].append(activity_record)
        logger.info(f"Device activity recorded in fallback storage after error - Device: {device_id}, Action: {action}")
        return True
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    # Display welcome message
    print("=" * 60)
    print("IOT FARMING DATABASE SIMULATOR".center(60))
    print("=" * 60)
    
    # Check if database is available
    test_conn = connect_db(retries=1)
    if test_conn:
        print("✅ Database connection successful!")
        test_conn.close()
    else:
        print("⚠️  Database connection failed - using fallback storage")
        print("   Check database.ini file or environment variables for correct credentials")
    
    print("\n" + "-" * 60)
    
    # Record device activities for simulation
    for device_id in [1, 2, 3]:
        add_device_activity(device_id, "Start Telemetry")
    
    # Start simulation
    simulate_telemetry()
    
    # Record end activities
    for device_id in [1, 2, 3]:
        add_device_activity(device_id, "End Telemetry")
        
    # Summary of fallback storage if used
    if len(fallback_storage["telemetry_data"]) > 0:
        print("\n" + "=" * 60)
        print("FALLBACK STORAGE SUMMARY".center(60))
        print("=" * 60)
        print(f"Telemetry data records: {len(fallback_storage['telemetry_data'])}")
        print(f"Device status records: {len(fallback_storage['device_status'])}")
        print(f"Device activity records: {len(fallback_storage['device_activity'])}")
        print("-" * 60)