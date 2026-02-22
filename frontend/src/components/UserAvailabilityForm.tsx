import { useEffect, useState } from "react";
import API from "../services/api";
import "./UserAvailabilityForm.css";

interface Availability {
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_full_day: boolean;
}

interface AuthUser {
  id: number;
  name: string;
  role: "staff" | "manager";
}

export default function UserAvailabilityForm() {
  const BUSINESS_OPEN = "06:00";
  const BUSINESS_CLOSE = "22:00";
  const [name, setName] = useState("");
  const [role, setRole] = useState<"staff" | "manager">("staff");
  const [minHours, setMinHours] = useState(0);
  const [maxHours, setMaxHours] = useState(40);
  const [availability, setAvailability] = useState<Availability[]>([
    { day_of_week: 0, start_time: "", end_time: "", is_full_day: false },
  ]);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"idle" | "success" | "error">("idle");

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  useEffect(() => {
    API.get<AuthUser>("/auth/me")
      .then(response => {
        setAuthUser(response.data);
        if (response.data.role === "staff") {
          setName(response.data.name);
          setRole("staff");
        }
      })
      .catch(err => {
        console.error(err);
        setStatus("Failed to load authenticated user.");
        setStatusType("error");
      });
  }, []);

  const addAvailability = () => {
    setAvailability([
      ...availability,
      { day_of_week: 0, start_time: "", end_time: "", is_full_day: false },
    ]);
  };

  const removeAvailability = (index: number) => {
    setAvailability(availability.filter((_, i) => i !== index));
  };

  const updateAvailability = (index: number, field: keyof Availability, value: any) => {
    setAvailability(prev =>
        prev.map((av, i) =>
            i === index ? { ...av, [field]: value } : av
        )
    );
  };

  const toggleFullDayAvailability = (index: number, isChecked: boolean) => {
    setAvailability(prev =>
      prev.map((av, i) => {
        if (i !== index) return av;

        if (isChecked) {
          return {
            ...av,
            is_full_day: true,
            start_time: BUSINESS_OPEN,
            end_time: BUSINESS_CLOSE,
          };
        }

        return {
          ...av,
          is_full_day: false,
          start_time: "",
          end_time: "",
        };
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("");
    setStatusType("idle");

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

    for (const av of availability) {
      if (!av.start_time || !av.end_time) {
        setStatus("All availability rows must have start and end times.");
        setStatusType("error");
        return;
      }
      if (av.start_time >= av.end_time) {
        setStatus("Start time must be before end time.");
        setStatusType("error");
        return;
      }
    }

    try {
      let userId: number | null = null;
      if (authUser?.role === "manager") {
        const userRes = await API.post("/users", {
          name,
          role,
          min_hours: minHours,
          max_hours: maxHours,
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

      const payload = {
        availabilities: availability.map(av => ({
          user_id: userId,
          day_of_week: av.day_of_week,
          start_time: av.start_time + ":00",
          end_time: av.end_time + ":00",
        })),
      };

      await API.post("/availability/bulk", payload);

      setStatus(authUser?.role === "manager"
        ? `User "${name}" and availability submitted successfully!`
        : "Availability submitted successfully!");
      setStatusType("success");
      if (authUser?.role === "manager") {
        setName("");
        setRole("staff");
        setMinHours(0);
        setMaxHours(40);
      }
      setAvailability([{ day_of_week: 0, start_time: "", end_time: "", is_full_day: false }]);
    } catch (err) {
      console.error(err);
      setStatus("Failed to submit. Check console for details.");
      setStatusType("error");
    }
  };

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

        <div className="availability-form__grid">
          {authUser?.role === "manager" ? (
            <>
              <label className="availability-form__field">
                <span>Name</span>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
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
            <h3>Availability Blocks</h3>
            <button type="button" onClick={addAvailability} className="availability-form__add-button">
              + Add Availability
            </button>
          </div>

          <div className="availability-form__rows">
            {availability.map((av, i) => (
              <div key={i} className="availability-row">
                <label className="availability-row__field">
                  <span>Day</span>
                  <select
                    value={av.day_of_week}
                    onChange={e => updateAvailability(i, "day_of_week", +e.target.value)}
                  >
                    {days.map((day, idx) => (
                      <option key={idx} value={idx}>{day}</option>
                    ))}
                  </select>
                </label>

                <label className="availability-row__toggle">
                  <input
                    type="checkbox"
                    checked={av.is_full_day}
                    onChange={e => toggleFullDayAvailability(i, e.target.checked)}
                  />
                  Fully Available
                </label>

                <label className="availability-row__field">
                  <span>Start</span>
                  <input
                    type="time"
                    value={av.start_time}
                    onChange={e => updateAvailability(i, "start_time", e.target.value)}
                    required
                    disabled={av.is_full_day}
                  />
                </label>

                <label className="availability-row__field">
                  <span>End</span>
                  <input
                    type="time"
                    value={av.end_time}
                    onChange={e => updateAvailability(i, "end_time", e.target.value)}
                    required
                    disabled={av.is_full_day}
                  />
                </label>

                {availability.length > 1 && (
                  <button type="button" onClick={() => removeAvailability(i)} className="availability-row__remove">
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>

        <div className="availability-form__actions">
          <button type="submit" className="availability-form__submit">Submit Availability</button>
        </div>
      </form>
    </section>
  );
}
