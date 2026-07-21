import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, ArrowUpRight } from "lucide-react";

const links = [
  { href: "#modules", label: "Modules" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#trust", label: "Trust & privacy" },
];

export function PublicNav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 transition-all duration-300 ${
        scrolled ? "border-b border-void-line bg-void/85 backdrop-blur-md" : "border-b border-transparent bg-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-8">
        <Link to="/" className="flex items-center gap-2.5">
          <svg width="26" height="26" viewBox="0 0 100 100">
            <polygon points="50,4 90,25 90,60 50,96 10,60 10,25" fill="none" stroke="#FF5A36" strokeWidth="6" />
            <circle cx="50" cy="45" r="9" fill="#FF5A36" />
          </svg>
          <span className="font-display text-[16px] font-semibold tracking-tight text-ink">SafeNet AI</span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <a key={l.href} href={l.href} className="text-sm text-ink-dim transition-colors hover:text-ink">
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <a href="tel:1930" className="font-mono text-xs text-ink-faint">Helpline 1930</a>
          <Link
            to="/console"
            className="flex items-center gap-1.5 rounded-lg bg-signal px-4 py-2 text-sm font-medium text-white shadow-[0_0_0_1px_rgba(255,90,54,0.4),0_8px_20px_-8px_rgba(255,90,54,0.6)] transition-all hover:bg-signal-soft"
          >
            Open Console <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <button className="text-ink-dim md:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
          <Menu className="h-6 w-6" />
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-void/98 backdrop-blur-md md:hidden"
          >
            <div className="flex items-center justify-between px-4 py-4">
              <span className="font-display text-[16px] font-semibold text-ink">SafeNet AI</span>
              <button onClick={() => setOpen(false)} className="text-ink-dim" aria-label="Close menu">
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="flex flex-col gap-1 px-4 pt-6">
              {links.map((l) => (
                <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="border-b border-void-line py-4 text-lg text-ink">
                  {l.label}
                </a>
              ))}
              <Link to="/console" onClick={() => setOpen(false)} className="mt-6 rounded-lg bg-signal px-4 py-3 text-center font-medium text-white">
                Open Console
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
