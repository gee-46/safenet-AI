import { useEffect, useRef, useState } from "react";
import { motion, useInView, animate } from "framer-motion";

const toneColors = {
  danger: "#FF5A36",
  safe: "#2FD9C4",
  gold: "#C9A227",
  neutral: "#5C6680",
};

/** Signature widget: arc gauge reading like an instrument dial, not a progress bar. */
export function ConfidenceGauge({ value = 0, tone = "neutral", size = 96, label, sub }) {
  const pct = Math.max(0, Math.min(1, value));
  const r = (size - 14) / 2;
  const c = 2 * Math.PI * r;
  const sweep = 270; // degrees of arc used
  const offset = c * (1 - (pct * sweep) / 360);
  const dashArray = `${(c * sweep) / 360} ${c - (c * sweep) / 360}`;
  const color = toneColors[tone] || toneColors.neutral;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-[225deg]">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="#1A2130"
            strokeWidth={7}
            strokeDasharray={dashArray}
            strokeLinecap="round"
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={7}
            strokeDasharray={dashArray}
            strokeLinecap="round"
            initial={{ strokeDashoffset: c }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
            style={{ filter: `drop-shadow(0 0 6px ${color}88)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-lg font-semibold tabular" style={{ color }}>
            {Math.round(pct * 100)}%
          </span>
        </div>
      </div>
      {label && <span className="mt-2 text-xs font-medium text-ink">{label}</span>}
      {sub && <span className="text-[11px] text-ink-faint">{sub}</span>}
    </div>
  );
}

export function Counter({ value = 0, decimals = 0, prefix = "", suffix = "", className = "" }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, value, {
      duration: 1.1,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
  }, [inView, value]);

  return (
    <span ref={ref} className={`tabular ${className}`}>
      {prefix}
      {display.toLocaleString("en-IN", { maximumFractionDigits: decimals, minimumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}
