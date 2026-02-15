import { useEffect } from "react";
import API from "./services/api";

function App() {
  useEffect(() => {
    API.get("/")
      .then(res => console.log("Backend response:", res.data))
      .catch(err => console.error("Error:", err));
  }, []);

  return <div>Roster Dashboard</div>;
}

export default App;
