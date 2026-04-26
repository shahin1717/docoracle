import { Routes, Route } from "react-router-dom";
import LoginPage from "./pages/Login";
import Register from "./pages/Register";
import AppPage from "./pages/AppPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<Register />} />
      <Route path="/app" element={<AppPage />} />
    </Routes>
  );
}

export default App;