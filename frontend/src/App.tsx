import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api/client";
import { Layout } from "./components/Layout";
import { AccountsPage } from "./pages/AccountsPage";
import { BroadcastPage } from "./pages/BroadcastPage";
import { ChatsPage } from "./pages/ChatsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/accounts" element={<AccountsPage />} />
        <Route path="/chats" element={<ChatsPage />} />
        <Route path="/broadcast" element={<BroadcastPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
