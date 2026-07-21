import { useEffect, useState } from "react";
import { NavLink, Link } from "react-router-dom";
import {
  LayoutDashboard,
  PhoneCall,
  Banknote,
  Share2,
  MapPinned,
  ShieldQuestion,
  FolderLock,
  Radio,
  Menu,
  X,
  LogOut,
} from "lucide-react";
import { health } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";

const nav = [
  { to: "/console", label: "Command Overview", icon: LayoutDashboard, end: true },
  { to: "/console/scam-shield", label: "ScamShield", icon: PhoneCall, sub: "Call analysis" },
  { to: "/console/counterfeit-lens", label: "CounterfeitLens", icon: Banknote, sub: "Currency scan" },
  { to: "/console/fraud-graph", label: "FraudGraph", icon: Share2, sub: "Network intel" },
  { to: "/console/geo-intel", label: "GeoIntel", icon: MapPinned, sub: "Patrol zones" },
  { to: "/console/citizen-shield", label: "CitizenShield", icon: ShieldQuestion, sub: "Public advisor" },
  { to: "/console/evidence", label: "Evidence Vault", icon: FolderLock, sub: "Case packages" },
];

function Clock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <span className="font-mono text-xs tabular text-ink-dim">
      {now.toLocaleTimeString("en-IN", { hour12: false })} IST
    </span>
  );
}

function ApiStatus() {
  const [status, setStatus] = useState("checking");
  useEffect(() => {
    let alive = true;
    const check = () =>
      health()
        .then(() => alive && setStatus("online"))
        .catch(() => alive && setStatus("offline"));
    check();
    const t = setInterval(check, 20000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);
  const tone =
    status === "online" ? "text-verified" : status === "offline" ? "text-signal" : "text-ink-faint";
  return (
    <div className="flex items-center gap-2">
      <span className={`relative flex h-2 w-2 ${tone}`}>
        <span className={`absolute inline-flex h-full w-full animate-ping2 rounded-full bg-current opacity-75`} />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
      </span>
      <span className={`font-mono text-[11px] uppercase tracking-wider ${tone}`}>
        API {status}
      </span>
    </div>
  );
}

function Logo({ compact }) {
  return (
    <Link to="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-80">
      <svg width="26" height="26" viewBox="0 0 100 100" className="shrink-0">
        <polygon
          points="50,4 90,25 90,60 50,96 10,60 10,25"
          fill="none"
          stroke="#FF5A36"
          strokeWidth="6"
        />
        <circle cx="50" cy="45" r="9" fill="#FF5A36" />
      </svg>
      {!compact && (
        <div className="leading-none">
          <div className="font-display text-[15px] font-semibold tracking-tight text-ink">SafeNet AI</div>
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
            Command Console
          </div>
        </div>
      )}
    </Link>
  );
}

export function SidebarContent({ onNavigate }) {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-full flex-col">
      <div className="px-5 pb-6 pt-6">
        <Logo />
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors ${
                isActive
                  ? "bg-void-raised text-ink"
                  : "text-ink-dim hover:bg-void-surface hover:text-ink"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border transition-colors ${
                    isActive
                      ? "border-signal/40 bg-signal-dim/30 text-signal-soft"
                      : "border-void-line bg-void-soft text-ink-faint group-hover:text-ink-dim"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                </span>
                <span className="flex flex-col">
                  <span className="text-sm font-medium leading-tight">{item.label}</span>
                  {item.sub && (
                    <span className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">
                      {item.sub}
                    </span>
                  )}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
      {user && (
        <div className="mx-3 mb-2 rounded-lg border border-void-line bg-void-soft p-3 lg:hidden">
          <p className="truncate text-xs font-medium text-ink">{user.email}</p>
          <p className="font-mono text-[9px] uppercase tracking-wider text-signal-soft">{user.role}</p>
          <button
            onClick={logout}
            className="mt-2 flex w-full items-center justify-center gap-1.5 rounded bg-void-raised py-1.5 font-mono text-[10px] uppercase tracking-wider text-ink-dim transition-colors hover:text-signal"
          >
            <LogOut className="h-3 w-3" /> Log Out
          </button>
        </div>
      )}
      <div className="mx-3 mb-4 mt-6 rounded-lg border border-void-line bg-void-soft p-3">
        <div className="flex items-center gap-2 text-ink-dim">
          <Radio className="h-3.5 w-3.5" />
          <span className="font-mono text-[10px] uppercase tracking-wider">Helpline</span>
        </div>
        <p className="mt-1 font-display text-lg font-semibold text-ink">1930</p>
        <p className="font-mono text-[10px] text-ink-faint">National Cybercrime · 24×7</p>
      </div>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-void-line bg-void-soft/60 lg:block">
      <div className="sticky top-0 h-screen">
        <SidebarContent />
      </div>
    </aside>
  );
}

export function Topbar({ title, onMenu }) {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-void-line bg-void/80 px-4 py-3.5 backdrop-blur-md sm:px-8">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenu}
          className="rounded-md border border-void-line p-1.5 text-ink-dim lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-4 w-4" />
        </button>
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint">
          {title}
        </span>
      </div>
      <div className="flex items-center gap-4">
        <ApiStatus />
        <div className="hidden h-4 w-px bg-void-line sm:block" />
        <Clock />
        {user && (
          <>
            <div className="hidden h-4 w-px bg-void-line sm:block" />
            <div className="flex items-center gap-2">
              <span className="hidden flex-col items-end sm:flex">
                <span className="max-w-[120px] truncate text-[11px] font-medium text-ink">
                  {user.email}
                </span>
                <span className="font-mono text-[9px] uppercase tracking-wider text-signal-soft">
                  {user.role}
                </span>
              </span>
              <button
                onClick={logout}
                title="Log Out"
                className="flex h-7 w-7 items-center justify-center rounded-md border border-void-line bg-void-soft text-ink-faint transition-colors hover:bg-void-raised hover:text-signal"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  );
}

export function MobileSidebar({ open, onClose }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="absolute inset-y-0 left-0 w-72 border-r border-void-line bg-void-soft">
        <button onClick={onClose} className="absolute right-3 top-5 text-ink-dim" aria-label="Close menu">
          <X className="h-5 w-5" />
        </button>
        <SidebarContent onNavigate={onClose} />
      </div>
    </div>
  );
}

export { nav };
