import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from "react-router-dom";
import { type ReactElement, useCallback, useEffect, useState } from "react";
import "./App.css";

import API, { setAuthErrorHandlers, setAuthToken } from "./services/api";
import RosterTable from "./components/RosterTable";
import UserAvailabilityForm from "./components/UserAvailabilityForm";
import GenerateRoster from "./components/GenerateRoster";
import ManageShiftAssignments from "./components/ManageShiftAssignments";
import DeleteRosterWeek from "./components/DeleteRosterWeek";
import RemoveUser from "./components/RemoveUser";
import MyRoster from "./components/MyRoster";
import ShiftCoverage from "./components/ShiftCoverage";
import MyProfile from "./components/MyProfile";
import Login from "./components/Login";
import CreateWorkplace from "./components/CreateWorkplace";
import AuthChoice from "./components/AuthChoice";

interface DashboardPageProps {
  shifts: any[];
  weekStartDate?: string;
}

type AppRole = "manager" | "staff";
type AuthView = "chooser" | "login" | "create";

interface AuthUser {
  id: number;
  name: string;
  role: AppRole;
  is_active: boolean;
}

interface OnboardingStatusResponse {
  is_bootstrapped: boolean;
}

function formatWeekOption(weekStartDate: string) {
  const [year, month, day] = weekStartDate.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const dayOfWeek = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayOfWeek);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNumber = Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  const dd = String(day).padStart(2, "0");
  const mm = String(month).padStart(2, "0");
  const yyyy = String(year);
  return `Week ${weekNumber} - ${dd}/${mm}/${yyyy}`;
}

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
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [isBootstrapped, setIsBootstrapped] = useState(false);
  const [authView, setAuthView] = useState<AuthView>("chooser");
  const [authzMessage, setAuthzMessage] = useState("");
  const [shifts, setShifts] = useState<any[]>([]);
  const [availableWeeks, setAvailableWeeks] = useState<string[]>([]);
  const [selectedWeek, setSelectedWeek] = useState<string>("");
  const demoHostname = (process.env.REACT_APP_DEMO_HOSTNAME || "").trim().toLowerCase();
  const showDemoUi =
    process.env.REACT_APP_SHOW_DEMO_UI === "true" ||
    (Boolean(demoHostname) && window.location.hostname.toLowerCase() === demoHostname);

  const role = authUser?.role ?? null;

  const clearAuth = useCallback(() => {
    setAuthToken(null);
    setAuthUser(null);
    setAuthView("chooser");
    setAuthzMessage("");
    setShifts([]);
    setAvailableWeeks([]);
    setSelectedWeek("");
  }, []);

  useEffect(() => {
    setAuthErrorHandlers({
      onUnauthorized: () => clearAuth(),
      onForbidden: () => setAuthzMessage("You are not authorized to perform that action."),
    });
    return () => setAuthErrorHandlers({});
  }, [clearAuth]);

  const fetchRoster = useCallback(() => {
    if (!authUser) return;
    API.get("/roster", selectedWeek ? { params: { week_start_date: selectedWeek } } : undefined)
      .then(res => setShifts(res.data))
      .catch(err => {
        console.error(err);
        if (err?.response?.status === 401) clearAuth();
      });
  }, [authUser, clearAuth, selectedWeek]);

  const fetchWeeks = useCallback(() => {
    if (!authUser) return;
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
      .catch(err => {
        console.error(err);
        if (err?.response?.status === 401) clearAuth();
      });
  }, [authUser, clearAuth]);

  useEffect(() => {
    let cancelled = false;

    async function initializeApp() {
      clearAuth();
      try {
        const response = await API.get<OnboardingStatusResponse>("/onboarding/status");
        if (!cancelled) {
          setIsBootstrapped(response.data.is_bootstrapped);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setIsBootstrapped(true);
        }
      } finally {
        if (!cancelled) {
          setAuthReady(true);
        }
      }
    }

    initializeApp();

    return () => {
      cancelled = true;
    };
  }, [clearAuth]);

  useEffect(() => {
    if (!authUser) return;
    fetchWeeks();
  }, [authUser, fetchWeeks]);

  useEffect(() => {
    if (!authUser) return;
    fetchRoster();
  }, [authUser, fetchRoster]);

  if (!authReady) {
    return (
      <main style={{ maxWidth: 560, margin: "80px auto", padding: 20 }}>
        <h1 style={{ marginTop: 0 }}>Loading session...</h1>
      </main>
    );
  }

  if (!role) {
    if (authView === "login") {
      return <Login onLoginSuccess={user => {
        setAuthUser(user);
        setAuthzMessage("");
      }} />;
    }

    if (authView === "create") {
      return <CreateWorkplace onCreateSuccess={user => {
        setAuthUser(user);
        setIsBootstrapped(true);
        setAuthzMessage("");
      }} />;
    }

    return (
      <AuthChoice
        isBootstrapped={isBootstrapped}
        onSelectLogin={() => setAuthView("login")}
        onSelectCreate={() => setAuthView("create")}
        showDemoCredentials={showDemoUi}
      />
    );
  }

  const navItems =
    role === "manager"
      ? [
          { to: "/", label: "Roster Dashboard" },
          { to: "/shift-coverage", label: "Shift Coverage" },
          { to: "/generate-roster", label: "Generate Roster" },
          { to: "/manage-shifts", label: "Manage Shifts" },
          { to: "/delete-roster-week", label: "Delete Roster Week" },
          { to: "/remove-user", label: "Remove User" },
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
                    {formatWeekOption(week)}
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="app-sidebar__footer">
            <button type="button" className="app-sidebar__switch" onClick={clearAuth}>
              Sign Out
            </button>
          </div>
        </aside>

        <main className="app-content">
          {showDemoUi && (
            <p className="app-content__demo-banner">
              Demo environment: data resets nightly at midnight (US Eastern).
            </p>
          )}
          {authzMessage && <p className="app-content__notice">{authzMessage}</p>}
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
              path="/delete-roster-week"
              element={(
                <RoleGate role={role} allowedRoles={["manager"]}>
                  <DeleteRosterWeek
                    selectedWeek={selectedWeek || undefined}
                    availableWeeks={availableWeeks}
                    refreshRoster={fetchRoster}
                    refreshWeeks={fetchWeeks}
                  />
                </RoleGate>
              )}
            />
            <Route
              path="/remove-user"
              element={(
                <RoleGate role={role} allowedRoles={["manager"]}>
                  <RemoveUser refreshRoster={fetchRoster} />
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
