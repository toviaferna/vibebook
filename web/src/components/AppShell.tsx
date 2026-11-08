import clsx from "clsx";
import { Library, Settings, Upload } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Biblioteca", icon: Library, end: true },
  { to: "/import", label: "Importar", icon: Upload },
  { to: "/settings", label: "Ajustes", icon: Settings },
];

function NavItems({ mobile = false }: { mobile?: boolean }) {
  return (
    <nav className={mobile ? "mobile-nav" : "nav"} aria-label="Navegación principal">
      {!mobile ? <p className="nav-label">Taller</p> : null}
      {navItems.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => clsx("nav-link", isActive && "is-active")}
        >
          <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export function AppShell() {
  return (
    <>
      <a className="skip-link" href="#main">
        Saltar al contenido
      </a>
      <div className="app-shell">
        <aside className="sidebar">
          <NavLink className="brand" to="/">
            <span className="brand-mark" aria-hidden="true">
              V
            </span>
            <span className="brand-name">
              vibe<span>book</span>
            </span>
          </NavLink>
          <NavItems />
          <div className="sidebar-footer">
            <span className="eyebrow">Modo local</span>
            <strong>Tu biblioteca, tu máquina.</strong>
            <p>Los libros y el audio no salen de tu computadora.</p>
          </div>
        </aside>

        <main className="main" id="main">
          <div className="topbar">
            <NavLink className="brand" to="/">
              <span className="brand-mark" aria-hidden="true">
                V
              </span>
              <span className="brand-name">
                vibe<span>book</span>
              </span>
            </NavLink>
            <NavLink className="icon-button" to="/settings" aria-label="Ajustes">
              <Settings size={20} />
            </NavLink>
          </div>
          <Outlet />
        </main>
      </div>
      <NavItems mobile />
    </>
  );
}
