// App.jsx
import "./App.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Control from "./pages/Control.jsx";
import Notification from "./pages/History.jsx";
import Reminders from "./pages/Reminder.jsx";
import Login from "./pages/Login.jsx";
import Alarm from "./pages/Alarm.jsx";

function App() {
  return (
      <Router>          
        <Routes>
              <Route path="/" element={<Login />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/control" element={<Control />} />
                <Route path="/history" element={<Notification />} />
                <Route path="/reminders" element={<Reminders />} />
                <Route path="/alerts" element={<Alarm />} />
          </Routes>
      </Router>
  );
}

export default App;
