// src/components/Login/LoginCombine.jsx
import { useEffect, useState } from 'react';
import AuthForm from './AuthForm.jsx';
import TogglePanel from './TogglePanel.jsx';
import './LoginCombine.scss';
// import '../../Utils/script.js';

const LoginCombine = () => {
    const [isSignUp, setIsSignUp] = useState(false);

    const handleToggle = (signUp) => {
        setIsSignUp(signUp);
    };

    return (
        <div className={`container ${isSignUp ? 'active' : ''}`}>
            <AuthForm isSignUp={isSignUp} />
            <TogglePanel onToggle={handleToggle} />
        </div>
    );
};

export default LoginCombine;