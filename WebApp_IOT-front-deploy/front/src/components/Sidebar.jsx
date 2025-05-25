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
                return "GROW SESSIONS";
            case "/history":
                return "DEVICES";
            case "/":
                return "BILLINGS";
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
                    className={activeTab === "GROW SESSIONS" ? "active" : ""}
                    onClick={() => handleNavigation("GROW SESSIONS", "/control")}
                >
                    <FaLeaf className="icon" />
                    <span>GROW SESSIONS</span>
                </li>
                <li
                    className={activeTab === "DEVICES" ? "active" : ""}
                    onClick={() => handleNavigation("DEVICES", "/history")}
                >
                    <FaThermometerHalf className="icon" />
                    <span>DEVICES</span>
                </li>
                <li
                    className={activeTab === "BILLINGS" ? "active" : ""}
                    onClick={() => handleNavigation("BILLINGS", "/")}
                >
                    <FaFileInvoiceDollar className="icon" />
                    <span>BILLINGS</span>
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