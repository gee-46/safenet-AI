import { useState, Suspense, lazy } from "react";
import { Routes, Route, useLocation, Navigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Sidebar, Topbar, MobileSidebar, nav } from "./components/layout/Shell";
import { useAuth } from "./context/AuthContext";

const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const ScamShield = lazy(() => import("./pages/ScamShield"));
const CounterfeitLens = lazy(() => import("./pages/CounterfeitLens"));
const FraudGraph = lazy(() => import("./pages/FraudGraph"));
const GeoIntel = lazy(() => import("./pages/GeoIntel"));
const CitizenShield = lazy(() => import("./pages/CitizenShield"));
const Evidence = lazy(() => import("./pages/Evidence"));
const NotFound = lazy(() => import("./pages/NotFound"));

function RouteFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-void-line border-t-signal" />
    </div>
  );
}

function PageTransition({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

function ProtectedRoute({ children }) {
  const { isLoggedIn, loading } = useAuth();

  if (loading) {
    return <RouteFallback />;
  }

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function ConsoleLayout({ children }) {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const current = nav.find((n) => (n.end ? location.pathname === n.to : location.pathname.startsWith(n.to)));

  return (
    <div className="flex min-h-screen bg-void">
      <Sidebar />
      <MobileSidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="flex min-h-screen flex-1 flex-col">
        <Topbar title={current?.label || "SafeNet AI"} onMenu={() => setMenuOpen(true)} />
        <main className="flex-1 px-4 py-8 sm:px-8">
          <div className="mx-auto max-w-7xl">{children}</div>
          <footer className="mx-auto mt-16 max-w-7xl border-t border-void-line pt-6 pb-4">
            <p className="font-mono text-[11px] text-ink-faint">
              SafeNet AI · India's unified public safety intelligence platform · Built for the ET AI Hackathon 2026
            </p>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const location = useLocation();
  const isConsole = location.pathname.startsWith("/console");

  const routes = (
    <Suspense fallback={<RouteFallback />}>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<PageTransition><Landing /></PageTransition>} />
          <Route path="/login" element={<PageTransition><Login /></PageTransition>} />
          <Route path="/console" element={<ProtectedRoute><PageTransition><Dashboard /></PageTransition></ProtectedRoute>} />
          <Route path="/console/scam-shield" element={<ProtectedRoute><PageTransition><ScamShield /></PageTransition></ProtectedRoute>} />
          <Route path="/console/counterfeit-lens" element={<ProtectedRoute><PageTransition><CounterfeitLens /></PageTransition></ProtectedRoute>} />
          <Route path="/console/fraud-graph" element={<ProtectedRoute><PageTransition><FraudGraph /></PageTransition></ProtectedRoute>} />
          <Route path="/console/geo-intel" element={<ProtectedRoute><PageTransition><GeoIntel /></PageTransition></ProtectedRoute>} />
          <Route path="/console/citizen-shield" element={<ProtectedRoute><PageTransition><CitizenShield /></PageTransition></ProtectedRoute>} />
          <Route path="/console/evidence" element={<ProtectedRoute><PageTransition><Evidence /></PageTransition></ProtectedRoute>} />
          <Route path="*" element={<PageTransition><NotFound /></PageTransition>} />
        </Routes>
      </AnimatePresence>
    </Suspense>
  );

  if (!isConsole) return routes;
  return <ConsoleLayout>{routes}</ConsoleLayout>;
}
