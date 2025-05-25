-- First create the custom enum types
CREATE TYPE reminder_status_type AS ENUM ('Unread', 'Read');
CREATE TYPE notification_type AS ENUM (
    'reminder', 'device', 'control', 'system', 
    'info', 'warning', 'critical', 'success'
);
CREATE TYPE severity_type AS ENUM ('low', 'medium', 'high');
CREATE TYPE device_status_type AS ENUM (
    'Active', 'Offline', 'Error', 'Maintenance', 'Disabled'
);

-- Now create the tables using those types
CREATE TABLE Reminder (
    ReminderID INT PRIMARY KEY,
    Tiltle VARCHAR(255) NOT NULL,
    Description TEXT,
    Time TIMESTAMP,
    Status reminder_status_type
);

CREATE TABLE Notification (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type notification_type,
    timestamp TIMESTAMP,
    read BOOLEAN DEFAULT FALSE,
    source VARCHAR(255)
);

CREATE TABLE Device (
    DID INT PRIMARY KEY,
    Dname VARCHAR(255) NOT NULL,
    Location VARCHAR(255),
    Type VARCHAR(100),
    status JSONB
);

CREATE TABLE Data (
    DataID INT PRIMARY KEY,
    DID INT,
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Value FLOAT,
    Unit VARCHAR(50),
    Status VARCHAR(50),
    FOREIGN KEY (DID) REFERENCES Device(DID)
);

CREATE TABLE PlantPhoto (
    id VARCHAR(255) PRIMARY KEY,
    plantId VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    illness BOOLEAN NOT NULL,
    notes TEXT
);

CREATE TABLE PlantIllness (
    photoId VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    severity severity_type NOT NULL,
    description TEXT NOT NULL,
    symptoms TEXT NOT NULL,
    causes TEXT NOT NULL,
    solutions TEXT NOT NULL,
    FOREIGN KEY (photoId) REFERENCES PlantPhoto(id)
);

CREATE TABLE Plant (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    position VARCHAR(255),
    species VARCHAR(255) NOT NULL,
    plantedDate DATE,
    lastChecked DATE
);

CREATE TABLE Device_Activity (
    ActivityID INT PRIMARY KEY,
    DID INT,
    Action VARCHAR(255) NOT NULL,
    Status device_status_type,
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (DID) REFERENCES Device(DID) ON DELETE CASCADE
);