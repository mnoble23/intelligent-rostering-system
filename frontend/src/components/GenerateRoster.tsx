import API from "../services/api";
import { useState } from "react";

interface GenerateRosterProps {
  refreshRoster?: () => void; 
}

export default function GenerateRoster({ refreshRoster }: GenerateRosterProps) {
  const [status, setStatus] = useState("");

  const handleGenerate = async () => {
    setStatus("Generating roster...");
    try {
      await API.post("/roster/generate");
      setStatus("Roster generated successfully!");
      if (refreshRoster) {
        refreshRoster(); 
      }
    } catch (err) {
      console.error(err);
      setStatus("Failed to generate roster. Check console for details.");
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: "20px auto" }}>
      <h2>Generate Weekly Roster</h2>
      {status && <p>{status}</p>}
      <button onClick={handleGenerate} style={{ padding: "10px 20px" }}>
        Generate Roster
      </button>
    </div>
  );
}
