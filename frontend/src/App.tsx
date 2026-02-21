import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from "react-router-dom";
import { type ReactElement, useCallback, useEffect, useState } from "react";
import "./App.css";

import API from "./services/api";
import RosterTable from "./components/RosterTable";
import UserAvailabilityForm from "./components/UserAvailabilityForm";
import GenerateRoster from "./components/GenerateRoster";
import ManageShiftAssignments from "./components/ManageShiftAssignments";
import MyRoster from "./components/MyRoster";
import ShiftCoverage from "./components/ShiftCoverage";
import MyProfile from "./components/MyProfile";

interface DashboardPageProps {
  shifts: any[];
  weekStartDate?: string;
}

type AppRole = "manager" | "staff";

function DashboardPage({ shifts, weekStartDate }: DashboardPageProps) {
  return <RosterTable shifts={shifts} weekStartDate={weekStartDate} />;
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
  const [availableWeeks, setAvailableWeeks] = useState<string[]>([]);
  const [selectedWeek, setSelectedWeek] = useState<string>("");

  const fetchRoster = useCallback(() => {
    API.get("/roster", selectedWeek ? { params: { week_start_date: selectedWeek } } : undefined)
      .then(res => setShifts(res.data))
      .catch(err => console.error(err));
  }, [selectedWeek]);

  const fetchWeeks = useCallback(() => {
    API.get<string[]>("/roster/weeks")
      .then(res => {
        const weeks = res.data ?? [];
        setAvailableWeeks(weeks);
        setSelectedWeek(current => {
          if (weeks.length === 0) return "";
          if (current && weeks.includes(current)) return current;
          return weeks[0];
        });
      })
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    fetchWeeks();
  }, [fetchWeeks]);

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

  const navItems =
    role === "manager"
      ? [
          { to: "/", label: "Roster Dashboard" },
          { to: "/shift-coverage", label: "Shift Coverage" },
          { to: "/generate-roster", label: "Generate Roster" },
          { to: "/manage-shifts", label: "Manage Shifts" },
          { to: "/submit-availability", label: "Submit Availability" },
          { to: "/my-roster", label: "My Roster" },
          { to: "/my-profile", label: "My Profile" },
        ]
      : [
          { to: "/", label: "Roster Dashboard" },
          { to: "/my-roster", label: "My Roster" },
          { to: "/my-profile", label: "My Profile" },
          { to: "/submit-availability", label: "Submit Availability" },
        ];

  return (
    <Router>
      <div className="app-shell">
        <aside className="app-sidebar">
          <div className="app-sidebar__brand">
            <h1>Roster OS</h1>
            <p>{role === "manager" ? "Manager workspace" : "Staff workspace"}</p>
          </div>
          <nav className="app-sidebar__links">
            {navItems.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `app-sidebar__link${isActive ? " app-sidebar__link--active" : ""}`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="app-sidebar__week-picker">
            <label htmlFor="week-select">Roster Week</label>
            <select
              id="week-select"
              value={selectedWeek}
              onChange={event => setSelectedWeek(event.target.value)}
              disabled={availableWeeks.length === 0}
            >
              {availableWeeks.length === 0 ? (
                <option value="">No roster weeks</option>
              ) : (
                availableWeeks.map(week => (
                  <option key={week} value={week}>
                    {week}
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="app-sidebar__footer">
            <button type="button" className="app-sidebar__switch" onClick={clearRole}>
              Switch Role
            </button>
          </div>
        </aside>

        <main className="app-content">
          <Routes>
            <Route
              path="/"
              element={(
                <RoleGate role={role} allowedRoles={["manager", "staff"]}>
                  <DashboardPage shifts={shifts} weekStartDate={selectedWeek || undefined} />
                </RoleGate>
              )}
            />
            <Route
              path="/shift-coverage"
              element={(
                <RoleGate role={role} allowedRoles={["manager"]}>
                  <ShiftCoverage weekStartDate={selectedWeek || undefined} />
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
                  <GenerateRoster
                    refreshRoster={fetchRoster}
                    refreshWeeks={fetchWeeks}
                    startDate={selectedWeek || undefined}
                  />
                </RoleGate>
              )}
            />
            <Route
              path="/manage-shifts"
              element={(
                <RoleGate role={role} allowedRoles={["manager"]}>
                  <ManageShiftAssignments weekStartDate={selectedWeek || undefined} />
                </RoleGate>
              )}
            />
            <Route
              path="/my-roster"
              element={(
                <RoleGate role={role} allowedRoles={["manager", "staff"]}>
                  <MyRoster weekStartDate={selectedWeek || undefined} />
                </RoleGate>
              )}
            />
            <Route
              path="/my-profile"
              element={(
                <RoleGate role={role} allowedRoles={["manager", "staff"]}>
                  <MyProfile weekStartDate={selectedWeek || undefined} />
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
        </main>
      </div>
    </Router>
  );
}
