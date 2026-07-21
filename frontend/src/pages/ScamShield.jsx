import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PhoneCall, ChevronDown, Send, ShieldCheck, ShieldAlert, RefreshCw, Radio } from "lucide-react";
import { Scam } from "../lib/api";
import { useApi, useAsyncAction } from "../lib/useApi";
import {
  PageHeader, Card, SectionLabel, Field, inputClass, Button, Badge,
  EmptyState, ErrorState, Skeleton, Reveal,
} from "../components/ui/Primitives";
import { ConfidenceGauge, Counter } from "../components/ui/Gauge";

const SCAM_TYPES = ["digital_arrest", "loan_fraud", "lottery", "kyc_update", "impersonation", "investment", "romance", "tech_support", "unknown"];
const STATUSES = ["pending", "confirmed", "false_positive", "escalated"];

const riskTone = { critical: "danger", high: "danger", medium: "gold", low: "safe" };
const statusTone = { confirmed: "danger", pending: "neutral", false_positive: "safe", escalated: "gold" };

function AnalyzerForm({ onResult }) {
  const [form, setForm] = useState({
    caller_number: "+919812345678",
    victim_number: "+919876500011",
    call_duration_seconds: 240,
    ring_pattern: "short-gap-long",
    silence_ratio: 0.18,
    speech_rate_wpm: 165,
    number_spoofing_detected: true,
    caller_location_reported: "Delhi Police HQ",
    transcript_snippet: "This is CBI. There is a case against your Aadhaar number. Do not disconnect the call or you will be arrested.",
    device_id: "",
  });
  const [advanced, setAdvanced] = useState(false);
  const { act, loading, error } = useAsyncAction((payload) => Scam.analyze(payload));

  const update = (k) => (e) => {
    const v = e?.target?.type === "checkbox" ? e.target.checked : e?.target?.value ?? e;
    setForm((f) => ({ ...f, [k]: v }));
  };

  const submit = async (e) => {
    e.preventDefault();
    const payload = {
      caller_number: form.caller_number,
      victim_number: form.victim_number,
      call_duration_seconds: form.call_duration_seconds ? Number(form.call_duration_seconds) : null,
      ring_pattern: form.ring_pattern || null,
      silence_ratio: form.silence_ratio !== "" ? Number(form.silence_ratio) : null,
      speech_rate_wpm: form.speech_rate_wpm !== "" ? Number(form.speech_rate_wpm) : null,
      number_spoofing_detected: !!form.number_spoofing_detected,
      caller_location_reported: form.caller_location_reported || null,
      transcript_snippet: form.transcript_snippet || null,
      device_id: form.device_id || null,
    };
    const res = await act(payload);
    onResult(res);
  };

  return (
    <Card className="p-5">
      <SectionLabel>Analyse call metadata</SectionLabel>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Caller number" required hint="E.164 format">
            <input required className={inputClass} value={form.caller_number} onChange={update("caller_number")} placeholder="+919812345678" />
          </Field>
          <Field label="Victim number" required>
            <input required className={inputClass} value={form.victim_number} onChange={update("victim_number")} placeholder="+919876500011" />
          </Field>
        </div>

        <Field label="Transcript snippet" hint={`${form.transcript_snippet.length}/500 · metadata only, never full audio`}>
          <textarea
            className={`${inputClass} min-h-[84px] resize-none`}
            maxLength={500}
            value={form.transcript_snippet}
            onChange={update("transcript_snippet")}
            placeholder="First few seconds of the call, if available…"
          />
        </Field>

        <button
          type="button"
          onClick={() => setAdvanced((v) => !v)}
          className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-ink-faint transition-colors hover:text-ink-dim"
        >
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${advanced ? "rotate-180" : ""}`} />
          Signal-flow features
        </button>

        <AnimatePresence>
          {advanced && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="grid grid-cols-2 gap-4 pt-1 sm:grid-cols-3">
                <Field label="Duration (sec)">
                  <input type="number" min="0" className={inputClass} value={form.call_duration_seconds} onChange={update("call_duration_seconds")} />
                </Field>
                <Field label="Ring pattern">
                  <input className={inputClass} value={form.ring_pattern} onChange={update("ring_pattern")} placeholder="short-gap-long" />
                </Field>
                <Field label="Speech rate (wpm)">
                  <input type="number" min="0" className={inputClass} value={form.speech_rate_wpm} onChange={update("speech_rate_wpm")} />
                </Field>
                <Field label="Silence ratio" hint="0–1">
                  <input type="number" step="0.01" min="0" max="1" className={inputClass} value={form.silence_ratio} onChange={update("silence_ratio")} />
                </Field>
                <Field label="Caller-reported location">
                  <input className={inputClass} value={form.caller_location_reported} onChange={update("caller_location_reported")} />
                </Field>
                <Field label="Device ID">
                  <input className={inputClass} value={form.device_id} onChange={update("device_id")} placeholder="optional" />
                </Field>
              </div>
              <label className="mt-4 flex items-center gap-2.5 text-sm text-ink-dim">
                <input type="checkbox" checked={form.number_spoofing_detected} onChange={update("number_spoofing_detected")} className="h-4 w-4 rounded border-void-line bg-void-soft accent-signal" />
                Number spoofing detected at carrier level
              </label>
            </motion.div>
          )}
        </AnimatePresence>

        {error && <p className="text-xs text-signal-soft">{error}</p>}

        <Button type="submit" loading={loading} icon={Send} className="w-full sm:w-auto">
          Run analysis
        </Button>
      </form>
    </Card>
  );
}

function ResultPanel({ result }) {
  if (!result) {
    return (
      <Card className="flex items-center justify-center p-5">
        <EmptyState
          icon={PhoneCall}
          title="Awaiting a call to analyse"
          description="Submit call metadata on the left — the verdict, confidence, and matched scam patterns will appear here in real time."
        />
      </Card>
    );
  }
  const tone = riskTone[result.risk_level] || "neutral";
  return (
    <Reveal>
      <Card className="p-5">
        <SectionLabel
          right={
            <Badge tone={result.alert_sent ? "safe" : "neutral"} dot>
              {result.alert_sent ? "Alert dispatched" : "No alert sent"}
            </Badge>
          }
        >
          Verdict
        </SectionLabel>
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
          <ConfidenceGauge value={result.confidence_score} tone={tone} size={112} sub={`${result.processing_time_ms}ms`} />
          <div className="flex-1 space-y-3 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              {result.is_scam ? (
                <Badge tone="danger" dot><ShieldAlert className="h-3 w-3" /> Scam detected</Badge>
              ) : (
                <Badge tone="safe" dot><ShieldCheck className="h-3 w-3" /> No scam pattern</Badge>
              )}
              <Badge tone={tone}>{result.risk_level} risk</Badge>
              <Badge tone="neutral" className="capitalize">{result.scam_type.replace(/_/g, " ")}</Badge>
            </div>
            <p className="text-sm text-ink-dim">{result.recommended_action}</p>
            {result.patterns_matched?.length > 0 && (
              <div className="flex flex-wrap justify-center gap-1.5 sm:justify-start">
                {result.patterns_matched.map((p) => (
                  <span key={p} className="rounded-md border border-void-line bg-void-soft px-2 py-1 font-mono text-[10px] text-ink-dim">
                    {p}
                  </span>
                ))}
              </div>
            )}
            <p className="font-mono text-[11px] text-ink-faint">Report ID · {result.report_id}</p>
          </div>
        </div>
      </Card>
    </Reveal>
  );
}

function ReportsTable() {
  const [filters, setFilters] = useState({ scam_type: "", state: "", status: "", days_back: 30, page: 1, page_size: 10 });
  const { data, loading, error, refetch } = useApi(() => Scam.reports(filters), [JSON.stringify(filters)]);
  const { act: updateStatus } = useAsyncAction((id, status) => Scam.updateStatus(id, status));

  const setF = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value, page: 1 }));

  return (
    <Card className="p-5">
      <SectionLabel right={<Button size="sm" variant="ghost" icon={RefreshCw} onClick={refetch}>Refresh</Button>}>
        Scam reports
      </SectionLabel>
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <select className={inputClass} value={filters.scam_type} onChange={setF("scam_type")}>
          <option value="">All types</option>
          {SCAM_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <select className={inputClass} value={filters.status} onChange={setF("status")}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
        <input className={inputClass} placeholder="State" value={filters.state} onChange={setF("state")} />
        <select className={inputClass} value={filters.days_back} onChange={setF("days_back")}>
          {[7, 30, 90, 365].map((d) => <option key={d} value={d}>{d}d window</option>)}
        </select>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : loading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
      ) : !data?.length ? (
        <EmptyState title="No reports match these filters" description="Try widening the date range or clearing a filter." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-void-line text-[10px] uppercase tracking-wider text-ink-faint">
                <th className="pb-2 pr-4 font-medium">Caller</th>
                <th className="pb-2 pr-4 font-medium">Type</th>
                <th className="pb-2 pr-4 font-medium">Confidence</th>
                <th className="pb-2 pr-4 font-medium">Location</th>
                <th className="pb-2 pr-4 font-medium">Status</th>
                <th className="pb-2 font-medium">Reported</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.id} className="border-b border-void-line/60 last:border-0">
                  <td className="py-2.5 pr-4 font-mono text-xs text-ink">{r.caller_number}</td>
                  <td className="py-2.5 pr-4 capitalize text-ink-dim">{r.scam_type.replace(/_/g, " ")}</td>
                  <td className="py-2.5 pr-4 font-mono tabular text-ink-dim">{Math.round(r.confidence_score * 100)}%</td>
                  <td className="py-2.5 pr-4 text-ink-dim">{[r.city, r.state].filter(Boolean).join(", ") || "—"}</td>
                  <td className="py-2.5 pr-4">
                    <select
                      value={r.status}
                      onChange={async (e) => {
                        await updateStatus(r.id, e.target.value);
                        refetch();
                      }}
                      className={`rounded-md border px-2 py-1 font-mono text-[10px] uppercase tracking-wider bg-void-soft ${
                        statusTone[r.status] ? "" : ""
                      } border-void-line text-ink-dim`}
                    >
                      {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                    </select>
                  </td>
                  <td className="py-2.5 font-mono text-[11px] text-ink-faint">
                    {new Date(r.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between">
        <span className="font-mono text-[11px] text-ink-faint">Page {filters.page}</span>
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" disabled={filters.page === 1} onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}>Prev</Button>
          <Button size="sm" variant="ghost" disabled={(data?.length || 0) < filters.page_size} onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}>Next</Button>
        </div>
      </div>
    </Card>
  );
}

function StatsStrip() {
  const { data, loading } = useApi(() => Scam.stats(30), []);
  if (loading) return <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div>;
  if (!data) return null;
  return (
    <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
      {[
        { label: "Analysed · 30d", value: data.total_analyzed },
        { label: "Confirmed scams", value: data.confirmed_scams },
        { label: "Detection rate", value: `${Math.round(data.detection_rate * 100)}%`, raw: true },
        { label: "Avg confidence", value: `${Math.round(data.avg_confidence * 100)}%`, raw: true },
      ].map((s) => (
        <Card key={s.label} className="p-4" hover={false}>
          <p className="font-display text-xl font-semibold text-ink">
            {s.raw ? s.value : <Counter value={s.value} />}
          </p>
          <p className="mt-0.5 text-[10px] uppercase tracking-wide text-ink-faint">{s.label}</p>
        </Card>
      ))}
    </div>
  );
}

export default function ScamShield() {
  const [result, setResult] = useState(null);
  return (
    <div>
      <PageHeader
        eyebrow="Module 01 · Real-time metadata classifier"
        title="ScamShield"
        description="Classifies live call metadata — never raw audio — against known digital-arrest, KYC, loan, lottery, and impersonation scripts, then dispatches a victim alert automatically above your confidence threshold."
        action={<Badge tone="safe" dot><Radio className="h-3 w-3" /> Privacy-by-design</Badge>}
      />
      <StatsStrip />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <AnalyzerForm onResult={setResult} />
        <ResultPanel result={result} />
      </div>
      <div className="mt-6">
        <ReportsTable />
      </div>
    </div>
  );
}
