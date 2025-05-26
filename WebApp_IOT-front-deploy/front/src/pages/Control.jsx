import React, { useState, useEffect } from "react";
import { useWebSocket } from "../contexts/WebSocket";
import Sidebar from "../components/Sidebar";
import "./Control.scss";
import { FaArrowLeft, FaArrowRight, FaTimes } from "react-icons/fa";
import Header from "../components/Header.jsx";

const Control = () => {
    const { sendDeviceCommand, changeControlType, isConnected, reconnect } = useWebSocket();
    const [activePanel, setActivePanel] = useState("Panel A1");
    const [activeSector, setActiveSector] = useState("A");
    const [notification, setNotification] = useState({ show: false, message: '', type: 'info' });
    
    // Thay đổi cách lưu trữ state của groups theo sector
    const [sectorGroups, setSectorGroups] = useState({
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
    });

    const [sectorGroupsThreshold, setSectorGroupsThreshold] = useState({
        'A': [
            { id: "Temperature", thresholdValue: 25, thresholdUnit: "°C" },
            { id: "Humidity", thresholdValue: 60, thresholdUnit: "%" },
            { id: "Light", thresholdValue: 500, thresholdUnit: "lux" },
            
        ],
        'B': [
            { id: "Temperature", thresholdValue: 25, thresholdUnit: "°C" },
            { id: "Humidity", thresholdValue: 60, thresholdUnit: "%" },
            { id: "Light", thresholdValue: 500, thresholdUnit: "lux" },
        ],
        'C': [
            { id: "Temperature", thresholdValue: 25, thresholdUnit: "°C" },
            { id: "Humidity", thresholdValue: 60, thresholdUnit: "%" },
            { id: "Light", thresholdValue: 500, thresholdUnit: "lux" },
        ],
        'D': [
            { id: "Temperature", thresholdValue: 25, thresholdUnit: "°C" },
            { id: "Humidity", thresholdValue: 60, thresholdUnit: "%" },
            { id: "Light", thresholdValue: 500, thresholdUnit: "lux" },
        ]
    });


    // Thời gian theo sector và thiết bị
    const [timeSettings, setTimeSettings] = useState({
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
    });

    const [showTimeModal, setShowTimeModal] = useState(false);
    const [selectedGroupIndex, setSelectedGroupIndex] = useState(null);

    // Attempt to reconnect if not connected
    useEffect(() => {
        if (!isConnected) {
            const reconnectInterval = setInterval(() => {
                console.log("Attempting to reconnect WebSocket...");
                reconnect();
            }, 5000);
            
            return () => clearInterval(reconnectInterval);
        }
    }, [isConnected, reconnect]);

    const showNotification = (message, type = 'info') => {
        setNotification({ show: true, message, type });
        setTimeout(() => setNotification({ show: false, message: '', type: 'info' }), 3000);
    };

    const toggleStatus = (index) => {
        try {
            if (!isConnected) {
                showNotification('Not connected to server. Attempting to reconnect...', 'error');
                reconnect();
                return;
            }

            const newSectorGroups = { ...sectorGroups };
            newSectorGroups[activeSector][index].status = !newSectorGroups[activeSector][index].status;
            setSectorGroups(newSectorGroups);

            const device = newSectorGroups[activeSector][index];
            
            const success = sendDeviceCommand(
                activeSector,
                device.id,
                device.status,
                device.type
            );
            
            if (success) {
                showNotification(`${device.id} ${device.status ? 'turned on' : 'turned off'}`, 'success');
            } else {
                showNotification('Failed to send command to server', 'error');
            }
        } catch (error) {
            console.error("Error toggling device status:", error);
            showNotification('An error occurred while toggling device status', 'error');
        }
    };

    const setControlType = (index, type) => {
        try {
            if (!isConnected) {
                showNotification('Not connected to server. Attempting to reconnect...', 'error');
                reconnect();
                return;
            }

            const newSectorGroups = { ...sectorGroups };
            newSectorGroups[activeSector][index].type = type;
            setSectorGroups(newSectorGroups);

            if (type === "Schedule") {
                setSelectedGroupIndex(index);
                setShowTimeModal(true);
                return;
            }

            const device = newSectorGroups[activeSector][index];
            
            const success = changeControlType(
                activeSector,
                device.id,
                type,
                device.status
            );
            
            if (!success) {
                showNotification('Failed to change control type', 'error');
            } else {
                showNotification(`Control type changed to ${type}`, 'success');
            }
        } catch (error) {
            console.error("Error changing control type:", error);
            showNotification('An error occurred while changing control type', 'error');
        }
    };

const handleStartButton = (index, isThresholdDevice = false) => {
    try {
        if (!isConnected) {
            showNotification('Not connected to server. Attempting to reconnect...', 'error');
            reconnect();
            return;
        }
        
        if (isThresholdDevice) {
            // Handle threshold devices (Temperature, Humidity, Light)
            const device = sectorGroupsThreshold[activeSector][index];
            console.log(`Starting threshold monitor for ${device.id}`);
            
            // Calculate min and max based on error percentage
            const errorPercentage = device.errorPercentage || 10;
            const thresholdValue = device.thresholdValue;
            const minThreshold = thresholdValue * (1 - errorPercentage / 100);
            const maxThreshold = thresholdValue * (1 + errorPercentage / 100);
            
            // Prepare payload with threshold information
            const payload = {
                command: "start",
                thresholdValue: thresholdValue,
                minThreshold: minThreshold,
                maxThreshold: maxThreshold,
                errorPercentage: errorPercentage,
                unit: device.thresholdUnit
            };
            
            // Send command via WebSocket
            const success = sendDeviceCommand(
                activeSector,
                device.id,
                true,
                "Threshold", // Specific control type for thresholds
                payload
            );
            
            if (success) {
                // Update status if needed
                const newSectorGroupsThreshold = { ...sectorGroupsThreshold };
                newSectorGroupsThreshold[activeSector][index].status = true;
                setSectorGroupsThreshold(newSectorGroupsThreshold);
                
                showNotification(`Started ${device.id} threshold monitoring`, 'success');
            } else {
                showNotification('Failed to start threshold monitoring', 'error');
            }
        } else {
            // Original code for regular devices (Light, Motor Fan, Pump)
            const device = sectorGroups[activeSector][index];
            console.log(`Starting ${device.id} with mode ${device.type}`);
            
            // For Schedule type, we need to send the time settings
            const payload = device.type === "Schedule" 
                ? { 
                    ...timeSettings[activeSector][index],
                    command: "start" 
                  } 
                : { command: "start" };
            
            const success = sendDeviceCommand(
                activeSector,
                device.id,
                true,
                device.type,
                payload
            );
            
            if (success) {
                // Update the group status to on
                const newSectorGroups = { ...sectorGroups };
                newSectorGroups[activeSector][index].status = true;
                setSectorGroups(newSectorGroups);
                
                showNotification(`Started ${device.id} in ${device.type} mode`, 'success');
            } else {
                showNotification('Failed to start device - WebSocket not connected', 'error');
            }
        }
    } catch (error) {
        console.error("Error starting device:", error);
        showNotification('An error occurred while starting the device', 'error');
    }
};

    const handleSectorChange = (sector) => {
        setActiveSector(sector);
    };
    
    const handleTimeSettingsChange = (field, value) => {
        if (selectedGroupIndex !== null) {
            const newTimeSettings = { ...timeSettings };
            newTimeSettings[activeSector][selectedGroupIndex][field] = value;
            setTimeSettings(newTimeSettings);
        }
    };
    
    const saveTimeSettings = () => {
        if (selectedGroupIndex !== null && isConnected) {
            const device = sectorGroups[activeSector][selectedGroupIndex];
            
            const success = changeControlType(
                activeSector,
                device.id,
                device.type,
                device.status,
                timeSettings[activeSector][selectedGroupIndex]
            );
            
            if (success) {
                showNotification(`Schedule settings saved for ${device.id}`, 'success');
                setShowTimeModal(false);
            } else {
                showNotification('Failed to save schedule settings', 'error');
            }
        } else {
            setShowTimeModal(false);
        }
    };

// Add this function before the return statement
const handleThresholdChange = (index, value) => {
    try {
        // Make a copy of the current state
        const newSectorGroupsThreshold = { ...sectorGroupsThreshold };
        const device = newSectorGroupsThreshold[activeSector][index];
        
        // Update the threshold value for the specified device
        device.thresholdValue = value;
        
        // If there's an error percentage set, validate the new value
        if (device.errorPercentage && device.baseValue) {
            // Calculate valid range
            const minAllowed = device.baseValue * (1 - device.errorPercentage/100);
            const maxAllowed = device.baseValue * (1 + device.errorPercentage/100);
            
            // Check if current value is within range
            device.isOutOfRange = value < minAllowed || value > maxAllowed;
            
            // Update error message if needed
            if (device.isOutOfRange) {
                device.errorMessage = `Value outside ±${device.errorPercentage}% range (${minAllowed.toFixed(1)}-${maxAllowed.toFixed(1)})`;
            } else {
                device.errorMessage = '';
            }
        }
        
        // Set the new state
        setSectorGroupsThreshold(newSectorGroupsThreshold);
        
        // Optional: If you want to send this change to the server
        if (isConnected) {
            console.log(`Threshold updated for ${activeSector}-${device.id}: ${value}`);
        }
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
                        <div className="connection-status">
                            <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
                                {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
                            </span>
                        </div>
                        <h2>Sector {activeSector}</h2>
                        <h3>Control Panel</h3>

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
                                            onChange={() => toggleStatus(index)}
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
                                            onChange={() => toggleStatus(index)}
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