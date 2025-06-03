import React, { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import "./Control.scss";
import { FaArrowLeft, FaArrowRight, FaTimes } from "react-icons/fa";
import Header from "../components/Header.jsx";
import { sendAttributes, DEVICE_INFO } from "../services/coreIOT.jsx";

const Control = () => {
    const [activePanel, setActivePanel] = useState("Panel A1");
    const [activeSector, setActiveSector] = useState(() => {
        // Load last active sector from localStorage or default to "A"
        return localStorage.getItem('lastActiveSector') || "A";
    });
    const [notification, setNotification] = useState({ show: false, message: '', type: 'info' });
    
    // Default sensor data structure
    const [sensorData, setSensorData] = useState({
        temperature: null,
        humidity: null,
        light: null,
        lastUpdated: null
    });

    // Load sector groups from localStorage or use defaults
    const [sectorGroups, setSectorGroups] = useState(() => {
        const savedSectorGroups = localStorage.getItem('sectorGroups');
        return savedSectorGroups ? JSON.parse(savedSectorGroups) : {
            'A': [
                { id: "Light", status: false, type: "Schedule" },
                { id: "Motor Fan", status: false, type: "Schedule" },
                { id: "Pump", status: false, type: "Schedule" },
                
            ],
            'B': [
                { id: "Light", status: false, type: "Schedule" },
                { id: "Motor Fan", status: false, type: "Schedule" },
                { id: "Pump", status: false, type: "Schedule" },
            ],
            'C': [
                { id: "Light", status: false, type: "Schedule" },
                { id: "Motor Fan", status: false, type: "Schedule" },
                { id: "Pump", status: false, type: "Schedule" },
            ],
            'D': [
                { id: "Light", status: false, type: "Schedule" },
                { id: "Motor Fan", status: false, type: "Schedule" },
                { id: "Pump", status: false, type: "Schedule" },
            ]
        };
    });

    // Load threshold groups from localStorage or use defaults
    const [sectorGroupsThreshold, setSectorGroupsThreshold] = useState(() => {
        const savedThresholds = localStorage.getItem('sectorGroupsThreshold');
        return savedThresholds ? JSON.parse(savedThresholds) : {
            'A': [
                { id: "Temperature", thresholdValue: 25, thresholdUnit: "°C" },
                { id: "Humidity", thresholdValue: 60, thresholdUnit: "%" },
                { id: "Light", thresholdValue: 300, thresholdUnit: "lux" },
                
            ],
            'B': [
                { id: "Temperature", thresholdValue: 25, thresholdUnit: "°C" },
                { id: "Humidity", thresholdValue: 60, thresholdUnit: "%" },
                { id: "Light", thresholdValue: 300, thresholdUnit: "lux" },
            ],
            'C': [
                { id: "Temperature", thresholdValue: 25, thresholdUnit: "°C" },
                { id: "Humidity", thresholdValue: 60, thresholdUnit: "%" },
                { id: "Light", thresholdValue: 300, thresholdUnit: "lux" },
            ],
            'D': [
                { id: "Temperature", thresholdValue: 25, thresholdUnit: "°C" },
                { id: "Humidity", thresholdValue: 60, thresholdUnit: "%" },
                { id: "Light", thresholdValue: 300, thresholdUnit: "lux" },
            ]
        };
    });

    // Load time settings from localStorage or use defaults  
    const [timeSettings, setTimeSettings] = useState(() => {
        const savedTimeSettings = localStorage.getItem('timeSettings');
        return savedTimeSettings ? JSON.parse(savedTimeSettings) : {
            'A': [
                { startTime: "00:00", endTime: "23:59" },
                { startTime: "00:00", endTime: "23:59" },
                { startTime: "00:00", endTime: "23:59" }
            ],
            'B': [
                { startTime: "00:00", endTime: "23:59" },
                { startTime: "00:00", endTime: "23:59" },
                { startTime: "00:00", endTime: "23:59" }
            ],
            'C': [
                { startTime: "00:00", endTime: "23:59" },
                { startTime: "00:00", endTime: "23:59" },
                { startTime: "00:00", endTime: "23:59" }
            ],
            'D': [
                { startTime: "00:00", endTime: "23:59" },
                { startTime: "00:00", endTime: "23:59" },
                { startTime: "00:00", endTime: "23:59" }
            ]
        };
    });

    const [showTimeModal, setShowTimeModal] = useState(false);
    const [selectedGroupIndex, setSelectedGroupIndex] = useState(null);

    // Add new state for threshold display values
    const [currentThresholds, setCurrentThresholds] = useState({
        Temperature: { value: null, minValue: null, maxValue: null },
        Humidity: { value: null, minValue: null, maxValue: null },
        Light: { value: null, minValue: null, maxValue: null }
    });

    const showNotification = (message, type = 'info') => {
        setNotification({ show: true, message, type });
        setTimeout(() => setNotification({ show: false, message: '', type: 'info' }), 3000);
    };    
    const toggleStatus = async (index, isThresholdDevice = false) => {
        try {
            if (isThresholdDevice) {
                const newSectorGroupsThreshold = { ...sectorGroupsThreshold };
                newSectorGroupsThreshold[activeSector][index].status = !newSectorGroupsThreshold[activeSector][index].status;
                setSectorGroupsThreshold(newSectorGroupsThreshold);
                localStorage.setItem('sectorGroupsThreshold', JSON.stringify(newSectorGroupsThreshold));
                const device = newSectorGroupsThreshold[activeSector][index];
                
                // Save notification for threshold device toggle
                const notificationContent = `${device.id} threshold monitoring ${device.status ? 'activated' : 'deactivated'} in Sector ${activeSector}`;
                await fetch('http://localhost:3000/api/notifications', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        datetime: new Date().toLocaleString('en-US', { month: 'short', day: 'numeric' }),
                        content: notificationContent,
                        status: "Completed"
                    })
                });
                
                showNotification(`${device.id} threshold monitoring ${device.status ? 'activated' : 'deactivated'}`, 'success');
            } else {
                const newSectorGroups = { ...sectorGroups };
                newSectorGroups[activeSector][index].status = !newSectorGroups[activeSector][index].status;
                setSectorGroups(newSectorGroups);
                localStorage.setItem('sectorGroups', JSON.stringify(newSectorGroups));
                const device = newSectorGroups[activeSector][index];
                
                // Save notification for device toggle
                const notificationContent = `${device.id} ${device.status ? 'turned on' : 'turned off'} in Sector ${activeSector}`;
                await fetch('http://localhost:3000/api/notifications', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        datetime: new Date().toLocaleString('en-US', { month: 'short', day: 'numeric' }),
                        content: notificationContent,
                        status: "Completed"
                    })
                });
                
                showNotification(`${device.id} ${device.status ? 'turned on' : 'turned off'}`, 'success');
            }
        } catch (error) {
            console.error("Error toggling device status:", error);
            showNotification('An error occurred while toggling device status', 'error');
        }
    };    

    const setControlType = (index, type) => {
        try {
            const newSectorGroups = { ...sectorGroups };
            const device = newSectorGroups[activeSector][index];
            device.type = type;
            setSectorGroups(newSectorGroups);
            localStorage.setItem('sectorGroups', JSON.stringify(newSectorGroups));

            if (type === "Schedule") {
                setSelectedGroupIndex(index);
                setShowTimeModal(true);
                return;
            }
            
            showNotification(`Control type changed to ${type}`, 'success');
        } catch (error) {
            console.error("Error changing control type:", error);
            showNotification('An error occurred while changing control type', 'error');
        }
    };    const handleStartButton = async (index, isThresholdDevice = false) => {
        try {
            if (isThresholdDevice) {
                const device = sectorGroupsThreshold[activeSector][index];
                
                // Save threshold value to server
                const response = await fetch('http://localhost:3000/api/threshold', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        attribute: device.id,
                        value: device.thresholdValue,
                        errorPercentage: device.errorPercentage || 10
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to save threshold value');
                }

                // Add threshold fetch after saving
                await fetchThresholds();

                // Save notification for threshold action
                const notificationResponse = await fetch('http://localhost:3000/api/notifications', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        datetime: new Date().toLocaleString('en-US', { month: 'short', day: 'numeric' }),
                        content: `Set threshold for ${device.id} to ${device.thresholdValue} ${device.id === "Temperature" ? "°C" : device.id === "Humidity" ? "%" : "lux"} in Sector ${activeSector}`,
                        status: "Completed"
                    })
                });

                if (!notificationResponse.ok) {
                    throw new Error('Failed to save notification');
                }

                const newSectorGroupsThreshold = { ...sectorGroupsThreshold };
                newSectorGroupsThreshold[activeSector][index].status = true;
                setSectorGroupsThreshold(newSectorGroupsThreshold);
                localStorage.setItem('sectorGroupsThreshold', JSON.stringify(newSectorGroupsThreshold));
                showNotification(`Started ${device.id} threshold monitoring and saved threshold values`, 'success');
            } else {
                const device = sectorGroups[activeSector][index];
                
                // If type is On or Off, send data to CoreIOT
                if (device.type === "On" || device.type === "Off") {
                    const entityType = 'DEVICE';
                    const entityId = DEVICE_INFO['1'].entityId;
                    const value = device.type === "On" ? 1 : 0;
                    
                    let attributeData = {};
                    switch (device.id) {
                        case "Light":
                            attributeData = { light_motor: value };
                            break;
                        case "Motor Fan":
                            attributeData = { fan_motor: value };
                            break;
                        case "Pump":
                            attributeData = { pump_motor: value };
                            break;
                    }

                    // Debug log
                    console.log('Sending control data:', {
                        entityType,
                        entityId,
                        device: device.id,
                        type: device.type,
                        value,
                        attributeData
                    });

                    // Send data using sendAttributes from coreIOT.jsx
                    await sendAttributes(entityType, entityId, attributeData);
                }
                
                // Save notification for device action
                const notificationResponse = await fetch('http://localhost:3000/api/notifications', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        datetime: new Date().toLocaleString('en-US', { month: 'short', day: 'numeric' }),
                        content: `Started ${device.id} in ${device.type} mode in Sector ${activeSector}`,
                        status: "Completed"
                    })
                });

                if (!notificationResponse.ok) {
                    throw new Error('Failed to save notification');
                }

                const newSectorGroups = { ...sectorGroups };
                newSectorGroups[activeSector][index].status = true;
                newSectorGroups[activeSector][index].type = device.type; // Save the control type
                setSectorGroups(newSectorGroups);
                localStorage.setItem('sectorGroups', JSON.stringify(newSectorGroups));
                
                const message = device.type === "On" 
                    ? `Started ${device.id} in ${device.type} mode and sent control signal to device` 
                    : `Started ${device.id} in ${device.type} mode`;
                showNotification(message, 'success');
            }
        } catch (error) {
            console.error("Error starting device:", error);
            showNotification('An error occurred while starting the device', 'error');
        }
    };

    const handleSectorChange = (sector) => {
        setActiveSector(sector);
        localStorage.setItem('lastActiveSector', sector);
    };
    
    const handleTimeSettingsChange = (field, value) => {
        if (selectedGroupIndex !== null) {
            const newTimeSettings = { ...timeSettings };
            newTimeSettings[activeSector][selectedGroupIndex][field] = value;
            setTimeSettings(newTimeSettings);
        }
    };

    const saveTimeSettings = async () => {
        if (selectedGroupIndex !== null) {
            const device = sectorGroups[activeSector][selectedGroupIndex];
            const timeRange = timeSettings[activeSector][selectedGroupIndex];
            
            // Save schedule action to notifications
            const notificationContent = `Scheduled ${device.id} from ${timeRange.startTime} to ${timeRange.endTime} in Sector ${activeSector}`;
            await fetch('http://localhost:3000/api/notifications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    datetime: new Date().toLocaleString('en-US', { month: 'short', day: 'numeric' }),
                    content: notificationContent,
                    status: "Completed"
                })
            });
            
            showNotification(`Schedule settings saved for ${device.id}`, 'success');
            setShowTimeModal(false);
            localStorage.setItem('timeSettings', JSON.stringify(timeSettings));
        } else {
            setShowTimeModal(false);
        }
    };

    // Add this function before the return statement
    const handleThresholdChange = async (index, value) => {
        try {
            const newSectorGroupsThreshold = { ...sectorGroupsThreshold };
            const device = newSectorGroupsThreshold[activeSector][index];
            
            // Update the threshold value
            device.thresholdValue = value;
            
            // Save threshold adjustment to notifications
            const notificationContent = `Adjusted ${device.id} threshold to ${value} ${device.thresholdUnit} in Sector ${activeSector}`;
            await fetch('http://localhost:3000/api/notifications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    datetime: new Date().toLocaleString('en-US', { month: 'short', day: 'numeric' }),
                    content: notificationContent,
                    status: "Pending"  // Changes to "Completed" when threshold is actually applied
                })
            });
            
            // Update state and validate as before
            if (device.errorPercentage && device.baseValue) {
                const minAllowed = device.baseValue * (1 - device.errorPercentage/100);
                const maxAllowed = device.baseValue * (1 + device.errorPercentage/100);
                device.isOutOfRange = value < minAllowed || value > maxAllowed;
                device.errorMessage = device.isOutOfRange ? 
                    `Value outside ±${device.errorPercentage}% range (${minAllowed.toFixed(1)}-${maxAllowed.toFixed(1)})` : '';
            }
            
            setSectorGroupsThreshold(newSectorGroupsThreshold);
            
        } catch (error) {
            console.error("Error updating threshold value:", error);
            showNotification('Failed to update threshold value', 'error');
        }
    };

    // Add this function before the return statement
    const handleErrorPercentageChange = (index, percentage) => {
        try {
            // Make a copy of the current state
            const newSectorGroupsThreshold = { ...sectorGroupsThreshold };
            
            // Ensure valid percentage (between 1 and 100)
            const validPercentage = Math.max(1, Math.min(100, percentage || 10));
            
            // Update the error percentage for the device
            newSectorGroupsThreshold[activeSector][index].errorPercentage = validPercentage;
            
            // Set the new state
            setSectorGroupsThreshold(newSectorGroupsThreshold);
            
            // Log the change
            if (isConnected) {
                console.log(`Error range updated for ${activeSector}-${newSectorGroupsThreshold[activeSector][index].id}: ±${validPercentage}%`);
            }
        } catch (error) {
            console.error("Error updating error percentage:", error);
            showNotification('Failed to update error percentage', 'error');
        }
    };

    // Add useEffect to fetch threshold values
    useEffect(() => {
        fetchThresholds();
    }, []); // Empty dependency array means this runs once when component mounts

    const fetchThresholds = async () => {
        try {
            const response = await fetch('http://localhost:3000/api/threshold');
            if (!response.ok) {
                throw new Error('Failed to fetch thresholds');
            }
            const data = await response.json();
            
            // Transform data into an object keyed by attribute
            const thresholdData = data.reduce((acc, item) => {
                acc[item.attribute] = {
                    value: parseFloat(item.value),
                    minValue: parseFloat(item.minValue),
                    maxValue: parseFloat(item.maxValue)
                };
                return acc;
            }, {});
            
            setCurrentThresholds(prev => ({
                ...prev,
                ...thresholdData
            }));
        } catch (error) {
            console.error('Error fetching thresholds:', error);
            showNotification('Failed to fetch threshold values', 'error');
        }
    };

    return (
        <div className="control">
            <Sidebar />
            {notification.show && (
                <div className={`notification ${notification.type}`}>
                    {notification.message}
                </div>
            )}
            
            {showTimeModal && (
                <div className="time-modal-overlay">
                    <div className="time-modal">
                        <div className="time-modal-header">
                            <h3>Schedule Settings for {sectorGroups[activeSector][selectedGroupIndex]?.id}</h3>
                            <button className="close-btn" onClick={() => setShowTimeModal(false)}>
                                <FaTimes />
                            </button>
                        </div>
                        <div className="time-modal-body">
                            <div className="time-setting">
                                <label>Start Time:</label>
                                <input
                                    type="time"
                                    value={timeSettings[activeSector][selectedGroupIndex]?.startTime || "00:00"}
                                    onChange={(e) => handleTimeSettingsChange("startTime", e.target.value)}
                                />
                            </div>
                            <div className="time-setting">
                                <label>End Time:</label>
                                <input
                                    type="time"
                                    value={timeSettings[activeSector][selectedGroupIndex]?.endTime || "23:59"}
                                    onChange={(e) => handleTimeSettingsChange("endTime", e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="time-modal-footer">
                            <button className="cancel-btn" onClick={() => setShowTimeModal(false)}>Cancel</button>
                            <button className="save-btn" onClick={saveTimeSettings}>Save</button>
                        </div>
                    </div>
                </div>
            )}
            
            <div className="control-content">
                <Header />
                <div className="control-container">
                    <div className="control-left">
                        <h2>Sector {activeSector}</h2>
                        <h3>Control Panel</h3>

                        {/* Add sensor data display section */}
                        <div className="sensor-data">
                            <h4>Current Threshold value</h4>
                            <div className="sensor-values">
                                <div className="sensor-card">
                                    <span className="sensor-name">Temperature</span>
                                    <div className="sensor-value">
                                        <span className="value">
                                            {currentThresholds.Temperature.value !== null 
                                                ? `${currentThresholds.Temperature.value.toFixed(1)} °C` 
                                                : "N/A"}
                                        </span>
                                    </div>
                                </div>
                                <div className="sensor-card">
                                    <span className="sensor-name">Humidity</span>
                                    <div className="sensor-value">
                                        <span className="value">
                                            {currentThresholds.Humidity.value !== null 
                                                ? `${currentThresholds.Humidity.value.toFixed(1)} %` 
                                                : "N/A"}
                                        </span>
                                    </div>
                                </div>
                                <div className="sensor-card">
                                    <span className="sensor-name">Light</span>
                                    <div className="sensor-value">
                                        <span className="value">
                                            {currentThresholds.Light.value !== null 
                                                ? `${currentThresholds.Light.value.toFixed(1)} lux` 
                                                : "N/A"}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            {sensorData.lastUpdated && (
                                <div className="data-timestamp">
                                    Last updated: {new Date(sensorData.lastUpdated).toLocaleTimeString()}
                                </div>
                            )}
                        </div>

                        {/* Existing light-status div */}
                        <div className="light-status">
                            <div className="light-card">
                                <span className="light-name">Working</span>
                                <div className="light-value">
                                    <span className="on">3 on</span>
                                    <span className="off">0 off</span>
                                </div>
                            </div>
                            <div className="light-card">
                                <span className="light-name">Emergency</span>
                                <div className="light-value">
                                    <span className="on">3 on</span>
                                    <span className="off">0 off</span>
                                </div>
                            </div>
                        </div>

                        <div className="sector-control">
                            <h3>Change Sector</h3>
                            <div className="sector-nav">
                                <div className="nav-circle">
                                    <button
                                        className={`nav-btn nav-c ${activeSector === "C" ? "active" : ""}`}
                                        onClick={() => handleSectorChange("C")}
                                    >
                                        C
                                    </button>
                                    <button
                                        className={`nav-btn nav-b ${activeSector === "B" ? "active" : ""}`}
                                        onClick={() => handleSectorChange("B")}
                                    >
                                        B
                                    </button>
                                    <button
                                        className={`nav-btn nav-d ${activeSector === "D" ? "active" : ""}`}
                                        onClick={() => handleSectorChange("D")}
                                    >
                                        D
                                    </button>
                                    <button
                                        className={`nav-btn nav-a ${activeSector === "A" ? "active" : ""}`}
                                        onClick={() => handleSectorChange("A")}
                                    >
                                        A
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="control-right">

                        <div className="control-groups">
                            <div className="group-header">
                                <span>Device</span>
                                <span>Type of control</span>
                                <span>Start</span>
                                <span>Status</span>
                            </div>
                            {sectorGroups[activeSector].map((group, index) => (
                                <div key={`${activeSector}_${group.id}`} className="group-row">
                                    <span className="group-id">{group.id}</span>
                                    <div className="control-type">
                                        <button
                                            className={`type-btn ${group.type === "Schedule" ? "active" : ""}`}
                                            onClick={() => setControlType(index, "Schedule")}
                                        >
                                            Schedule
                                        </button>
                                        <button
                                            className={`type-btn ${group.type === "On" ? "active" : ""}`}
                                            onClick={() => setControlType(index, "On")}
                                        >
                                            On
                                        </button>
                                       <button
                                            className={`type-btn ${group.type === "Off" ? "active" : ""}`}
                                            onClick={() => setControlType(index, "Off")}
                                        >
                                            Off
                                        </button>                                        
                                    </div>
                                    <button 
                                        className="start-btn"
                                        onClick={() => handleStartButton(index)}
                                    >
                                        Start
                                    </button>
                                    <label className="switch">
                                        <input
                                            type="checkbox"
                                            checked={group.status}
                                            onChange={() => toggleStatus(index, false)}
                                        />
                                        <span className="slider"></span>
                                    </label>
                                </div>
                            ))}
                        </div>

                        <div className="control-groups">
                            <div className="group-header">
                                <span>Device</span>
                                <span>Threshold</span>
                                <span>Start</span>
                                <span>Status</span>
                            </div>
                            {sectorGroupsThreshold[activeSector].map((group, index) => (
                                <div key={`${activeSector}_${group.id}`} className="group-row">
                                    <span className="group-id">{group.id}</span>
                            <div className="threshold-value">
                                <div className="threshold-input-container">
                                    <div className="threshold-controls-row">
                                    <div className="threshold-input-wrapper">
                                        <input
                                            id={`threshold-${index}`}
                                            type="number"
                                            value={group.thresholdValue || 0}
                                            onChange={(e) => handleThresholdChange(index, parseFloat(e.target.value))}
                                            className="threshold-input"
                                        />
                                    <span className="threshold-unit-fixed">
                                        {group.id === "Temperature" ? " °C" : 
                                        group.id === "Humidity" ? " %" : 
                                        group.id === "Light" ? " lux" : ""}
                                    </span>
                                    </div>

                                    <div className="error-range-setting">
                                        <label>±</label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="100"
                                            value={group.errorPercentage || 10}
                                            onChange={(e) => handleErrorPercentageChange(index, parseInt(e.target.value))}
                                            className="error-percentage-input"
                                        />
                                        <span>%</span>
                                    </div>
                                    </div>
                                        {group.errorMessage && <div className="threshold-error">{group.errorMessage}</div>}

                                </div>
                            </div>
                                    <button 
                                        className="start-btn"
                                        onClick={() => handleStartButton(index, true)}
                                    >
                                        Start
                                    </button>
                                    <label className="switch">
                                        <input
                                            type="checkbox"
                                            checked={group.status}
                                            onChange={() => toggleStatus(index, true)}
                                        />
                                        <span className="slider"></span>
                                    </label>
                                </div>
                            ))}
                        </div>


                    </div>
                </div>
            </div>
        </div>
    );
};

export default Control;