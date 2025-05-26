-- Create Device table
CREATE TABLE IF NOT EXISTS Device (
    DID INTEGER PRIMARY KEY,
    Dname VARCHAR(100),
    Location VARCHAR(100),
    Type VARCHAR(50),
    status JSONB
);


-- Create Data table for temperature
CREATE TABLE IF NOT EXISTS Data_Temperature (
    DataID INTEGER PRIMARY KEY,
    DID INTEGER REFERENCES Device(DID),
    Value DECIMAL,
    Unit VARCHAR(10),
    Status VARCHAR(20),
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Data_Humidity (
    DataID INTEGER PRIMARY KEY,
    DID INTEGER REFERENCES Device(DID),
    Value DECIMAL,
    Unit VARCHAR(10),
    Status VARCHAR(20),
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS Data_Light (
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

CREATE TABLE IF NOT EXISTS Device_Thresholds (
    ThresholdID SERIAL PRIMARY KEY,
    Sector VARCHAR(255) NOT NULL,
    Device VARCHAR(255) NOT NULL,
    MinThreshold DECIMAL(10, 2) NOT NULL,
    MaxThreshold DECIMAL(10, 2) NOT NULL,
    Unit VARCHAR(50),
    Status BOOLEAN DEFAULT TRUE,
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(Sector, Device)
);

-- Create index for searching by sector and device
CREATE INDEX IF NOT EXISTS idx_device_commands_sector_device 
ON Device_Commands(Sector, Device);

INSERT INTO Device (DID, Dname, Location, Type, status)
VALUES (1, 'Temperature Sensor 1', 'HCMUT', 'Sensor', '{"active": true}'::jsonb);

INSERT INTO Data_Temperature (DataID, DID, Value, Unit, Status)
VALUES (1, 1, 23.5, '°C', 'Normal');

INSERT INTO Data_Light (DataID, DID, Value, Unit, Status)
VALUES (1, 1, 245, 'lux', 'Normal');

INSERT INTO Data_Humidity (DataID, DID, Value, Unit, Status)
VALUES (1, 1, 60, '%', 'Normal');

SELECT * FROM public.device
ORDER BY DID ASC