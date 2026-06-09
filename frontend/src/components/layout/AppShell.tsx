import { NavLink } from "react-router-dom";
import { ReceiptText } from "lucide-react";
import type { ReactNode } from "react";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
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
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
