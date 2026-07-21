import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { ShieldAlert, Banknote, Network, BellRing, TrendingUp, Gauge as GaugeIcon, Timer } from "lucide-react";
import { Analytics } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, SectionLabel, Skeleton, ErrorState, Reveal, Badge } from "../components/ui/Primitives";
import { Counter, ConfidenceGauge } from "../components/ui/Gauge";

const METRICS = [
  { key: "scam_detections", label: "Scam calls" },
  { key: "counterfeit", label: "Counterfeit notes" },
  { key: "alerts", label: "Alerts sent" },
];

function RadarHero({ loading }) {
  return (
    <Card className="mb-8 overflow-hidden p-0" hover={false}>
      <div className="relative flex flex-col items-center gap-8 border-b border-void-line px-6 py-10 hex-backdrop sm:flex-row sm:justify-between sm:px-10">
        <div className="relative z-10 max-w-xl">
          <div className="eyebrow mb-3 flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${loading ? "bg-ink-faint" : "bg-verified animate-pulse"}`} />
            Live intelligence sweep
          </div>
          <h1 className="font-display text-3xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-[2.6rem]">
            One console for scam calls,<br className="hidden sm:block" /> fake notes, and fraud networks.
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-dim">
            SafeNet AI fuses call-metadata classification, currency computer vision, and graph
            intelligence into a single command view for citizens and cyber cells alike.
          </p>
        </div>
        <div className="relative z-10 flex h-40 w-40 items-center justify-center sm:h-48 sm:w-48">
          <div className="absolute inset-0 rounded-full border border-void-line" />
          <div className="absolute inset-6 rounded-full border border-void-line" />
          <div className="absolute inset-12 rounded-full border border-void-line" />
          <div
            className="absolute inset-0 origin-center animate-radar rounded-full"
            style={{
              background: "conic-gradient(from 0deg, rgba(255,90,54,0.5), transparent 40%)",
            }}
          />
          <span className="absolute left-[30%] top-[38%] h-1.5 w-1.5 rounded-full bg-signal shadow-[0_0_10px_2px_rgba(255,90,54,0.7)]" />
          <span className="absolute left-[62%] top-[58%] h-1 w-1 rounded-full bg-verified shadow-[0_0_8px_2px_rgba(47,217,196,0.7)]" />
          <span className="absolute left-[70%] top-[30%] h-1 w-1 rounded-full bg-gold shadow-[0_0_8px_2px_rgba(201,162,39,0.7)]" />
          <ShieldAlert className="relative h-9 w-9 text-ink" strokeWidth={1.5} />
        </div>
      </div>
    </Card>
  );
}

function StatCard({ icon: Icon, label, value, decimals = 0, prefix = "", suffix = "", tone = "neutral", delay = 0 }) {
  const toneMap = {
    neutral: "text-ink",
    danger: "text-signal-soft",
    safe: "text-verified-soft",
    gold: "text-gold-soft",
  };
  return (
    <Reveal delay={delay}>
      <Card className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-void-line bg-void-soft text-ink-dim">
            <Icon className="h-4 w-4" />
          </span>
        </div>
        <p className={`font-display text-2xl font-semibold sm:text-3xl ${toneMap[tone]}`}>
          <Counter value={value} decimals={decimals} prefix={prefix} suffix={suffix} />
        </p>
        <p className="mt-1 text-xs uppercase tracking-wide text-ink-faint">{label}</p>
      </Card>
    </Reveal>
  );
}

export default function Dashboard() {
  const [metric, setMetric] = useState("scam_detections");
  const { data: stats, loading: statsLoading, error: statsError, refetch } = useApi(
    () => Analytics.dashboard(30),
    []
  );
  const { data: trend, loading: trendLoading } = useApi(
    () => Analytics.trends({ days_back: 30, metric }),
    [metric]
  );
  const { data: perf, loading: perfLoading } = useApi(() => Analytics.modelPerformance(7), []);

  return (
    <div>
      <RadarHero loading={statsLoading} />

      {statsError ? (
        <ErrorState message={statsError} onRetry={refetch} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            <StatCard icon={ShieldAlert} label="Scam calls · 30d" value={stats?.total_scam_detections_30d ?? 0} tone="danger" delay={0} />
            <StatCard icon={Banknote} label="Counterfeit notes · 30d" value={stats?.total_counterfeit_reports_30d ?? 0} tone="gold" delay={0.05} />
            <StatCard icon={Network} label="Active fraud cases" value={stats?.active_fraud_cases ?? 0} tone="neutral" delay={0.1} />
            <StatCard icon={BellRing} label="Alerts sent · 30d" value={stats?.alerts_sent_30d ?? 0} tone="safe" delay={0.15} />
            <StatCard
              icon={TrendingUp}
              label="Est. loss prevented"
              value={stats?.estimated_loss_prevented_inr ?? 0}
              prefix="₹"
              tone="gold"
              delay={0.2}
            />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="p-5 lg:col-span-2">
              <SectionLabel
                right={
                  <div className="flex gap-1 rounded-lg border border-void-line bg-void-soft p-1">
                    {METRICS.map((m) => (
                      <button
                        key={m.key}
                        onClick={() => setMetric(m.key)}
                        className={`rounded-md px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider transition-colors ${
                          metric === m.key ? "bg-void-raised text-ink" : "text-ink-faint hover:text-ink-dim"
                        }`}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                }
              >
                30-day trend
              </SectionLabel>
              {trendLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={trend?.data || []} margin={{ left: -18, right: 8 }}>
                    <defs>
                      <linearGradient id="fillMetric" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#FF5A36" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#FF5A36" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1A2130" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#5C6680", fontSize: 10, fontFamily: "IBM Plex Mono" }}
                      tickLine={false}
                      axisLine={{ stroke: "#232B3D" }}
                      tickFormatter={(d) => d?.slice(5)}
                      minTickGap={24}
                    />
                    <YAxis
                      tick={{ fill: "#5C6680", fontSize: 10, fontFamily: "IBM Plex Mono" }}
                      tickLine={false}
                      axisLine={false}
                      width={30}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#141924",
                        border: "1px solid #232B3D",
                        borderRadius: 8,
                        fontSize: 12,
                        fontFamily: "IBM Plex Mono",
                      }}
                      labelStyle={{ color: "#9AA4BC" }}
                    />
                    <Area type="monotone" dataKey="count" stroke="#FF5A36" strokeWidth={2} fill="url(#fillMetric)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card className="p-5">
              <SectionLabel>Top scam types · 30d</SectionLabel>
              <div className="space-y-3">
                {statsLoading ? (
                  Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-6 w-full" />)
                ) : stats?.top_scam_types?.length ? (
                  stats.top_scam_types.map((t, i) => {
                    const max = stats.top_scam_types[0].count || 1;
                    return (
                      <div key={t.type}>
                        <div className="mb-1 flex items-center justify-between text-xs">
                          <span className="capitalize text-ink-dim">{t.type.replace(/_/g, " ")}</span>
                          <span className="font-mono tabular text-ink-faint">{t.count}</span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-void-soft">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-signal-dim to-signal"
                            style={{ width: `${(t.count / max) * 100}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-xs text-ink-faint">No scam reports in this window yet.</p>
                )}
              </div>
            </Card>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="p-5 lg:col-span-2">
              <SectionLabel>States by incident volume · 30d</SectionLabel>
              {statsLoading ? (
                <Skeleton className="h-40 w-full" />
              ) : stats?.top_states?.length ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {stats.top_states.map((s) => (
                    <div key={s.state} className="rounded-lg border border-void-line bg-void-soft p-3">
                      <p className="truncate text-xs text-ink-dim">{s.state}</p>
                      <p className="mt-1 font-mono text-lg font-semibold text-ink">{s.count}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-ink-faint">No state-tagged reports yet.</p>
              )}
            </Card>

            <Card className="p-5">
              <SectionLabel>Detection accuracy</SectionLabel>
              <div className="flex items-center justify-center py-2">
                <ConfidenceGauge
                  value={stats?.detection_accuracy ?? 0}
                  tone="safe"
                  size={120}
                  sub={`${Math.round(stats?.avg_detection_latency_ms ?? 0)} ms avg latency`}
                />
              </div>
            </Card>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Card className="p-5">
              <SectionLabel right={<Badge tone="danger">Scam classifier</Badge>}>Model performance · 7d</SectionLabel>
              {perfLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <MetricTile icon={GaugeIcon} label="Inferences" value={perf?.scam_classifier?.total_inferences ?? 0} />
                  <MetricTile icon={TrendingUp} label="Avg confidence" value={`${Math.round((perf?.scam_classifier?.avg_confidence ?? 0) * 100)}%`} />
                  <MetricTile icon={Timer} label="Avg latency" value={`${Math.round(perf?.scam_classifier?.avg_latency_ms ?? 0)}ms`} />
                  <MetricTile icon={ShieldAlert} label="False-positive rate" value={`${Math.round((perf?.scam_classifier?.false_positive_rate ?? 0) * 100)}%`} />
                </div>
              )}
            </Card>
            <Card className="p-5">
              <SectionLabel right={<Badge tone="gold">Counterfeit detector</Badge>}>Model performance · 7d</SectionLabel>
              {perfLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : (
                <div className="grid grid-cols-3 gap-4">
                  <MetricTile icon={GaugeIcon} label="Inferences" value={perf?.counterfeit_detector?.total_inferences ?? 0} />
                  <MetricTile icon={TrendingUp} label="Avg confidence" value={`${Math.round((perf?.counterfeit_detector?.avg_confidence ?? 0) * 100)}%`} />
                  <MetricTile icon={Timer} label="Avg latency" value={`${Math.round(perf?.counterfeit_detector?.avg_latency_ms ?? 0)}ms`} />
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function MetricTile({ icon: Icon, label, value }) {
  return (
    <div>
      <Icon className="mb-2 h-3.5 w-3.5 text-ink-faint" />
      <p className="font-mono text-lg font-semibold tabular text-ink">{value}</p>
      <p className="text-[10px] uppercase tracking-wide text-ink-faint">{label}</p>
    </div>
  );
}
