// src/components/TogglePanel/TogglePanel.jsx
import './TogglePanel.scss';

const TogglePanel = ({ onToggle }) => {
    return (
        <div className="toggle-container">
            <div className="toggle">
                <div className="toggle-panel toggle-left">
                    <h2>Welcome Back</h2>
                    <p>Enter your personal details to use all of site features</p>
                    <button
                        className="hidden"
                        onClick={() => onToggle(false)}
                    >
                        Sign In
                    </button>
                </div>
                <div className="toggle-panel toggle-right">
                    <h2>Hello there</h2>
                    <p>Register with your personal details to use all of site features</p>
                    <button
                        className="hidden"
                        onClick={() => onToggle(true)}
                    >
                        Sign Up
                    </button>
                </div>
            </div>
        </div>
    );
};

export default TogglePanel;