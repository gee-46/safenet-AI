import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  PhoneCall, Banknote, Share2, MapPinned, ShieldQuestion, FolderLock,
  ArrowRight, Radio, Lock, Languages, Gauge, ScanEye, Network, PhoneIncoming,
  BellRing, FileCheck2,
} from "lucide-react";
import { PublicNav } from "../components/landing/PublicNav";
import { HeroVisual } from "../components/landing/HeroVisual";
import { PhoneWaveArt, NoteArt, GraphArt, MapArt, ChatArt, DocArt } from "../components/landing/ModuleArt";
import { Badge } from "../components/ui/Primitives";

function Reveal({ children, delay = 0, y = 24, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

const MODULES = [
  {
    to: "/console/scam-shield", art: PhoneWaveArt, icon: PhoneCall, tag: "01",
    title: "ScamShield", tint: "#FF5A36",
    desc: "Classifies live call metadata against digital-arrest, KYC, loan, and lottery scripts, then alerts the victim before the call ends.",
  },
  {
    to: "/console/counterfeit-lens", art: NoteArt, icon: Banknote, tag: "02",
    title: "CounterfeitLens", tint: "#C9A227",
    desc: "Computer vision checks watermark, security thread, microprint, and serial format against RBI note specifications.",
  },
  {
    to: "/console/fraud-graph", art: GraphArt, icon: Share2, tag: "03",
    title: "FraudGraph", tint: "#8B7CF6",
    desc: "Traces phone numbers, bank accounts, and devices through a graph to surface mule networks and score connected risk.",
  },
  {
    to: "/console/geo-intel", art: MapArt, icon: MapPinned, tag: "04",
    title: "GeoIntel", tint: "#2FD9C4",
    desc: "Aggregates incidents into H3 hexagonal clusters so patrol resources go where the risk actually is.",
  },
  {
    to: "/console/citizen-shield", art: ChatArt, icon: ShieldQuestion, tag: "05",
    title: "CitizenShield", tint: "#F0B429",
    desc: "A plain-language advisor in 12 Indian languages that tells anyone, instantly, whether a call or message is a scam.",
  },
  {
    to: "/console/evidence", art: DocArt, icon: FolderLock, tag: "06",
    title: "Evidence Vault", tint: "#5C6680",
    desc: "Bundles timelines and network summaries into a PDF with CrPC / IT Act citations, ready to file with an FIR.",
  },
];

const STEPS = [
  { icon: PhoneIncoming, title: "Signal comes in", desc: "A call, an SMS, or a photo of a note enters the system — metadata only, never recordings." },
  { icon: Gauge, title: "Models classify it", desc: "Purpose-built classifiers score it in real time and match it against known fraud patterns." },
  { icon: BellRing, title: "Action is triggered", desc: "High-confidence verdicts alert the person involved and register entities into the fraud graph." },
  { icon: FileCheck2, title: "Case is documented", desc: "Every automated decision is logged for audit, and evidence packages are ready for cyber cells." },
];

function CapabilityStrip() {
  const items = [
    { icon: Languages, label: "12 Indian languages" },
    { icon: ScanEye, label: "4 currency denominations" },
    { icon: Network, label: "Multi-hop fraud graph" },
    { icon: Lock, label: "Metadata-only by design" },
  ];
  return (
    <div className="border-y border-void-line bg-void-soft/50">
      <div className="mx-auto grid max-w-7xl grid-cols-2 gap-6 px-4 py-6 sm:grid-cols-4 sm:px-8">
        {items.map((it) => (
          <div key={it.label} className="flex items-center gap-2.5">
            <it.icon className="h-4 w-4 shrink-0 text-ink-faint" />
            <span className="text-xs text-ink-dim">{it.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModuleCard({ m, i }) {
  return (
    <Reveal delay={i * 0.06}>
      <Link
        to={m.to}
        className="group relative flex h-full flex-col overflow-hidden rounded-2xl border border-void-line bg-void-surface/60 p-5 transition-all duration-300 hover:-translate-y-1 hover:border-void-line hover:bg-void-raised/70"
      >
        <div className="mb-4 h-20 w-full opacity-90 transition-opacity group-hover:opacity-100">
          <m.art />
        </div>
        <div className="mb-2 flex items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">Module {m.tag}</span>
        </div>
        <h3 className="font-display text-lg font-semibold text-ink">{m.title}</h3>
        <p className="mt-1.5 flex-1 text-sm leading-relaxed text-ink-dim">{m.desc}</p>
        <span
          className="mt-4 flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors"
          style={{ color: m.tint }}
        >
          Explore <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-1" />
        </span>
      </Link>
    </Reveal>
  );
}

export default function Landing() {
  return (
    <div className="bg-void">
      <PublicNav />

      {/* Hero */}
      <section className="relative overflow-hidden hex-backdrop">
        <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-10 px-4 pb-16 pt-14 sm:px-8 sm:pb-24 sm:pt-20 lg:grid-cols-2 lg:gap-6">
          <div>
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="eyebrow mb-5 flex items-center gap-2"
            >
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal" />
              Public safety intelligence platform
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.1 }}
              className="font-display text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-5xl lg:text-[3.4rem]"
            >
              Stop scam calls, fake notes,
              <br className="hidden sm:block" /> and fraud rings
              <span className="text-glow-signal text-signal"> in real time.</span>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="mt-5 max-w-lg text-base leading-relaxed text-ink-dim"
            >
              SafeNet AI fuses call-metadata classification, currency computer vision, and graph
              intelligence into one console — built for citizens, cyber cells, and everyone
              between them.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.3 }}
              className="mt-8 flex flex-wrap items-center gap-4"
            >
              <Link
                to="/console"
                className="flex items-center gap-2 rounded-lg bg-signal px-6 py-3.5 text-sm font-medium text-white shadow-[0_0_0_1px_rgba(255,90,54,0.4),0_10px_28px_-8px_rgba(255,90,54,0.65)] transition-all hover:-translate-y-0.5 hover:bg-signal-soft"
              >
                Open Command Console <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/console/citizen-shield"
                className="flex items-center gap-2 rounded-lg border border-void-line bg-void-surface/60 px-6 py-3.5 text-sm font-medium text-ink transition-all hover:-translate-y-0.5 hover:border-ink-faint"
              >
                Check a suspicious call
              </Link>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.9, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          >
            <HeroVisual />
          </motion.div>
        </div>
      </section>

      <CapabilityStrip />

      {/* Modules */}
      <section id="modules" className="mx-auto max-w-7xl px-4 py-20 sm:px-8 sm:py-28">
        <Reveal>
          <div className="mb-12 max-w-2xl">
            <div className="eyebrow mb-3">Six modules, one console</div>
            <h2 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              Every angle of public-safety fraud, covered.
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-ink-dim">
              Each module runs independently and feeds the same fraud graph — a scam call and a
              fake note reported an hour apart can surface as the same network.
            </p>
          </div>
        </Reveal>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m, i) => <ModuleCard key={m.title} m={m} i={i} />)}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-y border-void-line bg-void-soft/40">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <div className="mb-14 max-w-2xl">
              <div className="eyebrow mb-3">How it works</div>
              <h2 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
                From first signal to case file.
              </h2>
            </div>
          </Reveal>
          <div className="relative grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div className="absolute left-0 right-0 top-6 hidden h-px bg-gradient-to-r from-transparent via-void-line to-transparent lg:block" />
            {STEPS.map((s, i) => (
              <Reveal key={s.title} delay={i * 0.1}>
                <div className="relative">
                  <div className="relative z-10 mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-void-line bg-void-surface text-ink-dim">
                    <s.icon className="h-5 w-5" />
                  </div>
                  <p className="font-mono text-[11px] uppercase tracking-wider text-ink-faint">Step {i + 1}</p>
                  <h3 className="mt-1 font-display text-base font-semibold text-ink">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-dim">{s.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Trust / privacy */}
      <section id="trust" className="mx-auto max-w-7xl px-4 py-20 sm:px-8 sm:py-28">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
          <Reveal>
            <div className="eyebrow mb-3">Trust &amp; privacy</div>
            <h2 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              Built to protect people — including from itself.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-dim">
              ScamShield reads call metadata, never audio recordings. CounterfeitLens processes
              images you choose to upload. Every automated verdict — model, confidence, latency —
              is written to an immutable audit trail, so decisions stay explainable to a court, a
              regulator, or the person they were made about.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Badge tone="safe" dot>Metadata, not audio</Badge>
              <Badge tone="neutral">Full decision audit trail</Badge>
              <Badge tone="gold">CrPC &amp; IT Act aligned</Badge>
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="grid grid-cols-2 gap-4">
              {[
                { icon: Radio, label: "Real-time classification", sub: "Sub-second verdicts" },
                { icon: Lock, label: "Privacy by design", sub: "No raw audio stored" },
                { icon: Network, label: "Graph-linked cases", sub: "Cross-module correlation" },
                { icon: FileCheck2, label: "Audit-ready", sub: "Every verdict logged" },
              ].map((c) => (
                <div key={c.label} className="rounded-2xl border border-void-line bg-void-surface/60 p-5">
                  <c.icon className="mb-3 h-5 w-5 text-ink-faint" />
                  <p className="text-sm font-medium text-ink">{c.label}</p>
                  <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-ink-faint">{c.sub}</p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-8">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl border border-void-line bg-void-surface/60 px-6 py-14 text-center hex-backdrop sm:px-16 sm:py-20">
            <h2 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              Bring SafeNet AI to your cyber cell.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-ink-dim">
              Open the console to analyse a call, scan a note, or trace a fraud network — the same
              engine running behind every module on this page.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <Link
                to="/console"
                className="flex items-center gap-2 rounded-lg bg-signal px-6 py-3.5 text-sm font-medium text-white shadow-[0_0_0_1px_rgba(255,90,54,0.4),0_10px_28px_-8px_rgba(255,90,54,0.65)] transition-all hover:-translate-y-0.5 hover:bg-signal-soft"
              >
                Open Command Console <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="tel:1930" className="flex items-center gap-2 rounded-lg border border-void-line bg-void-soft px-6 py-3.5 text-sm font-medium text-ink transition-all hover:-translate-y-0.5 hover:border-ink-faint">
                Call 1930 · Cybercrime helpline
              </a>
            </div>
          </div>
        </Reveal>
      </section>

      <footer className="border-t border-void-line">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row sm:px-8">
          <div className="flex items-center gap-2.5">
            <svg width="20" height="20" viewBox="0 0 100 100">
              <polygon points="50,4 90,25 90,60 50,96 10,60 10,25" fill="none" stroke="#FF5A36" strokeWidth="6" />
              <circle cx="50" cy="45" r="9" fill="#FF5A36" />
            </svg>
            <span className="font-mono text-[11px] text-ink-faint">
              SafeNet AI · India's unified public safety intelligence platform
            </span>
          </div>
          <p className="font-mono text-[11px] text-ink-faint">Built for the ET AI Hackathon 2026</p>
        </div>
      </footer>
    </div>
  );
}
