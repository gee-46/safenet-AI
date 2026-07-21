import { useState } from "react";
import { MessageSquareWarning, Send, Phone, Globe2, ExternalLink, ShieldQuestion } from "lucide-react";
import { Citizen } from "../lib/api";
import { useApi, useAsyncAction } from "../lib/useApi";
import {
  PageHeader, Card, SectionLabel, Field, inputClass, Button, Badge,
  EmptyState, ErrorState, Skeleton, Reveal,
} from "../components/ui/Primitives";
import { ConfidenceGauge } from "../components/ui/Gauge";

const LANGUAGES = [
  ["en", "English"], ["hi", "हिन्दी"], ["ta", "தமிழ்"], ["te", "తెలుగు"], ["kn", "ಕನ್ನಡ"],
  ["ml", "മലയാളം"], ["mr", "मराठी"], ["gu", "ગુજરાતી"], ["bn", "বাংলা"], ["pa", "ਪੰਜਾਬੀ"], ["or", "ଓଡ଼ିଆ"], ["as", "অসমীয়া"],
];
const CONTEXTS = ["call", "sms", "payment", "job_offer", "other"];
const riskTone = { scam: "danger", high_risk: "danger", suspicious: "gold", safe: "safe" };

function AssessPanel({ onResult }) {
  const [message, setMessage] = useState("Someone called claiming to be from CBI, said there's a case against my Aadhaar, and asked me to stay on video call and not tell anyone or I'll be arrested.");
  const [phone, setPhone] = useState("");
  const [language, setLanguage] = useState("en");
  const [contextType, setContextType] = useState("call");
  const { act, loading, error } = useAsyncAction((p) => Citizen.assess(p));

  const submit = async (e) => {
    e.preventDefault();
    const res = await act({ message, phone_number: phone || null, language, context_type: contextType });
    onResult(res);
  };

  return (
    <Card className="p-5">
      <SectionLabel>Describe the situation</SectionLabel>
      <form onSubmit={submit} className="space-y-4">
        <Field label="What happened?" required hint={`${message.length}/2000`}>
          <textarea
            required
            maxLength={2000}
            className={`${inputClass} min-h-[120px] resize-none`}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe the call, message, or offer in your own words…"
          />
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Context">
            <select className={inputClass} value={contextType} onChange={(e) => setContextType(e.target.value)}>
              {CONTEXTS.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
            </select>
          </Field>
          <Field label="Language">
            <select className={inputClass} value={language} onChange={(e) => setLanguage(e.target.value)}>
              {LANGUAGES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </select>
          </Field>
          <Field label="Phone number" hint="optional">
            <input className={inputClass} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91…" />
          </Field>
        </div>
        {error && <p className="text-xs text-signal-soft">{error}</p>}
        <Button type="submit" loading={loading} icon={Send}>Assess my risk</Button>
      </form>
    </Card>
  );
}

function ResultCard({ result }) {
  if (!result) {
    return (
      <Card className="flex items-center justify-center p-5">
        <EmptyState
          icon={MessageSquareWarning}
          title="No assessment yet"
          description="Your risk verdict, plain-language explanation, and next steps will appear here — in the language you chose."
        />
      </Card>
    );
  }
  const tone = riskTone[result.risk_level] || "neutral";
  return (
    <Reveal>
      <Card className="p-5">
        <SectionLabel right={<Badge tone="neutral"><Globe2 className="h-3 w-3" /> {result.response_language}</Badge>}>Assessment</SectionLabel>
        <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
          <ConfidenceGauge value={result.confidence} tone={tone} size={104} />
          <div className="flex-1 space-y-3 text-center sm:text-left">
            <Badge tone={tone} dot className="capitalize">{result.risk_level.replace(/_/g, " ")}</Badge>
            <p className="text-sm leading-relaxed text-ink-dim">{result.explanation}</p>
          </div>
        </div>
        {result.recommended_actions?.length > 0 && (
          <ul className="mt-5 space-y-2 border-t border-void-line pt-4">
            {result.recommended_actions.map((a, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-ink-dim">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-signal" />
                {a}
              </li>
            ))}
          </ul>
        )}
        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-void-line pt-4">
          <a href={`tel:${result.helpline_number}`} className="flex items-center gap-2 rounded-lg border border-signal-dim bg-signal-dim/15 px-3 py-2 text-sm text-signal-soft">
            <Phone className="h-4 w-4" /> Call {result.helpline_number}
          </a>
          {result.report_url && (
            <a href={result.report_url} target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-lg border border-void-line bg-void-soft px-3 py-2 text-sm text-ink-dim">
              <ExternalLink className="h-4 w-4" /> File a report
            </a>
          )}
        </div>
      </Card>
    </Reveal>
  );
}

function ScamTypeLibrary() {
  const { data, loading, error, refetch } = useApi(() => Citizen.scamTypes(), []);
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  return (
    <Card className="p-5">
      <SectionLabel right={<ShieldQuestion className="h-4 w-4 text-ink-faint" />}>Know the scripts</SectionLabel>
      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}</div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {data?.scam_types?.map((s) => (
            <div key={s.type} className="rounded-xl border border-void-line bg-void-soft p-4">
              <p className="font-display text-sm font-semibold text-ink">{s.name}</p>
              <p className="mt-1 text-xs leading-relaxed text-ink-dim">{s.description}</p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {s.red_flags.slice(0, 3).map((f) => (
                  <span key={f} className="rounded-md border border-signal-dim bg-signal-dim/10 px-2 py-0.5 font-mono text-[10px] text-signal-soft">{f}</span>
                ))}
              </div>
              <p className="mt-2.5 text-xs text-verified-soft">→ {s.what_to_do}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function Helplines() {
  const { data, loading, error, refetch } = useApi(() => Citizen.helplines(), []);
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  return (
    <Card className="p-5">
      <SectionLabel>Helplines &amp; portals</SectionLabel>
      {loading ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            {data?.helplines?.map((h) => (
              <a key={h.number} href={`tel:${h.number}`} className="flex items-center justify-between rounded-lg border border-void-line bg-void-soft px-3 py-2.5 hover:border-ink-faint">
                <span className="text-xs text-ink-dim">{h.name}</span>
                <span className="font-mono text-sm font-semibold text-ink">{h.number}</span>
              </a>
            ))}
          </div>
          <div className="space-y-2">
            {data?.portals?.map((p) => (
              <a key={p.url} href={p.url} target="_blank" rel="noreferrer" className="flex items-center justify-between rounded-lg border border-void-line bg-void-soft px-3 py-2.5 hover:border-ink-faint">
                <span className="text-xs text-ink-dim">{p.name}</span>
                <ExternalLink className="h-3.5 w-3.5 text-ink-faint" />
              </a>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export default function CitizenShield() {
  const [result, setResult] = useState(null);
  return (
    <div>
      <PageHeader
        eyebrow="Module 05 · Multilingual public advisor"
        title="CitizenShield"
        description="Describe a suspicious call, SMS, or offer in your own language and get a plain verdict with next steps — the same engine that powers the WhatsApp advisor."
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <AssessPanel onResult={setResult} />
        <ResultCard result={result} />
      </div>
      <div className="mt-6 space-y-6">
        <ScamTypeLibrary />
        <Helplines />
      </div>
    </div>
  );
}
