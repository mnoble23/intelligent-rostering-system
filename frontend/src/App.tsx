import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";

import API from "./services/api";
import RosterTable from "./components/RosterTable";
import UserAvailabilityForm from "./components/UserAvailabilityForm";
import GenerateRoster from "./components/GenerateRoster";
import ManageShiftAssignments from "./components/ManageShiftAssignments";
import MyRoster from "./components/MyRoster";
import ShiftCoverage from "./components/ShiftCoverage";

interface DashboardPageProps {
  shifts: any[];
  refreshRoster: () => void;
}

function DashboardPage({ shifts, refreshRoster }: DashboardPageProps) {
  useEffect(() => {
    refreshRoster();
  }, [refreshRoster]);

  return <RosterTable shifts={shifts} />;
}

export default function App() {
  const [shifts, setShifts] = useState<any[]>([]);

  const fetchRoster = useCallback(() => {
    API.get("/roster")
      .then(res => setShifts(res.data))
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    fetchRoster();
  }, [fetchRoster]);

  return (
    <Router>
      <nav style={{ padding: 10, borderBottom: "1px solid #ccc", marginBottom: 20 }}>
        <Link to="/" style={{ marginRight: 10 }}>Roster Dashboard</Link>
        <Link to="/shift-coverage" style={{ marginRight: 10 }}>Shift Coverage</Link>
        <Link to="/submit-availability" style={{ marginRight: 10 }}>Submit Availability</Link>
        <Link to="/generate-roster" style={{ marginRight: 10 }}>Generate Roster</Link>
        <Link to="/manage-shifts" style={{ marginRight: 10 }}>Manage Shifts</Link>
        <Link to="/my-roster">My Roster</Link>
      </nav>

      <Routes>
        <Route path="/" element={<DashboardPage shifts={shifts} refreshRoster={fetchRoster} />} />
        <Route path="/shift-coverage" element={<ShiftCoverage />} />
        <Route path="/submit-availability" element={<UserAvailabilityForm />} />
        <Route
          path="/generate-roster"
          element={<GenerateRoster refreshRoster={fetchRoster} />}
        />
        <Route path="/manage-shifts" element={<ManageShiftAssignments />} />
        <Route path="/my-roster" element={<MyRoster />} />
      </Routes>
    </Router>
  );
}
