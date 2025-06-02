import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./Sidebar.scss";
import { FaHome, FaLeaf, FaThermometerHalf, FaFileInvoiceDollar, FaCog } from "react-icons/fa";

const Sidebar = () => {
    const navigate = useNavigate();
    const location = useLocation();

    // Determine active tab based on current pathname
    const getActiveTab = (pathname) => {
        switch (pathname) {
            case "/dashboard":
                return "SENSORS";
            case "/control":
                return "CONTROL PANEL";
            case "/alerts":
                return "ALERTS";
            case "/history":
                return "SERVER LOGS";
            case "/reminders":
                return "REMINDERS";
            default:
                return "SENSORS";
        }
    };

    const [activeTab, setActiveTab] = useState(getActiveTab(location.pathname));

    const handleNavigation = (tab, path) => {
        setActiveTab(tab);
        navigate(path);
    };

    return (
        <div className="sidebar">
            <div className="sidebar-header">
                <h3>GrowControl</h3>
            </div>
            <ul>
                <li
                    className={activeTab === "SENSORS" ? "active" : ""}
                    onClick={() => handleNavigation("SENSORS", "/dashboard")}
                >
                    <FaHome className="icon" />
                    <span>SENSORS</span>
                </li>
                <li
                    className={activeTab === "CONTROL PANEL" ? "active" : ""}
                    onClick={() => handleNavigation("CONTROL PANEL", "/control")}
                >
                    <FaLeaf className="icon" />
                    <span>CONTROL PANEL</span>
                </li>
                <li
                    className={activeTab === "ALERTS" ? "active" : ""}
                    onClick={() => handleNavigation("ALERTS", "/alerts")}
                >
                    <FaThermometerHalf className="icon" />
                    <span>ALERTS</span>
                </li>
                <li
                    className={activeTab === "SERVER LOGS" ? "active" : ""}
                    onClick={() => handleNavigation("SERVER LOGS", "/history")}
                >
                    <FaThermometerHalf className="icon" />
                    <span>SERVER LOGS</span>
                </li>
                <li
                    className={activeTab === "REMINDERS" ? "active" : ""}
                    onClick={() => handleNavigation("REMINDERS", "/reminders")}
                >
                    <FaFileInvoiceDollar className="icon" />
                    <span>REMINDERS</span>
                </li>
            </ul>
        </div>
    );
};

export default Sidebar;