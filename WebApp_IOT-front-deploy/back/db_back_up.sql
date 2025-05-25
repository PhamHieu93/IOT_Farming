-- Database backup created at 2025-05-25T15:12:58.624045

-- Recreate tables
-- Create Device table
CREATE TABLE IF NOT EXISTS Device (
    DID INTEGER PRIMARY KEY,
    Dname VARCHAR(100),
    Location VARCHAR(100),
    Type VARCHAR(50),
    status JSONB
);

-- Create Data table
CREATE TABLE IF NOT EXISTS Data (
    DataID INTEGER PRIMARY KEY,
    DID INTEGER REFERENCES Device(DID),
    Value DECIMAL,
    Unit VARCHAR(10),
    Status VARCHAR(20),
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Device_Activity table
CREATE TABLE IF NOT EXISTS Device_Activity (
    ActivityID INTEGER PRIMARY KEY,
    DID INTEGER REFERENCES Device(DID),
    Action VARCHAR(100),
    Status VARCHAR(50),
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Device_Commands table to store command history
CREATE TABLE IF NOT EXISTS Device_Commands (
    CommandID SERIAL PRIMARY KEY,                -- Auto-incrementing ID
    Sector VARCHAR(50) NOT NULL,                 -- Sector where device is located (e.g. 'A', 'B')
    Device VARCHAR(100) NOT NULL,                -- Device name (e.g. 'Light', 'Fan')
    Status BOOLEAN NOT NULL,                     -- Device status (true/false)
    Type VARCHAR(50) NOT NULL,                   -- Control type (e.g. 'Manual', 'Schedule', 'Auto')
    Command_Data JSONB DEFAULT '{}',             -- Additional command data in JSON format
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- When command was issued
);

-- Create index for faster querying
CREATE INDEX IF NOT EXISTS idx_device_commands_timestamp 
ON Device_Commands(Timestamp DESC);

-- Create index for searching by sector and device
CREATE INDEX IF NOT EXISTS idx_device_commands_sector_device 
ON Device_Commands(Sector, Device);


-- Device Commands Data
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (1, 'A', 'Light', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 12:12:52.353437'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (2, 'A', 'Light', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 12:17:27.133055'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (3, 'A', 'Light', True, 'On/Off', '{"command": "start"}'::jsonb, '2025-05-25 12:17:28.360875'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (4, 'A', 'Light', True, 'On/Off', '{"command": "start"}'::jsonb, '2025-05-25 12:17:33.811908'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (5, 'A', 'Light', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 12:17:36.890838'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (6, 'A', 'Pump', True, 'Schedule', '{}'::jsonb, '2025-05-25 12:17:38.460192'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (7, 'A', 'Pump', False, 'Schedule', '{}'::jsonb, '2025-05-25 12:17:38.956702'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (8, 'A', 'Light', True, 'On/Off', '{"command": "start"}'::jsonb, '2025-05-25 12:18:06.186036'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (9, 'A', 'Motor Fan', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 12:18:07.600055'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (10, 'A', 'Light', True, 'On/Off', '{"command": "start"}'::jsonb, '2025-05-25 12:19:55.090747'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (11, 'A', 'Light', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 12:19:56.188549'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (12, 'A', 'Light', True, 'On/Off', '{"command": "start"}'::jsonb, '2025-05-25 12:19:56.841401'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (13, 'A', 'Light', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 14:31:53.183243'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (14, 'A', 'Motor Fan', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 14:31:53.774464'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (15, 'A', 'Light', True, 'On/Off', '{"command": "start"}'::jsonb, '2025-05-25 14:35:41.593311'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (16, 'B', 'Light', True, 'Schedule', '{"command": "start", "endTime": "23:59", "startTime": "00:00"}'::jsonb, '2025-05-25 14:37:10.421407'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (17, 'A', 'Light', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 14:40:57.811169'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (18, 'A', 'Motor Fan', True, 'On/Off', '{"command": "start"}'::jsonb, '2025-05-25 14:40:59.235769'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (19, 'A', 'Pump', True, 'Schedule', '{"command": "start", "endTime": "23:59", "startTime": "00:00"}'::jsonb, '2025-05-25 14:41:02.006303'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (20, 'A', 'Motor Fan', False, 'On/Off', '{}'::jsonb, '2025-05-25 14:41:26.129809'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (21, 'A', 'Motor Fan', True, 'On/Off', '{}'::jsonb, '2025-05-25 14:41:27.929180'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (22, 'A', 'Light', False, 'Manual', '{}'::jsonb, '2025-05-25 14:41:30.213461'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (23, 'A', 'Light', True, 'Manual', '{}'::jsonb, '2025-05-25 14:41:30.554524'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (24, 'A', 'Pump', True, 'Schedule', '{"command": "start", "endTime": "23:59", "startTime": "00:00"}'::jsonb, '2025-05-25 14:41:59.181942'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (25, 'A', 'Motor Fan', True, 'On/Off', '{"command": "start"}'::jsonb, '2025-05-25 14:42:00.171535'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (26, 'A', 'Light', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 14:42:01.602343'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (27, 'B', 'Motor Fan', True, 'Manual', '{"command": "start"}'::jsonb, '2025-05-25 14:43:34.364284'::timestamp);
INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) VALUES (28, 'B', 'Motor Fan', False, 'Manual', '{}'::jsonb, '2025-05-25 14:43:53.995052'::timestamp);

-- Device Data
INSERT INTO Device (DID, Dname, Location, Type, status) VALUES (2, 'Humidity Monitor', 'Greenhouse', 'humidity', '{"id": "humidity002", "name": "Humidity Monitor", "type": "humidity", "unit": "%", "model": "IOT Farming Sensor v2", "status": "normal", "location": {"area": "Center", "zone": "Greenhouse", "position": "Ceiling"}, "lastValue": 57.7, "threshold": {"max": 80, "min": 40, "warningMax": 75, "warningMin": 45, "criticalMax": 85, "criticalMin": 30}, "indicColor": "#FF9733", "installDate": "2024-01-15", "lastUpdated": "2025-05-25T15:12:30.755704", "batteryLevel": 76, "serialNumber": "IOT-2025-0002", "firmwareVersion": "2.1.0", "readingInterval": 5}'::jsonb);
INSERT INTO Device (DID, Dname, Location, Type, status) VALUES (3, 'Soil Moisture Sensor', 'Field', 'soil_moisture', '{"id": "soil_moisture003", "name": "Soil Moisture Sensor", "type": "soil_moisture", "unit": "%", "model": "IOT Farming Sensor v2", "status": "warning", "location": {"area": "East", "zone": "Field", "position": "Ground"}, "lastValue": 62.4, "threshold": {"max": 60, "min": 20, "warningMax": 55, "warningMin": 25, "criticalMax": 65, "criticalMin": 15}, "indicColor": "#FF3333", "installDate": "2024-01-15", "lastUpdated": "2025-05-25T15:12:30.828876", "batteryLevel": 87, "serialNumber": "IOT-2025-0003", "firmwareVersion": "2.1.0", "readingInterval": 5}'::jsonb);
INSERT INTO Device (DID, Dname, Location, Type, status) VALUES (1, 'Greenhouse Temperature Sensor', 'Greenhouse', 'temperature', '{"id": "temperature001", "name": "Greenhouse Temperature Sensor", "type": "temperature", "unit": "\u00b0C", "model": "IOT Farming Sensor v2", "status": "normal", "location": {"area": "North", "zone": "Greenhouse", "position": "Wall"}, "lastValue": 20.4, "threshold": {"max": 28, "min": 18, "warningMax": 26, "warningMin": 20, "criticalMax": 30, "criticalMin": 15}, "indicColor": "#FF9733", "installDate": "2024-01-15", "lastUpdated": "2025-05-25T15:12:30.681962", "batteryLevel": 92, "serialNumber": "IOT-2025-0001", "firmwareVersion": "2.1.0", "readingInterval": 5}'::jsonb);
