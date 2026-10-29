import { Route, Routes } from "react-router-dom";
import RequireOwner from "./components/RequireOwner";
import History from "./pages/History";
import ReportPage from "./pages/ReportPage";
import Review from "./pages/Review";
import Rules from "./pages/Rules";

export default function App() {
  return (
    <Routes>
      <Route element={<RequireOwner />}>
        <Route path="/" element={<Review />} />
        <Route path="/r/:id" element={<ReportPage />} />
        <Route path="/history" element={<History />} />
        <Route path="/rules" element={<Rules />} />
      </Route>
    </Routes>
  );
}
