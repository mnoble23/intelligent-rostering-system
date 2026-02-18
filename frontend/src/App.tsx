import { BrowserRouter as Router, Routes, Route, Link, Navigate } from "react-router-dom";
import { type ReactElement, useCallback, useEffect, useState } from "react";

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

type AppRole = "manager" | "staff";

function DashboardPage({ shifts, refreshRoster }: DashboardPageProps) {
  useEffect(() => {
    refreshRoster();
  }, [refreshRoster]);

  return <RosterTable shifts={shifts} />;
}

interface RoleGateProps {
  role: AppRole;
  allowedRoles: AppRole[];
  children: ReactElement;
}

function RoleGate({ role, allowedRoles, children }: RoleGateProps) {
  if (!allowedRoles.includes(role)) {
    return <Navigate to={role === "manager" ? "/" : "/my-roster"} replace />;
  }

  return children;
}

export default function App() {
  const [role, setRole] = useState<AppRole | null>(() => {
    const saved = localStorage.getItem("app_role");
    return saved === "manager" || saved === "staff" ? saved : null;
  });
  const [shifts, setShifts] = useState<any[]>([]);

  const fetchRoster = useCallback(() => {
    API.get("/roster")
      .then(res => setShifts(res.data))
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    fetchRoster();
  }, [fetchRoster]);

  const setAndPersistRole = (nextRole: AppRole) => {
    setRole(nextRole);
    localStorage.setItem("app_role", nextRole);
  };

  const clearRole = () => {
    setRole(null);
    localStorage.removeItem("app_role");
  };

  if (!role) {
    return (
      <main style={{ maxWidth: 560, margin: "80px auto", padding: 20 }}>
        <h1 style={{ marginTop: 0 }}>Who are you?</h1>
        <p>Select a role to continue. You can switch later from the top bar.</p>
        <div style={{ display: "flex", gap: 12 }}>
          <button type="button" onClick={() => setAndPersistRole("manager")}>
            I am a Manager
          </button>
          <button type="button" onClick={() => setAndPersistRole("staff")}>
            I am Staff
          </button>
        </div>
      </main>
    );
  }

  return (
    <Router>
      <nav style={{ padding: 10, borderBottom: "1px solid #ccc", marginBottom: 20 }}>
        {role === "manager" ? (
          <>
            <Link to="/" style={{ marginRight: 10 }}>Roster Dashboard</Link>
            <Link to="/shift-coverage" style={{ marginRight: 10 }}>Shift Coverage</Link>
            <Link to="/generate-roster" style={{ marginRight: 10 }}>Generate Roster</Link>
            <Link to="/manage-shifts" style={{ marginRight: 10 }}>Manage Shifts</Link>
            <Link to="/submit-availability" style={{ marginRight: 10 }}>Submit Availability</Link>
            <Link to="/my-roster" style={{ marginRight: 10 }}>My Roster</Link>
          </>
        ) : (
          <>
            <Link to="/" style={{ marginRight: 10 }}>Roster Dashboard</Link>
            <Link to="/my-roster" style={{ marginRight: 10 }}>My Roster</Link>
            <Link to="/submit-availability" style={{ marginRight: 10 }}>Submit Availability</Link>
          </>
        )}
        <button type="button" onClick={clearRole}>Switch Role</button>
      </nav>

      <Routes>
        <Route
          path="/"
          element={(
            <RoleGate role={role} allowedRoles={["manager", "staff"]}>
              <DashboardPage shifts={shifts} refreshRoster={fetchRoster} />
            </RoleGate>
          )}
        />
        <Route
          path="/shift-coverage"
          element={(
            <RoleGate role={role} allowedRoles={["manager"]}>
              <ShiftCoverage />
            </RoleGate>
          )}
        />
        <Route
          path="/submit-availability"
          element={(
            <RoleGate role={role} allowedRoles={["manager", "staff"]}>
              <UserAvailabilityForm />
            </RoleGate>
          )}
        />
        <Route
          path="/generate-roster"
          element={(
            <RoleGate role={role} allowedRoles={["manager"]}>
              <GenerateRoster refreshRoster={fetchRoster} />
            </RoleGate>
          )}
        />
        <Route
          path="/manage-shifts"
          element={(
            <RoleGate role={role} allowedRoles={["manager"]}>
              <ManageShiftAssignments />
            </RoleGate>
          )}
        />
        <Route
          path="/my-roster"
          element={(
            <RoleGate role={role} allowedRoles={["manager", "staff"]}>
              <MyRoster />
            </RoleGate>
          )}
        />
        <Route
          path="*"
          element={(
            <Navigate to={role === "manager" ? "/" : "/my-roster"} replace />
          )}
        />
      </Routes>
    </Router>
  );
}
