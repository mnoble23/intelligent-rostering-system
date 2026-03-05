import { useEffect, useState } from "react";
import API, { formatApiError } from "../services/api";
import "./UserAvailabilityForm.css";

interface AvailabilityApiRow {
  id: number;
  user_id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
}

interface AuthUser {
  id: number;
  name: string;
  role: "staff" | "manager";
}

interface ManagerUser {
  id: number;
  name: string;
  role: "staff" | "manager";
  min_hours: number;
  max_hours: number;
  min_shifts_per_week: number;
  max_shifts_per_week: number;
}

type ManagerMode = "new" | "existing";
type DayMode = "unavailable" | "full" | "custom";

interface TimeBlock {
  start_time: string;
  end_time: string;
}

interface DayPlan {
  day_of_week: number;
  mode: DayMode;
  blocks: TimeBlock[];
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const BUSINESS_OPEN = "06:00";
const BUSINESS_CLOSE = "22:00";

function toHHMM(value: string) {
  const [hour = "00", minute = "00"] = value.split(":");
  return `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
}

function hhmmToMinutes(value: string) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function buildEmptyDayPlans(): DayPlan[] {
  return DAYS.map((_, dayIndex) => ({
    day_of_week: dayIndex,
    mode: "custom" as DayMode,
    blocks: [{ start_time: "", end_time: "" }],
  }));
}

function mapApiAvailabilityToDayPlans(rows: AvailabilityApiRow[]): DayPlan[] {
  const grouped = new Map<number, TimeBlock[]>();
  for (const row of rows) {
    const list = grouped.get(row.day_of_week) ?? [];
    list.push({
      start_time: toHHMM(row.start_time),
      end_time: toHHMM(row.end_time),
    });
    grouped.set(row.day_of_week, list);
  }

  return DAYS.map((_, dayIndex) => {
    const blocks = (grouped.get(dayIndex) ?? []).sort((a, b) => a.start_time.localeCompare(b.start_time));
    if (blocks.length === 0) {
      return {
        day_of_week: dayIndex,
        mode: "custom" as DayMode,
        blocks: [{ start_time: "", end_time: "" }],
      };
    }

    const isFullDayOnly =
      blocks.length === 1 &&
      blocks[0].start_time === BUSINESS_OPEN &&
      blocks[0].end_time === BUSINESS_CLOSE;

    if (isFullDayOnly) {
      return {
        day_of_week: dayIndex,
        mode: "full" as DayMode,
        blocks,
      };
    }

    return {
      day_of_week: dayIndex,
      mode: "custom" as DayMode,
      blocks,
    };
  });
}

export default function UserAvailabilityForm() {
  const [name, setName] = useState("");
  const [role, setRole] = useState<"staff" | "manager">("staff");
  const [minHours, setMinHours] = useState(0);
  const [maxHours, setMaxHours] = useState(40);
  const [minShiftsPerWeek, setMinShiftsPerWeek] = useState(1);
  const [maxShiftsPerWeek, setMaxShiftsPerWeek] = useState(7);
  const [dayPlans, setDayPlans] = useState<DayPlan[]>(buildEmptyDayPlans());

  const [managerMode, setManagerMode] = useState<ManagerMode | null>(null);
  const [managerUsers, setManagerUsers] = useState<ManagerUser[]>([]);
  const [selectedExistingUserId, setSelectedExistingUserId] = useState<number | "">("");
  const [existingUserSearch, setExistingUserSearch] = useState("");
  const [isExistingUserMenuOpen, setIsExistingUserMenuOpen] = useState(false);
  const [availabilityRows, setAvailabilityRows] = useState<AvailabilityApiRow[]>([]);

  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"idle" | "success" | "error">("idle");

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const meResponse = await API.get<AuthUser>("/auth/me");
        setAuthUser(meResponse.data);

        if (meResponse.data.role === "staff") {
          setName(meResponse.data.name);
          setRole("staff");
          const availabilityResponse = await API.get<AvailabilityApiRow[]>("/availability");
          setDayPlans(mapApiAvailabilityToDayPlans(availabilityResponse.data ?? []));
          return;
        }

        const [usersResponse, availabilityResponse] = await Promise.all([
          API.get<ManagerUser[]>("/users/"),
          API.get<AvailabilityApiRow[]>("/availability"),
        ]);
        setManagerUsers(usersResponse.data ?? []);
        setAvailabilityRows(availabilityResponse.data ?? []);
      } catch (err) {
        console.error(err);
        setStatus(formatApiError(err, { fallbackMessage: "Failed to load authenticated user." }));
        setStatusType("error");
      }
    };

    loadInitialData();
  }, []);

  useEffect(() => {
    if (authUser?.role !== "manager") return;

    if (managerMode === null) {
      setSelectedExistingUserId("");
      return;
    }

    if (managerMode === "new") {
      setSelectedExistingUserId("");
      setExistingUserSearch("");
      setName("");
      setRole("staff");
      setMinHours(0);
      setMaxHours(40);
      setMinShiftsPerWeek(1);
      setMaxShiftsPerWeek(7);
      setDayPlans(buildEmptyDayPlans());
      return;
    }

    if (managerUsers.length === 0) {
      setSelectedExistingUserId("");
    }
  }, [authUser?.role, managerMode, managerUsers]);

  useEffect(() => {
    if (authUser?.role !== "manager" || managerMode !== "existing" || selectedExistingUserId === "") return;

    const selectedUser = managerUsers.find(user => user.id === selectedExistingUserId);
    if (!selectedUser) return;

    setName(selectedUser.name);
    setRole(selectedUser.role);
    setMinHours(selectedUser.min_hours);
    setMaxHours(selectedUser.max_hours);
    setMinShiftsPerWeek(selectedUser.min_shifts_per_week);
    setMaxShiftsPerWeek(selectedUser.max_shifts_per_week);

    const selectedAvailability = availabilityRows.filter(row => row.user_id === selectedUser.id);
    setDayPlans(mapApiAvailabilityToDayPlans(selectedAvailability));
  }, [authUser?.role, managerMode, selectedExistingUserId, managerUsers, availabilityRows]);

  const updateDayMode = (dayIndex: number, mode: DayMode) => {
    setDayPlans(prev =>
      prev.map(plan => {
        if (plan.day_of_week !== dayIndex) return plan;
        if (mode === "full") {
          return {
            ...plan,
            mode,
            blocks: [{ start_time: BUSINESS_OPEN, end_time: BUSINESS_CLOSE }],
          };
        }
        if (mode === "unavailable") {
          return {
            ...plan,
            mode,
            blocks: [{ start_time: "", end_time: "" }],
          };
        }
        return {
          ...plan,
          mode,
          blocks: plan.blocks.length > 0 ? plan.blocks : [{ start_time: "", end_time: "" }],
        };
      })
    );
  };

  const updateBlock = (dayIndex: number, blockIndex: number, field: keyof TimeBlock, value: string) => {
    setDayPlans(prev =>
      prev.map(plan => {
        if (plan.day_of_week !== dayIndex) return plan;
        return {
          ...plan,
          blocks: plan.blocks.map((block, idx) => (idx === blockIndex ? { ...block, [field]: value } : block)),
        };
      })
    );
  };

  const addExtraBlock = (dayIndex: number) => {
    setDayPlans(prev =>
      prev.map(plan => {
        if (plan.day_of_week !== dayIndex) return plan;
        return {
          ...plan,
          mode: "custom",
          blocks: [...plan.blocks, { start_time: "", end_time: "" }],
        };
      })
    );
  };

  const removeBlock = (dayIndex: number, blockIndex: number) => {
    setDayPlans(prev =>
      prev.map(plan => {
        if (plan.day_of_week !== dayIndex) return plan;
        if (plan.blocks.length <= 1) return plan;
        return {
          ...plan,
          blocks: plan.blocks.filter((_, idx) => idx !== blockIndex),
        };
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("");
    setStatusType("idle");

    if (authUser?.role === "manager" && managerMode === null) {
      setStatus("Choose Add New User or Update Existing User first.");
      setStatusType("error");
      return;
    }

    if (!name.trim()) {
      setStatus("Please enter a name.");
      setStatusType("error");
      return;
    }
    if (minHours < 0 || maxHours < 0) {
      setStatus("Minimum and maximum hours must be zero or greater.");
      setStatusType("error");
      return;
    }
    if (maxHours < minHours) {
      setStatus("Maximum hours must be greater than or equal to minimum hours.");
      setStatusType("error");
      return;
    }
    if (minShiftsPerWeek < 0 || maxShiftsPerWeek < 0) {
      setStatus("Minimum and maximum shifts must be zero or greater.");
      setStatusType("error");
      return;
    }
    if (maxShiftsPerWeek < minShiftsPerWeek) {
      setStatus("Maximum shifts must be greater than or equal to minimum shifts.");
      setStatusType("error");
      return;
    }

    const payloadAvailability: Array<{
      user_id: number;
      day_of_week: number;
      start_time: string;
      end_time: string;
    }> = [];

    for (const plan of dayPlans) {
      if (plan.mode === "unavailable") continue;

      if (plan.mode === "full") {
        payloadAvailability.push({
          user_id: 0,
          day_of_week: plan.day_of_week,
          start_time: `${BUSINESS_OPEN}:00`,
          end_time: `${BUSINESS_CLOSE}:00`,
        });
        continue;
      }

      const normalizedBlocks = plan.blocks
        .map(block => ({
          start: block.start_time,
          end: block.end_time,
        }))
        .sort((a, b) => a.start.localeCompare(b.start));

      if (normalizedBlocks.length === 0) {
        setStatus(`Add at least one time block for ${DAYS[plan.day_of_week]}.`);
        setStatusType("error");
        return;
      }

      for (const block of normalizedBlocks) {
        if (!block.start || !block.end) {
          setStatus(`Complete all start/end times for ${DAYS[plan.day_of_week]}.`);
          setStatusType("error");
          return;
        }
        if (block.start >= block.end) {
          setStatus(`End time must be later than start time for ${DAYS[plan.day_of_week]}.`);
          setStatusType("error");
          return;
        }
      }

      for (let i = 1; i < normalizedBlocks.length; i += 1) {
        if (hhmmToMinutes(normalizedBlocks[i].start) < hhmmToMinutes(normalizedBlocks[i - 1].end)) {
          setStatus(`Availability blocks overlap on ${DAYS[plan.day_of_week]}. Adjust times and try again.`);
          setStatusType("error");
          return;
        }
      }

      for (const block of normalizedBlocks) {
        payloadAvailability.push({
          user_id: 0,
          day_of_week: plan.day_of_week,
          start_time: `${block.start}:00`,
          end_time: `${block.end}:00`,
        });
      }
    }

    if (payloadAvailability.length === 0) {
      setStatus("At least one available day/block is required before submitting.");
      setStatusType("error");
      return;
    }

    try {
      let userId: number | null = null;
      if (authUser?.role === "manager") {
        if (managerMode === "existing" && selectedExistingUserId === "") {
          setStatus("Choose an existing user to update.");
          setStatusType("error");
          return;
        }
        const userRes = await API.post("/users/", {
          name,
          role,
          min_hours: minHours,
          max_hours: maxHours,
          min_shifts_per_week: minShiftsPerWeek,
          max_shifts_per_week: maxShiftsPerWeek,
        });
        userId = userRes.data.id;
      } else {
        userId = authUser?.id ?? null;
      }

      if (!userId) {
        setStatus("Unable to resolve user identity.");
        setStatusType("error");
        return;
      }

      await API.post("/availability/bulk", {
        availabilities: payloadAvailability.map(entry => ({ ...entry, user_id: userId as number })),
      });

      if (authUser?.role === "manager" && managerMode === "existing") {
        setStatus(`User "${name}" updated successfully.`);
      } else if (authUser?.role === "manager") {
        setStatus(`User "${name}" and availability submitted successfully!`);
      } else {
        setStatus("Availability submitted successfully!");
      }
      setStatusType("success");

      if (authUser?.role === "manager") {
        const [usersResponse, availabilityResponse] = await Promise.all([
          API.get<ManagerUser[]>("/users/"),
          API.get<AvailabilityApiRow[]>("/availability"),
        ]);
        setManagerUsers(usersResponse.data ?? []);
        setAvailabilityRows(availabilityResponse.data ?? []);
        if (managerMode === "new") {
          setName("");
          setRole("staff");
          setMinHours(0);
          setMaxHours(40);
          setMinShiftsPerWeek(1);
          setMaxShiftsPerWeek(7);
          setDayPlans(buildEmptyDayPlans());
        }
      } else {
        const availabilityResponse = await API.get<AvailabilityApiRow[]>("/availability");
        setDayPlans(mapApiAvailabilityToDayPlans(availabilityResponse.data ?? []));
      }
    } catch (err: unknown) {
      console.error(err);
      setStatus(formatApiError(err, {
        fallbackMessage: "Failed to submit user and availability details.",
        detailMap: {
          "At least one availability entry is required": "Add at least one availability block before submitting.",
          "You can only manage your own availability": "You can only submit your own availability with this account.",
          "One or more users are not in your workplace": "Selected user is not in this workplace.",
          "Name is required": "Enter a user name before submitting.",
          "role must be 'manager' or 'staff'": "Role must be either manager or staff.",
          "max_hours must be greater than or equal to min_hours": "Max weekly hours must be greater than or equal to min weekly hours.",
          "max_shifts_per_week must be greater than or equal to min_shifts_per_week": "Max weekly shifts must be greater than or equal to min weekly shifts.",
          "password must be at least 8 characters": "Generated user password must be at least 8 characters.",
        },
      }));
      setStatusType("error");
    }
  };

  const showInputs = authUser?.role !== "manager" || managerMode !== null;
  const filteredManagerUsers = managerUsers.filter(user =>
    user.name.toLowerCase().includes(existingUserSearch.trim().toLowerCase())
  );

  return (
    <section className="availability-form">
      <form onSubmit={handleSubmit} className="availability-form__shell">
        <header className="availability-form__hero">
          <p className="availability-form__eyebrow">Intake</p>
          <h2>User & Availability Submission</h2>
          <p className="availability-form__lead">
            Capture staffing details and weekly availability blocks in one clean workflow.
          </p>
        </header>

        {status && <p className={`availability-form__status availability-form__status--${statusType}`}>{status}</p>}

        {authUser?.role === "manager" && (
          <section className="availability-form__mode">
            <p className="availability-form__mode-label">What would you like to do?</p>
            <div className="availability-form__mode-toggle">
              <button
                type="button"
                className={`availability-form__mode-option${managerMode === "new" ? " availability-form__mode-option--active" : ""}`}
                onClick={() => setManagerMode("new")}
              >
                Add New User
              </button>
              <button
                type="button"
                className={`availability-form__mode-option${managerMode === "existing" ? " availability-form__mode-option--active" : ""}`}
                onClick={() => setManagerMode("existing")}
              >
                Update Existing User
              </button>
            </div>
          </section>
        )}

        {showInputs ? (
          <>
            <div className="availability-form__grid">
              {authUser?.role === "manager" ? (
                <>
                  {managerMode === "existing" && (
                    <label className="availability-form__field">
                      <span>Select Existing User</span>
                      <div className="availability-form__user-picker">
                        <input
                          type="text"
                          value={existingUserSearch}
                          placeholder={managerUsers.length === 0 ? "No users available" : "Search user by name..."}
                          onChange={e => {
                            setExistingUserSearch(e.target.value);
                            setIsExistingUserMenuOpen(true);
                          }}
                          onFocus={() => setIsExistingUserMenuOpen(true)}
                          onBlur={() => window.setTimeout(() => setIsExistingUserMenuOpen(false), 120)}
                          disabled={managerUsers.length === 0}
                        />
                        {isExistingUserMenuOpen && managerUsers.length > 0 && (
                          <div className="availability-form__user-menu">
                            {filteredManagerUsers.length === 0 ? (
                              <div className="availability-form__user-item availability-form__user-item--empty">No matches</div>
                            ) : (
                              filteredManagerUsers.map(user => (
                                <button
                                  key={user.id}
                                  type="button"
                                  className={`availability-form__user-item${selectedExistingUserId === user.id ? " availability-form__user-item--active" : ""}`}
                                  onMouseDown={() => {
                                    setSelectedExistingUserId(user.id);
                                    setExistingUserSearch(user.name);
                                    setIsExistingUserMenuOpen(false);
                                  }}
                                >
                                  {user.name}
                                </button>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    </label>
                  )}
                  <label className="availability-form__field">
                    <span>Name</span>
                    <input
                      type="text"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      disabled={managerMode === "existing"}
                      required
                    />
                  </label>
                  <label className="availability-form__field">
                    <span>Role</span>
                    <select
                      value={role}
                      onChange={e => setRole(e.target.value as "staff" | "manager")}
                    >
                      <option value="staff">Staff</option>
                      <option value="manager">Manager</option>
                    </select>
                  </label>
                  <label className="availability-form__field">
                    <span>Min Weekly Hours</span>
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      value={minHours}
                      onChange={e => setMinHours(Number(e.target.value))}
                    />
                  </label>
                  <label className="availability-form__field">
                    <span>Max Weekly Hours</span>
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      value={maxHours}
                      onChange={e => setMaxHours(Number(e.target.value))}
                    />
                  </label>
                  <label className="availability-form__field">
                    <span>Min Weekly Shifts</span>
                    <input
                      type="number"
                      min={0}
                      max={7}
                      step={1}
                      value={minShiftsPerWeek}
                      onChange={e => setMinShiftsPerWeek(Number(e.target.value))}
                    />
                  </label>
                  <label className="availability-form__field">
                    <span>Max Weekly Shifts</span>
                    <input
                      type="number"
                      min={0}
                      max={7}
                      step={1}
                      value={maxShiftsPerWeek}
                      onChange={e => setMaxShiftsPerWeek(Number(e.target.value))}
                    />
                  </label>
                </>
              ) : (
                <label className="availability-form__field">
                  <span>Logged in as</span>
                  <input type="text" value={authUser?.name ?? ""} disabled />
                </label>
              )}
            </div>

            <section className="availability-form__availability">
              <div className="availability-form__availability-head">
                <h3>Weekly Availability</h3>
              </div>

              <div className="availability-form__week-grid">
                {dayPlans.map(plan => (
                  <article key={plan.day_of_week} className="availability-day-card">
                    <header className="availability-day-card__head">
                      <h4>{DAYS[plan.day_of_week]}</h4>
                      <div className="availability-day-card__modes">
                        <button
                          type="button"
                          className={`availability-day-card__mode${plan.mode === "full" ? " availability-day-card__mode--active" : ""}`}
                          onClick={() => updateDayMode(plan.day_of_week, "full")}
                        >
                          Fully Available
                        </button>
                        <button
                          type="button"
                          className={`availability-day-card__mode${plan.mode === "unavailable" ? " availability-day-card__mode--active" : ""}`}
                          onClick={() => updateDayMode(plan.day_of_week, "unavailable")}
                        >
                          Not Available
                        </button>
                        <button
                          type="button"
                          className={`availability-day-card__mode${plan.mode === "custom" ? " availability-day-card__mode--active" : ""}`}
                          onClick={() => updateDayMode(plan.day_of_week, "custom")}
                        >
                          Custom Times
                        </button>
                      </div>
                    </header>

                    {plan.mode === "custom" && (
                      <div className="availability-day-card__blocks">
                        {plan.blocks.map((block, blockIndex) => (
                          <div key={`${plan.day_of_week}-${blockIndex}`} className="availability-day-card__block">
                            <label>
                              <span>Start</span>
                              <input
                                type="time"
                                value={block.start_time}
                                onChange={e => updateBlock(plan.day_of_week, blockIndex, "start_time", e.target.value)}
                              />
                            </label>
                            <label>
                              <span>End</span>
                              <input
                                type="time"
                                value={block.end_time}
                                onChange={e => updateBlock(plan.day_of_week, blockIndex, "end_time", e.target.value)}
                              />
                            </label>
                            <button
                              type="button"
                              onClick={() => removeBlock(plan.day_of_week, blockIndex)}
                              disabled={plan.blocks.length <= 1}
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                        <button
                          type="button"
                          className="availability-day-card__add"
                          onClick={() => addExtraBlock(plan.day_of_week)}
                        >
                          + Add Extra Block
                        </button>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>

            <div className="availability-form__actions">
              <button type="submit" className="availability-form__submit">
                {authUser?.role === "manager" && managerMode === "existing"
                  ? "Update User & Availability"
                  : "Submit Availability"}
              </button>
            </div>
          </>
        ) : (
          <p className="availability-form__status availability-form__status--idle">
            Choose a mode above to show user and availability inputs.
          </p>
        )}
      </form>
    </section>
  );
}
