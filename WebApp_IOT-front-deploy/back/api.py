from flask import Flask, jsonify
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'database': 'master',  # Replace with your database name
    'user': 'postgres',         # Replace with your username
    'password': '09032004',     # Replace with your password
    'port': 5432
}

def get_db_connection():
    """Create a database connection"""
    conn = psycopg2.connect(**DB_PARAMS)
    conn.autocommit = True
    return conn

@app.route('/api/sensors/data', methods=['GET'])
def get_sensors_data():
    """Get all sensor data for the dashboard"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query to get latest sensor readings grouped by sensor type
        cursor.execute("""
            SELECT s.sensor_type, d.value, d.timestamp, s.unit
            FROM sensor_data d
            JOIN sensors s ON d.sensor_id = s.id
            WHERE d.timestamp IN (
                SELECT MAX(timestamp) 
                FROM sensor_data 
                GROUP BY sensor_id
            )
            ORDER BY s.sensor_type;
        """)
        
        latest_readings = cursor.fetchall()
        
        # Query to get historical data for charts
        cursor.execute("""
            SELECT s.sensor_type, d.value, d.timestamp
            FROM sensor_data d
            JOIN sensors s ON d.sensor_id = s.id
            WHERE d.timestamp > NOW() - INTERVAL '30 days'
            ORDER BY s.sensor_type, d.timestamp;
        """)
        
        historical_data = cursor.fetchall()
        
        # Format the data for the frontend
        sensors = {}
        chart_data = []
        
        # Process latest readings
        for row in latest_readings:
            sensor_type, value, timestamp, unit = row
            
            if sensor_type not in sensors:
                sensors[sensor_type] = {
                    'id': sensor_type.lower(),
                    'name': sensor_type,
                    'value': value,
                    'unit': unit,
                }
        
        # Process historical data for charts
        sensor_history = {}
        for row in historical_data:
            sensor_type, value, timestamp = row
            
            date_str = timestamp.strftime("%b %d")
            if date_str not in sensor_history:
                sensor_history[date_str] = {}
            
            sensor_history[date_str][sensor_type.lower()] = value
        
        # Convert to array for chart data
        for date, values in sensor_history.items():
            data_point = {'name': date}
            data_point.update(values)
            chart_data.append(data_point)
        
        # Query for humidity data for specific chart
        cursor.execute("""
            SELECT d.timestamp, d.value
            FROM sensor_data d
            JOIN sensors s ON d.sensor_id = s.id
            WHERE s.sensor_type = 'Humidity'
            AND d.timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY d.timestamp DESC
            LIMIT 24;
        """)
        
        humidity_data = []
        for row in cursor.fetchall():
            timestamp, value = row
            humidity_data.append({
                'name': timestamp.strftime("%H:%M"),
                'value': value
            })
        
        return jsonify({
            'success': True,
            'sensors': list(sensors.values()),
            'chartData': chart_data,
            'humidityData': humidity_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)