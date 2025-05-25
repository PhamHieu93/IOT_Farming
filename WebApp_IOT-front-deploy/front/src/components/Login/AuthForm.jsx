import { useNavigate } from 'react-router-dom';
import { useRef, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
    faGoogle,
    faFacebookF,
    faGithub,
    faLinkedinIn,
} from '@fortawesome/free-brands-svg-icons';
import 'react-toastify/dist/ReactToastify.css';
import './AuthForm.scss';

const AuthForm = ({ isSignUp, setIsSignUp }) => {
    const navigate = useNavigate();
    const formRef = useRef(null);
    const emailInputRef = useRef(null);

    useEffect(() => {
        if (!isSignUp && emailInputRef.current) {
            emailInputRef.current.focus();
        }
    }, [isSignUp]);

    const handleSubmit = (event) => {
        event.preventDefault();
        const form = formRef.current;

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        if (!isSignUp) {
            navigate('/dashboard');
        } else {
            setIsSignUp(false);
        }
    };

    return (
        <div className={`form-container ${isSignUp ? 'sign-up' : 'sign-in'}`}>
            <form ref={formRef}>
                <h1>{isSignUp ? 'Create Account' : 'Sign In'}</h1>
                <div className="social-icons">
                    <a href="#" className="icon">
                        <FontAwesomeIcon icon={faGoogle} />
                    </a>
                    <a href="#" className="icon">
                        <FontAwesomeIcon icon={faFacebookF} />
                    </a>
                    <a href="#" className="icon">
                        <FontAwesomeIcon icon={faGithub} />
                    </a>
                    <a href="#" className="icon">
                        <FontAwesomeIcon icon={faLinkedinIn} />
                    </a>
                </div>
                <span>{isSignUp ? 'or use your email for registration' : 'or use your email'}</span>
                {isSignUp && <input type="text" placeholder="Name" required />}
                <input type="email" placeholder="Email" required ref={emailInputRef} />
                <input type="password" placeholder="Password" required />
                {!isSignUp && (
                    <a href="#" className="forgot-password">
                        Forget Your Password?
                    </a>
                )}
                <button type="button" onClick={handleSubmit}>
                    {isSignUp ? 'Sign Up' : 'Sign In'}
                </button>
            </form>
        </div>
    );
};

export default AuthForm;
