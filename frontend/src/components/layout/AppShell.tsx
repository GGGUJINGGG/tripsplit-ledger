import {
  NavLink,
  useNavigate,
} from "react-router-dom";
import {
  LogOut,
  ReceiptText,
} from "lucide-react";
import type { ReactNode } from "react";

import { useAuth } from "../../auth/AuthContext";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  function handleLogout(): void {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">
            <ReceiptText size={22} />
          </span>
          <div>
            <strong>TripSplit</strong>
            <span>Ledger</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Primary navigation">
          <NavLink to="/">Trips</NavLink>
        </nav>
        <div className="sidebar-account">
          <div>
            <strong>{user?.display_name}</strong>
            <span>{user?.email}</span>
          </div>

          <button
            className="sidebar-logout"
            type="button"
            onClick={handleLogout}
          >
            <LogOut size={17} />
            Log out
          </button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
