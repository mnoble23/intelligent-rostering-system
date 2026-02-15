import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { useEffect, useState } from "react";

import API from "./services/api";
import RosterTable from "./components/RosterTable";
import UserAvailabilityForm from "./components/UserAvailabilityForm";
import GenerateRoster from "./components/GenerateRoster";

export default function App() {
  const [shifts, setShifts] = useState<any[]>([]);

  const fetchRoster = () => {
    API.get("/roster")
      .then(res => setShifts(res.data))
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchRoster();
  }, []);

  return (
    <Router>
      {/* Navbar */}
      <nav style={{ padding: 10, borderBottom: "1px solid #ccc", marginBottom: 20 }}>
        <Link to="/" style={{ marginRight: 10 }}>Roster Dashboard</Link>
        <Link to="/submit-availability" style={{ marginRight: 10 }}>Submit Availability</Link>
        <Link to="/generate-roster">Generate Roster</Link>
      </nav>

      {/* Routes */}
      <Routes>
        {/* Dashboard */}
        <Route path="/" element={<RosterTable shifts={shifts} />} />

        {/* Combined User + Availability Form */}
        <Route path="/submit-availability" element={<UserAvailabilityForm />} />

        {/* Generate Roster Page */}
        <Route path="/generate-roster" element={<GenerateRoster />} />
      </Routes>
    </Router>
  );
}

