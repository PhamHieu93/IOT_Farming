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
            case "/history":
                return "NOTIFICATIONS";
            case "/reminders":
                return "REMINDERS";
            case "/settings":
                return "SETTINGS";
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
                    className={activeTab === "NOTIFICATIONS" ? "active" : ""}
                    onClick={() => handleNavigation("NOTIFICATIONS", "/notifications")}
                >
                    <FaThermometerHalf className="icon" />
                    <span>NOTIFICATIONS</span>
                </li>
                <li
                    className={activeTab === "REMINDERS" ? "active" : ""}
                    onClick={() => handleNavigation("REMINDERS", "/reminders")}
                >
                    <FaFileInvoiceDollar className="icon" />
                    <span>REMINDERS</span>
                </li>
                <li
                    className={activeTab === "SETTINGS" ? "active" : ""}
                    onClick={() => handleNavigation("SETTINGS", "/settings")}
                >
                    <FaCog className="icon" />
                    <span>SETTINGS</span>
                </li>
            </ul>
        </div>
    );
};

export default Sidebar;