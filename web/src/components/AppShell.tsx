import clsx from "clsx";
import { Library, Monitor, Moon, Settings, Sun, Upload } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { BrandMark } from "./BrandMark";
import { useThemeMode } from "./ThemeProvider";

const navItems = [
  { to: "/", label: "Biblioteca", icon: Library, end: true },
  { to: "/import", label: "Importar", icon: Upload },
  { to: "/settings", label: "Ajustes", icon: Settings },
];

function sectionLabel(pathname: string): string {
  if (pathname.startsWith("/import")) return "Importar";
  if (pathname.startsWith("/settings")) return "Ajustes";
  if (pathname.includes("/studio")) return "Estudio";
  if (pathname.startsWith("/books/")) return "Libro";
  return "Biblioteca";
}

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

function ThemeToggle() {
  const { mode, setMode } = useThemeMode();
  const options = [
    { value: "system" as const, label: "Sistema", icon: Monitor },
    { value: "light" as const, label: "Claro", icon: Sun },
    { value: "dark" as const, label: "Oscuro", icon: Moon },
  ];
  const current = options.find((option) => option.value === mode) ?? options[0];
  const next = options[(options.findIndex((option) => option.value === mode) + 1) % options.length];
  const Icon = current.icon;

  return (
    <button
      type="button"
      className="icon-button theme-toggle"
      onClick={() => setMode(next.value)}
      aria-label={`Tema ${current.label}. Cambiar a ${next.label}`}
      title={`Tema ${current.label} · cambiar a ${next.label}`}
    >
      <Icon size={18} aria-hidden="true" />
    </button>
  );
}

export function AppShell() {
  const location = useLocation();

  return (
    <>
      <a className="skip-link" href="#main">
        Saltar al contenido
      </a>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="sidebar-spine" aria-hidden="true">
            <span className="spine-mark">VB</span>
            <span className="spine-rule" />
            <span className="spine-label">Biblioteca</span>
            <span className="spine-index">001</span>
          </div>
          <div className="sidebar-content">
            <NavLink className="brand" to="/">
              <BrandMark className="brand-mark" />
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
          </div>
        </aside>

        <main className="main" id="main">
          <div className="topbar">
            <NavLink className="brand topbar-brand-mobile" to="/">
              <BrandMark size={30} className="brand-mark" />
              <span className="brand-name">
                vibe<span>book</span>
              </span>
            </NavLink>
            <div className="topbar-context">
              <span className="topbar-kicker">Taller</span>
              <strong>{sectionLabel(location.pathname)}</strong>
            </div>
            <div className="topbar-actions">
              <span className="local-status">Modo local</span>
              <ThemeToggle />
              <NavLink className="icon-button" to="/settings" aria-label="Ajustes">
                <Settings size={19} aria-hidden="true" />
              </NavLink>
            </div>
          </div>
          <Outlet />
        </main>
      </div>
      <NavItems mobile />
    </>
  );
}
