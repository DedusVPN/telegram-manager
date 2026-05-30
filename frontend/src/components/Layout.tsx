import { NavLink, Outlet } from "react-router-dom";
import {
  Globe,
  History,
  LayoutDashboard,
  LogOut,
  Megaphone,
  MessageCircle,
  UserPlus,
  Users,
} from "lucide-react";
import { clearToken } from "../api/client";
import { Icon } from "./Icon";

const links = [
  { to: "/", label: "Дашборд", icon: LayoutDashboard },
  { to: "/accounts", label: "Аккаунты", icon: Users },
  { to: "/registration", label: "Регистрация", icon: UserPlus },
  { to: "/proxies", label: "Прокси", icon: Globe },
  { to: "/chats", label: "Чаты", icon: MessageCircle },
  { to: "/broadcast", label: "Рассылка", icon: Megaphone },
  { to: "/history", label: "История", icon: History },
];

export function Layout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <img src="/logo.svg" alt="Dedus" className="topbar-logo" draggable={false} />
          <div className="topbar-brand-text">
            <strong>Dedus</strong>
            <span>Account Manager</span>
          </div>
        </div>

        <nav className="topbar-nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => `topbar-nav-link${isActive ? " active" : ""}`}
            >
              <Icon icon={link.icon} size="sm" />
              {link.label}
            </NavLink>
          ))}
        </nav>

        <button
          className="topbar-logout"
          type="button"
          title="Выйти"
          onClick={() => {
            clearToken();
            window.location.href = "/login";
          }}
        >
          <Icon icon={LogOut} size="sm" />
          <span className="topbar-logout-label">Выйти</span>
        </button>
      </header>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
