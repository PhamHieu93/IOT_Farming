import React from 'react';
import { FiBell } from 'react-icons/fi';
import './Header.scss';

const Header = () => {
    return (
        <div className="dashboard-header">
            <h2>Sensors <span className="chevron">{">"}</span> Sensor 02</h2>
            <div className="header-actions">
                <div className="notification-icon">
                    <FiBell className="icon" />
                </div>
                <div className="user-avatar">
                    <img
                        src="https://via.placeholder.com/40"
                        alt="User Avatar"
                    />
                </div>
            </div>
        </div>
    );
};

export default Header;