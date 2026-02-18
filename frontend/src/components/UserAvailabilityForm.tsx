import { useState } from "react";
import API from "../services/api";

interface Availability {
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_full_day: boolean;
}

export default function UserAvailabilityForm() {
  const BUSINESS_OPEN = "06:00";
  const BUSINESS_CLOSE = "22:00";
  const [name, setName] = useState("");
  const [availability, setAvailability] = useState<Availability[]>([
    { day_of_week: 0, start_time: "", end_time: "", is_full_day: false },
  ]);
  const [status, setStatus] = useState("");

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

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

    if (!name.trim()) {
      setStatus("Please enter a name.");
      return;
    }

    for (const av of availability) {
      if (!av.start_time || !av.end_time) {
        setStatus("All availability rows must have start and end times.");
        return;
      }
      if (av.start_time >= av.end_time) {
        setStatus("Start time must be before end time.");
        return;
      }
    }

    try {
      const userRes = await API.post("/users", { name });
      const userId = userRes.data.id;

      const payload = {
      availabilities: availability.map(av => ({
        user_id: userId,
        day_of_week: av.day_of_week,
        start_time: av.start_time + ":00",
        end_time: av.end_time + ":00"
      }))
    };

      await API.post("/availability/bulk", payload);

      setStatus(`User "${name}" and availability submitted successfully!`);
      setName("");
      setAvailability([{ day_of_week: 0, start_time: "", end_time: "", is_full_day: false }]);
    } catch (err) {
      console.error(err);
      setStatus("Failed to submit. Check console for details.");
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 600, margin: "20px auto" }}>
      <h2>User & Availability Submission</h2>

      {status && <p style={{ color: status.startsWith("Failed") ? "red" : "green" }}>{status}</p>}

      <div style={{ marginBottom: 10 }}>
        <label>
          Name:{" "}
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            required
            style={{ width: "100%", padding: 6 }}
          />
        </label>
      </div>

      <h3>Availability</h3>
      {availability.map((av, i) => (
        <div
          key={i}
          style={{ display: "flex", gap: 10, marginBottom: 8, alignItems: "center" }}
        >
          <select
            value={av.day_of_week}
            onChange={e => updateAvailability(i, "day_of_week", +e.target.value)}
          >
            {days.map((day, idx) => (
              <option key={idx} value={idx}>{day}</option>
            ))}
          </select>

          <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              checked={av.is_full_day}
              onChange={e => toggleFullDayAvailability(i, e.target.checked)}
            />
            Fully Available
          </label>

          <input
            type="time"
            value={av.start_time}
            onChange={e => updateAvailability(i, "start_time", e.target.value)}
            required
            disabled={av.is_full_day}
          />
          <input
            type="time"
            value={av.end_time}
            onChange={e => updateAvailability(i, "end_time", e.target.value)}
            required
            disabled={av.is_full_day}
          />

          {availability.length > 1 && (
            <button type="button" onClick={() => removeAvailability(i)}>Remove</button>
          )}
        </div>
      ))}

      <button type="button" onClick={addAvailability} style={{ marginBottom: 10 }}>
        + Add Availability
      </button>

      <div>
        <button type="submit">Submit</button>
      </div>
    </form>
  );
}
