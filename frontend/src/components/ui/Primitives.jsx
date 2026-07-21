import { motion } from "framer-motion";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-dim">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function Card({ children, className = "", hover = true, as: As = "div", ...rest }) {
  return (
    <As className={`card ${hover ? "card-hover" : ""} ${className}`} {...rest}>
      {children}
    </As>
  );
}

export function SectionLabel({ children, right }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h2 className="eyebrow flex items-center gap-2 text-ink-dim">{children}</h2>
      {right}
    </div>
  );
}

const badgeTones = {
  neutral: "bg-void-raised text-ink-dim border-void-line",
  danger: "bg-signal-dim/40 text-signal-soft border-signal-dim",
  safe: "bg-verified-dim/40 text-verified-soft border-verified-dim",
  gold: "bg-gold-dim/40 text-gold-soft border-gold-dim",
  info: "bg-void-raised text-ink border-void-line",
};

export function Badge({ tone = "neutral", children, dot = false, className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider ${badgeTones[tone]} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  icon: Icon,
  className = "",
  ...rest
}) {
  const base =
    "relative inline-flex items-center justify-center gap-2 font-body font-medium transition-all duration-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none";
  const sizes = { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2.5 text-sm", lg: "px-6 py-3.5 text-base" };
  const variants = {
    primary:
      "bg-signal text-white shadow-[0_0_0_1px_rgba(255,90,54,0.4),0_8px_24px_-8px_rgba(255,90,54,0.6)] hover:bg-signal-soft hover:shadow-[0_0_0_1px_rgba(255,90,54,0.6),0_10px_28px_-6px_rgba(255,90,54,0.7)] active:scale-[0.98]",
    verified:
      "bg-verified text-void shadow-[0_0_0_1px_rgba(47,217,196,0.4),0_8px_24px_-8px_rgba(47,217,196,0.6)] hover:bg-verified-soft active:scale-[0.98]",
    ghost: "border border-void-line bg-void-surface/60 text-ink hover:border-ink-faint hover:bg-void-raised active:scale-[0.98]",
    subtle: "text-ink-dim hover:text-ink hover:bg-void-raised",
  };
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} disabled={loading || rest.disabled} {...rest}>
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

export function Field({ label, hint, children, required }) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-ink-dim">
          {label} {required && <span className="text-signal">*</span>}
        </span>
        {hint && <span className="text-[11px] text-ink-faint">{hint}</span>}
      </div>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-void-line bg-void-soft px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-faint transition-colors focus:border-verified/60 focus:outline-none";

export function EmptyState({ title = "Nothing here yet", description, icon: Icon = Inbox }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-void-line py-16 text-center">
      <Icon className="h-8 w-8 text-ink-faint" />
      <div>
        <p className="font-display text-sm font-medium text-ink">{title}</p>
        {description && <p className="mt-1 max-w-sm text-xs text-ink-faint">{description}</p>}
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-signal-dim bg-signal-dim/10 py-14 text-center">
      <AlertTriangle className="h-7 w-7 text-signal-soft" />
      <div>
        <p className="font-display text-sm font-medium text-ink">Couldn't reach the API</p>
        <p className="mt-1 max-w-sm text-xs text-ink-faint">{message}</p>
      </div>
      {onRetry && (
        <Button size="sm" variant="ghost" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-lg bg-void-raised ${className}`} />;
}

export function Reveal({ children, delay = 0, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
