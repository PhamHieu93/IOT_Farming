// src/App.jsx
import LoginCombine from '../components/Login/LoginCombine.jsx';

function Login() {


    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            background: 'linear-gradient(to right, #d1dbf1, #aac7fa)',
            padding: '20px'
        }}>
            <LoginCombine />
        </div>
    );
}

export default Login;