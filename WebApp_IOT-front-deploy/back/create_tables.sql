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
