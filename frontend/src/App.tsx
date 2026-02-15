import { useEffect, useState } from "react";
import API from "./services/api";
import RosterTable from "./components/RosterTable";

interface Staff {
  id: number;
  name: string;
}

interface ShiftAssignment {
  day_of_week: number;
  start_time: string;
  end_time: string;
  staff: Staff[];
}

function App() {
  const [shifts, setShifts] = useState<ShiftAssignment[]>([]);

  useEffect(() => {
    API.get("/roster")
      .then(res => setShifts(res.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div style={{ padding: "20px" }}>
      <h1>Roster Dashboard</h1>
      <RosterTable shifts={shifts} />
    </div>
  );
}

export default App;
