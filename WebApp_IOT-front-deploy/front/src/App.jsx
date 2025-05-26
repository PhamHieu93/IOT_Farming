// App.jsx
import "./App.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Control from "./pages/Control.jsx";
import History from "./pages/History.jsx";
import Login from "./pages/Login.jsx";
import Layout from "./components/Layout.jsx";
import { WebSocketProvider } from "./contexts/WebSocket.jsx";

function App() {
  return (
    <WebSocketProvider>
      <Router>
          <Routes>
              <Route path="/" element={<Login />} />
              <Route element={<Layout />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/control" element={<Control />} />
                <Route path="/history" element={<History />} />
              </Route>
          </Routes>
      </Router>
    </WebSocketProvider>
  );
}

export default App;
