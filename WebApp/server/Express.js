const express = require('express');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
const csv = require('csv-parse/sync');

const app = express();
app.use(cors());
app.use(express.json());

// Update paths to point to server/public
const CSV_FILE_PATH = path.join(__dirname, 'public', 'notes.csv');
const THRESHOLD_CSV_PATH = path.join(__dirname, 'public', 'threshold.csv');
const AUTH_CSV_PATH = path.join(__dirname, 'public', 'authenticate.csv');
const NOTIFICATIONS_CSV_PATH = path.join(__dirname, 'public', 'notifications.csv');
const ALERTS_CSV_PATH = path.join(__dirname, 'public', 'alerts.csv');

// Ensure CSV files exist with headers
if (!fs.existsSync(CSV_FILE_PATH)) {
    fs.writeFileSync(CSV_FILE_PATH, 'id,datetime,content,status\n');
}

if (!fs.existsSync(THRESHOLD_CSV_PATH)) {
    fs.writeFileSync(THRESHOLD_CSV_PATH, 'attribute,minValue,value,maxValue\n');
}

if (!fs.existsSync(AUTH_CSV_PATH)) {
    fs.writeFileSync(AUTH_CSV_PATH, 'email,password\n');
}

if (!fs.existsSync(NOTIFICATIONS_CSV_PATH)) {
    fs.writeFileSync(NOTIFICATIONS_CSV_PATH, 'id,datetime,content,status\n');
}

if (!fs.existsSync(ALERTS_CSV_PATH)) {
    fs.writeFileSync(ALERTS_CSV_PATH, 'datetime,content,status\n');
}

// Authentication endpoints
app.post('/api/auth/signup', (req, res) => {
    try {
        const { email, password } = req.body;
        if (!email || !password) {
            return res.status(400).json({ message: 'Email and password are required' });
        }

        // Ensure file exists with header
        if (!fs.existsSync(AUTH_CSV_PATH)) {
            fs.writeFileSync(AUTH_CSV_PATH, 'email,password\n');
        }

        // Read existing users
        const fileData = fs.readFileSync(AUTH_CSV_PATH, 'utf-8');
        const records = csv.parse(fileData, { columns: true, skip_empty_lines: true });

        // Check if user already exists
        if (records.some(record => record.email === email)) {
            return res.status(409).json({ message: 'Email already exists' });
        }

        // Get the file content and check if we need to add a newline
        let currentContent = fs.readFileSync(AUTH_CSV_PATH, 'utf-8');
        if (currentContent && !currentContent.endsWith('\n')) {
            currentContent += '\n';
            fs.writeFileSync(AUTH_CSV_PATH, currentContent);
        }

        // Append new user with proper line ending
        fs.appendFileSync(AUTH_CSV_PATH, `${email},${password}\n`);
        res.status(201).json({ message: 'User registered successfully' });
    } catch (error) {
        console.error('Signup error:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
});

app.post('/api/auth/login', async (req, res) => {
    try {
        const { email, password } = req.body;
        if (!email || !password) {
            return res.status(400).json({ message: 'Email and password are required' });
        }

        // Ensure authentication file exists
        if (!fs.existsSync(AUTH_CSV_PATH)) {
            fs.writeFileSync(AUTH_CSV_PATH, 'email,password\n');
            return res.status(401).json({ message: 'Account have not been registered' });
        }

        // Read and parse the authentication CSV
        const fileData = fs.readFileSync(AUTH_CSV_PATH, 'utf-8');
        if (!fileData.trim()) {
            return res.status(401).json({ message: 'Account have not been registered' });
        }

        const records = csv.parse(fileData, { 
            columns: true, 
            skip_empty_lines: true,
            trim: true 
        });
        
        // Find user and verify credentials
        const user = records.find(record => record.email.trim() === email.trim());
        if (!user) {
            return res.status(401).json({ message: 'Account have not been registered' });
        }
        if (user.password.trim() !== password.trim()) {
            return res.status(401).json({ message: 'Wrong password' });
        }

        // Handle notification
        const date = new Date().toLocaleString('en-US', { month: 'short', day: 'numeric' });
        
        // Ensure notifications file exists
        if (!fs.existsSync(NOTIFICATIONS_CSV_PATH)) {
            fs.writeFileSync(NOTIFICATIONS_CSV_PATH, 'id,datetime,user,action,status\n');
        }

        // Get next notification ID
        const notificationsContent = fs.readFileSync(NOTIFICATIONS_CSV_PATH, 'utf-8');
        let nextId = 1;
        
        if (notificationsContent.trim()) {
            const notificationRecords = csv.parse(notificationsContent, {
                columns: true,
                skip_empty_lines: true
            });
            if (notificationRecords.length > 0) {
                nextId = Math.max(...notificationRecords.map(r => parseInt(r.id))) + 1;
            }
        }        // Add login notification
        const notification = `${nextId},${date},User logged in,Completed\n`;
        fs.appendFileSync(NOTIFICATIONS_CSV_PATH, notification);

        res.json({ message: 'Login successful' });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
});

// GET endpoint to fetch notes and notifications
app.get('/api/notes', (req, res) => {
    try {
        let allRecords = [];

        // Read only from notes.csv
        if (fs.existsSync(CSV_FILE_PATH)) {
            const notesContent = fs.readFileSync(CSV_FILE_PATH, 'utf-8');
            if (notesContent.trim()) {
                const notesRecords = csv.parse(notesContent, {
                    columns: true,
                    skip_empty_lines: true
                });
                allRecords = [...notesRecords];
            }
        }

        // Sort by ID to maintain order
        allRecords.sort((a, b) => parseInt(b.id) - parseInt(a.id));
        
        res.json(allRecords);
    } catch (error) {
        console.error('Server error:', error);
        res.status(500).json({ error: error.message });
    }
});

// POST endpoint to add new notes
app.post('/api/notes', (req, res) => {
    try {
        const { content, status, datetime } = req.body;
        
        // Read existing notes to determine next ID
        let nextId = 1;
        if (fs.existsSync(CSV_FILE_PATH)) {
            const fileContent = fs.readFileSync(CSV_FILE_PATH, 'utf-8');
            if (fileContent.trim()) {
                const records = csv.parse(fileContent, {
                    columns: true,
                    skip_empty_lines: true
                });
                if (records.length > 0) {
                    nextId = Math.max(...records.map(r => parseInt(r.id))) + 1;
                }
            }
        }

        const csvLine = `${nextId},${datetime},${content},${status}\n`;
        
        if (!fs.existsSync(CSV_FILE_PATH)) {
            fs.writeFileSync(CSV_FILE_PATH, 'id,datetime,content,status\n');
        }
        
        fs.appendFileSync(CSV_FILE_PATH, csvLine);
        res.json({ success: true, id: nextId });
    } catch (error) {
        console.error('Error saving note:', error);
        res.status(500).json({ error: error.message });
    }
});

// PUT endpoint to update note status
app.put('/api/notes/:id', (req, res) => {
    try {
        const { status } = req.body;
        const id = req.params.id;
        
        // Read all notes
        const fileContent = fs.readFileSync(CSV_FILE_PATH, 'utf-8');
        const records = csv.parse(fileContent, {
            columns: true,
            skip_empty_lines: true
        });
        
        // Find and update the note
        const updatedRecords = records.map(record => 
            record.id === id ? { ...record, status } : record
        );
        
        // Write back to CSV
        const header = 'id,datetime,content,status\n';
        const csvContent = updatedRecords.map(record => 
            `${record.id},${record.datetime},${record.content},${record.status}`
        ).join('\n');
        
        fs.writeFileSync(CSV_FILE_PATH, header + csvContent + '\n');
        
        res.json({ success: true });
    } catch (error) {
        console.error('Error updating note:', error);
        res.status(500).json({ error: error.message });
    }
});

// DELETE endpoint to remove a note
app.delete('/api/notes/:id', (req, res) => {
    try {
        const id = req.params.id;
        
        // Read all notes
        const fileContent = fs.readFileSync(CSV_FILE_PATH, 'utf-8');
        const records = csv.parse(fileContent, {
            columns: true,
            skip_empty_lines: true
        });
        
        // Filter out the note to delete
        const updatedRecords = records.filter(record => record.id !== id);
        
        // Write back to CSV
        const header = 'id,datetime,content,status\n';
        const csvContent = updatedRecords.map(record => 
            `${record.id},${record.datetime},${record.content},${record.status}`
        ).join('\n');
        
        fs.writeFileSync(CSV_FILE_PATH, header + csvContent + '\n');
        
        res.json({ success: true });
    } catch (error) {
        console.error('Error deleting note:', error);
        res.status(500).json({ error: error.message });
    }
});

// POST endpoint to save threshold values
app.post('/api/threshold', (req, res) => {
    try {
        const { attribute, value, errorPercentage } = req.body;
        
        // Calculate min and max values based on error percentage
        const minValue = (value * (1 - errorPercentage/100)).toFixed(1);
        const maxValue = (value * (1 + errorPercentage/100)).toFixed(1);
        
        // Create CSV line
        const csvLine = `${attribute},${minValue},${value},${maxValue}\n`;
        
        if (!fs.existsSync(THRESHOLD_CSV_PATH)) {
            fs.writeFileSync(THRESHOLD_CSV_PATH, 'attribute,minValue,value,maxValue\n');
        }
        
        // Read existing content to check for attribute
        const fileContent = fs.readFileSync(THRESHOLD_CSV_PATH, 'utf-8');
        const records = csv.parse(fileContent, {
            columns: true,
            skip_empty_lines: true
        });
        
        // Filter out existing entry for this attribute
        const updatedRecords = records.filter(record => record.attribute !== attribute);
        
        // Write header and all records
        const header = 'attribute,minValue,value,maxValue\n';
        const csvContent = updatedRecords.map(record => 
            `${record.attribute},${record.minValue},${record.value},${record.maxValue}`
        ).join('\n');
        
        // Write the file with updated content plus new record
        fs.writeFileSync(THRESHOLD_CSV_PATH, header + csvContent + (csvContent ? '\n' : '') + `${attribute},${minValue},${value},${maxValue}\n`);
        
        res.json({ success: true });
    } catch (error) {
        console.error('Error saving threshold:', error);
        res.status(500).json({ error: error.message });
    }
});

// GET endpoint to fetch threshold values
app.get('/api/threshold', (req, res) => {
    try {
        if (!fs.existsSync(THRESHOLD_CSV_PATH)) {
            return res.json([]); 
        }
        
        const fileContent = fs.readFileSync(THRESHOLD_CSV_PATH, 'utf-8');
        if (!fileContent.trim()) {
            return res.json([]); 
        }

        const records = csv.parse(fileContent, {
            columns: true,
            skip_empty_lines: true
        });
        
        res.json(records);
    } catch (error) {
        console.error('Error fetching thresholds:', error);
        res.status(500).json({ error: error.message });
    }
});

// GET endpoint to fetch notifications
app.get('/api/notifications', (req, res) => {
    try {
        let notifications = [];

        if (fs.existsSync(NOTIFICATIONS_CSV_PATH)) {
            const notificationsContent = fs.readFileSync(NOTIFICATIONS_CSV_PATH, 'utf-8');
            if (notificationsContent.trim()) {
                notifications = csv.parse(notificationsContent, {
                    columns: true,
                    skip_empty_lines: true
                });
            }
        }

        // Sort by ID to maintain order
        notifications.sort((a, b) => parseInt(b.id) - parseInt(a.id));
        
        res.json(notifications);
    } catch (error) {
        console.error('Error fetching notifications:', error);
        res.status(500).json({ error: error.message });
    }
});

// POST endpoint to add new notifications
app.post('/api/notifications', (req, res) => {
    try {
        const { datetime, content, status } = req.body;
        
        // Ensure file exists with header
        if (!fs.existsSync(NOTIFICATIONS_CSV_PATH)) {
            fs.writeFileSync(NOTIFICATIONS_CSV_PATH, 'id,datetime,content,status\n');
        }

        // Read existing notifications to determine next ID
        const fileContent = fs.readFileSync(NOTIFICATIONS_CSV_PATH, 'utf-8');
        let nextId = 1;
        
        if (fileContent.trim()) {
            const records = csv.parse(fileContent, {
                columns: true,
                skip_empty_lines: true
            });
            if (records.length > 0) {
                nextId = Math.max(...records.map(r => parseInt(r.id))) + 1;
            }
        }

        // Create CSV line
        const csvLine = `${nextId},${datetime},${content},${status}\n`;
        
        // Append new notification
        fs.appendFileSync(NOTIFICATIONS_CSV_PATH, csvLine);
        
        res.json({ success: true, id: nextId });
    } catch (error) {
        console.error('Error saving notification:', error);
        res.status(500).json({ error: error.message });
    }
});

// Alert endpoints
app.post('/api/alerts', (req, res) => {
    try {
        const { sensor, value, threshold } = req.body;
        
        // Create alert in the proper format
        const datetime = new Date().toISOString();
        
        // Handle different sensor types
        const content = `${sensor} ${value <= threshold ? 'is near' : 'has reached'} the threshold`;
        const status = value <= threshold ? 'warning' : 'critical';
        
        // Ensure file exists with header
        if (!fs.existsSync(ALERTS_CSV_PATH)) {
            fs.writeFileSync(ALERTS_CSV_PATH, 'datetime,content,status\n');
        }

        // Get the file content and check if we need to add a newline
        let currentContent = fs.readFileSync(ALERTS_CSV_PATH, 'utf-8');
        if (currentContent && !currentContent.endsWith('\n')) {
            currentContent += '\n';
            fs.writeFileSync(ALERTS_CSV_PATH, currentContent);
        }
        
        // Append new alert
        fs.appendFileSync(ALERTS_CSV_PATH, `${datetime},${content},${status}\n`);
        
        res.json({ success: true });
    } catch (error) {
        console.error('Error saving alert:', error);
        res.status(500).json({ message: 'Failed to save alert' });
    }
});

app.get('/api/alerts', (req, res) => {
    try {
        // Ensure file exists with header
        if (!fs.existsSync(ALERTS_CSV_PATH)) {
            fs.writeFileSync(ALERTS_CSV_PATH, 'datetime,content,status\n');
            return res.json([]);
        }

        // Read alerts from CSV
        const fileData = fs.readFileSync(ALERTS_CSV_PATH, 'utf-8');
        if (!fileData.trim()) {
            return res.json([]);
        }

        const alerts = csv.parse(fileData, { 
            columns: true, 
            skip_empty_lines: true,
            trim: true
        });
        
        // Sort alerts by datetime (most recent first)
        alerts.sort((a, b) => new Date(b.datetime) - new Date(a.datetime));
        
        res.json(alerts);
    } catch (error) {
        console.error('Error reading alerts:', error);
        res.status(500).json({ message: 'Failed to fetch alerts' });
    }
});

// DELETE endpoint to remove an alert
app.delete('/api/alerts/:datetime', (req, res) => {
    try {
        const targetDatetime = req.params.datetime;
        
        // Read all alerts
        const fileContent = fs.readFileSync(ALERTS_CSV_PATH, 'utf-8');
        const alerts = csv.parse(fileContent, {
            columns: true,
            skip_empty_lines: true
        });
        
        // Filter out the alert to delete
        const updatedAlerts = alerts.filter(alert => alert.datetime !== targetDatetime);
        
        // Write back to CSV
        const header = 'datetime,content,status\n';
        const csvContent = updatedAlerts.map(alert => 
            `${alert.datetime},${alert.content},${alert.status}`
        ).join('\n');
        
        fs.writeFileSync(ALERTS_CSV_PATH, header + csvContent + (csvContent ? '\n' : ''));
        
        res.json({ success: true });
    } catch (error) {
        console.error('Error deleting alert:', error);
        res.status(500).json({ message: 'Failed to delete alert' });
    }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});