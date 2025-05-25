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
    const [groups, setGroups] = useState([
        { id: "Light", status: true, type: "Schedule" },
        { id: "Motor Fan", status: true, type: "Schedule" },
        { id: "Pump", status: false, type: "Schedule" },
    ]);

    // Time modal state
    const [showTimeModal, setShowTimeModal] = useState(false);
    const [selectedGroupIndex, setSelectedGroupIndex] = useState(null);
    const [timeSettings, setTimeSettings] = useState(groups.map(() => ({
        startTime: "00:00",
        endTime: "23:59"
    })));
    
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

            const newGroups = [...groups];
            newGroups[index].status = !newGroups[index].status;
            setGroups(newGroups);

            // Send command using WebSocket context
            console.log(`Sending device command: Sector ${activeSector}, Device ${newGroups[index].id}, Status ${newGroups[index].status}`);
            
            const success = sendDeviceCommand(
                activeSector,
                newGroups[index].id,
                newGroups[index].status,
                newGroups[index].type
            );
            
            if (success) {
                showNotification(`${newGroups[index].id} ${newGroups[index].status ? 'turned on' : 'turned off'}`, 'success');
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
            
            const newGroups = [...groups];
            newGroups[index].type = type;
            setGroups(newGroups);
            
            // If Schedule type is selected, show the time modal
            if (type === "Schedule") {
                setSelectedGroupIndex(index);
                setShowTimeModal(true);
                return;
            }

            // Send control type change using WebSocket context
            console.log(`Sending control type change: Sector ${activeSector}, Device ${newGroups[index].id}, Type ${type}`);
            
            const success = changeControlType(
                activeSector,
                newGroups[index].id,
                type,
                newGroups[index].status
            );
            
            if (!success) {
                showNotification('Failed to change control type - WebSocket not connected', 'error');
            } else {
                showNotification(`Control type changed to ${type}`, 'success');
            }
        } catch (error) {
            console.error("Error changing control type:", error);
            showNotification('An error occurred while changing control type', 'error');
        }
    };

    const handleStartButton = (index) => {
        try {
            if (!isConnected) {
                showNotification('Not connected to server. Attempting to reconnect...', 'error');
                reconnect();
                return;
            }
            
            const device = groups[index];
            console.log(`Starting ${device.id} with mode ${device.type}`);
            
            // For Schedule type, we need to send the time settings
            const payload = device.type === "Schedule" 
                ? { 
                    ...timeSettings[index],
                    command: "start" 
                  } 
                : { command: "start" };
            
            const success = sendDeviceCommand(
                activeSector,
                device.id,
                true, // Set to active/on
                device.type,
                payload
            );
            
            if (success) {
                // Update the group status to on
                const newGroups = [...groups];
                newGroups[index].status = true;
                setGroups(newGroups);
                
                showNotification(`Started ${device.id} in ${device.type} mode`, 'success');
            } else {
                showNotification('Failed to start device - WebSocket not connected', 'error');
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
            const newTimeSettings = [...timeSettings];
            newTimeSettings[selectedGroupIndex][field] = value;
            setTimeSettings(newTimeSettings);
        }
    };
    
    const saveTimeSettings = () => {
        if (selectedGroupIndex !== null && isConnected) {
            const device = groups[selectedGroupIndex];
            
            const success = changeControlType(
                activeSector,
                device.id,
                device.type,
                device.status,
                timeSettings[selectedGroupIndex]
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
                            <h3>Schedule Settings for {groups[selectedGroupIndex]?.id}</h3>
                            <button className="close-btn" onClick={() => setShowTimeModal(false)}>
                                <FaTimes />
                            </button>
                        </div>
                        <div className="time-modal-body">
                            <div className="time-setting">
                                <label>Start Time:</label>
                                <input
                                    type="time"
                                    value={timeSettings[selectedGroupIndex]?.startTime || "00:00"}
                                    onChange={(e) => handleTimeSettingsChange("startTime", e.target.value)}
                                />
                            </div>
                            <div className="time-setting">
                                <label>End Time:</label>
                                <input
                                    type="time"
                                    value={timeSettings[selectedGroupIndex]?.endTime || "23:59"}
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
                        <h3>Control panel lighting</h3>

                        <div className="light-status">
                            <div className="light-card">
                                <span className="light-name">Working light</span>
                                <div className="light-value">
                                    <span className="on">30 on</span>
                                    <span className="off">0 off</span>
                                </div>
                            </div>
                            <div className="light-card">
                                <span className="light-name">Emergency light</span>
                                <div className="light-value">
                                    <span className="on">24 on</span>
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
                        <div className="panel-tabs">
                            {["Panel A1", "Panel A2", "Panel A3", "Panel A4", "Panel A5"].map((panel) => (
                                <button
                                    key={panel}
                                    className={`panel-tab ${activePanel === panel ? "active" : ""}`}
                                    onClick={() => setActivePanel(panel)}
                                >
                                    {panel}
                                </button>
                            ))}
                        </div>

                        <div className="control-groups">
                            <div className="group-header">
                                <span>Group</span>
                                <span>Type of control</span>
                                <span>Start</span>
                                <span>Status</span>
                            </div>
                            {groups.map((group, index) => (
                                <div key={group.id} className="group-row">
                                    <span className="group-id">{group.id}</span>
                                    <div className="control-type">
                                        <button
                                            className={`type-btn ${group.type === "Schedule" ? "active" : ""}`}
                                            onClick={() => setControlType(index, "Schedule")}
                                        >
                                            Schedule
                                        </button>
                                        <button
                                            className={`type-btn ${group.type === "Manual" ? "active" : ""}`}
                                            onClick={() => setControlType(index, "Manual")}
                                        >
                                            Manual
                                        </button>
                                        <button
                                            className={`type-btn ${group.type === "On/Off" ? "active" : ""}`}
                                            onClick={() => setControlType(index, "On/Off")}
                                        >
                                            On/Off
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
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Control;