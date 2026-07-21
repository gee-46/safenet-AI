import { motion } from "framer-motion";
import { PhoneCall, Banknote, Share2, MapPinned, ShieldCheck } from "lucide-react";

const orbit = (delay) => ({
  animate: { rotate: 360 },
  transition: { duration: 34, repeat: Infinity, ease: "linear", delay },
});

const float = (delay = 0, dist = 10) => ({
  animate: { y: [0, -dist, 0] },
  transition: { duration: 5 + delay, repeat: Infinity, ease: "easeInOut", delay },
});

function OrbitBadge({ angle, radius, icon: Icon, color, delay }) {
  const rad = (angle * Math.PI) / 180;
  const x = Math.cos(rad) * radius;
  const y = Math.sin(rad) * radius;
  return (
    <motion.div
      className="absolute left-1/2 top-1/2 flex h-10 w-10 items-center justify-center rounded-xl border backdrop-blur-sm"
      style={{
        marginLeft: x - 20,
        marginTop: y - 20,
        borderColor: `${color}55`,
        background: `${color}14`,
        boxShadow: `0 0 24px -6px ${color}88`,
      }}
      {...float(delay, 8)}
    >
      <Icon className="h-4 w-4" style={{ color }} />
    </motion.div>
  );
}

export function HeroVisual() {
  return (
    <div className="relative mx-auto flex h-[340px] w-[340px] items-center justify-center sm:h-[420px] sm:w-[420px]">
      {/* concentric rings */}
      {[1, 0.72, 0.46].map((s, i) => (
        <div
          key={i}
          className="absolute rounded-full border border-void-line"
          style={{ width: `${s * 100}%`, height: `${s * 100}%` }}
        />
      ))}

      {/* radar sweep */}
      <div className="absolute inset-0 overflow-hidden rounded-full">
        <motion.div
          className="absolute inset-0 origin-center"
          style={{ background: "conic-gradient(from 0deg, rgba(255,90,54,0.45), transparent 32%)" }}
          animate={{ rotate: 360 }}
          transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
        />
      </div>

      {/* hex core */}
      <div className="relative z-10 flex h-24 w-24 items-center justify-center rounded-2xl border border-signal/40 bg-void-surface/90 shadow-[0_0_40px_-8px_rgba(255,90,54,0.5)] sm:h-28 sm:w-28">
        <ShieldCheck className="h-9 w-9 text-signal-soft" strokeWidth={1.5} />
      </div>

      {/* orbiting module badges */}
      <motion.div className="absolute inset-0" {...orbit(0)}>
        <OrbitBadge angle={0} radius={148} icon={PhoneCall} color="#FF5A36" delay={0} />
        <OrbitBadge angle={72} radius={148} icon={Banknote} color="#C9A227" delay={0.4} />
        <OrbitBadge angle={144} radius={148} icon={Share2} color="#8B7CF6" delay={0.8} />
        <OrbitBadge angle={216} radius={148} icon={MapPinned} color="#2FD9C4" delay={1.2} />
        <OrbitBadge angle={288} radius={148} icon={ShieldCheck} color="#F0B429" delay={1.6} />
      </motion.div>

      {/* floating verdict chips */}
      <motion.div
        className="absolute -left-4 top-6 rounded-lg border border-void-line bg-void-surface/95 px-3 py-2 shadow-xl backdrop-blur-sm sm:-left-10"
        {...float(0.2, 10)}
      >
        <p className="font-mono text-[9px] uppercase tracking-wider text-signal-soft">Digital-arrest scam</p>
        <p className="font-mono text-xs tabular text-ink">94% confidence</p>
      </motion.div>
      <motion.div
        className="absolute -right-2 bottom-10 rounded-lg border border-void-line bg-void-surface/95 px-3 py-2 shadow-xl backdrop-blur-sm sm:-right-8"
        {...float(1, 12)}
      >
        <p className="font-mono text-[9px] uppercase tracking-wider text-verified-soft">₹500 note · genuine</p>
        <p className="font-mono text-xs tabular text-ink">98% confidence</p>
      </motion.div>
      <motion.div
        className="absolute bottom-0 left-6 rounded-lg border border-void-line bg-void-surface/95 px-3 py-2 shadow-xl backdrop-blur-sm sm:left-2"
        {...float(1.6, 8)}
      >
        <p className="font-mono text-[9px] uppercase tracking-wider text-gold-soft">Network risk</p>
        <p className="font-mono text-xs tabular text-ink">14 linked accounts</p>
      </motion.div>
    </div>
  );
}
