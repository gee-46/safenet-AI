import { useCallback, useRef, useState } from "react";
import { UploadCloud, Banknote, RefreshCw, CheckCircle2, XCircle, HelpCircle, Image as ImageIcon } from "lucide-react";
import { Currency } from "../lib/api";
import { useApi, useAsyncAction } from "../lib/useApi";
import {
  PageHeader, Card, SectionLabel, Field, inputClass, Button, Badge,
  EmptyState, ErrorState, Skeleton, Reveal,
} from "../components/ui/Primitives";
import { ConfidenceGauge, Counter } from "../components/ui/Gauge";

const DENOMINATIONS = [100, 200, 500, 2000];
const VERDICTS = ["genuine", "counterfeit", "uncertain"];
const verdictTone = { genuine: "safe", counterfeit: "danger", uncertain: "gold" };
const verdictIcon = { genuine: CheckCircle2, counterfeit: XCircle, uncertain: HelpCircle };

function UploadForm({ onResult }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [denomination, setDenomination] = useState(500);
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const { act, loading, error } = useAsyncAction((fd) => Currency.verify(fd));

  const handleFile = useCallback((f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!file) return;
    const fd = new FormData();
    fd.append("image", file);
    fd.append("denomination", denomination);
    if (city) fd.append("city", city);
    if (state) fd.append("state", state);
    const res = await act(fd);
    onResult(res);
  };

  return (
    <Card className="p-5">
      <SectionLabel>Scan a currency note</SectionLabel>
      <form onSubmit={submit} className="space-y-4">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files?.[0]); }}
          onClick={() => inputRef.current?.click()}
          className={`flex min-h-[180px] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-6 text-center transition-colors ${
            dragging ? "border-verified bg-verified-dim/10" : "border-void-line bg-void-soft hover:border-ink-faint"
          }`}
        >
          <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
          {preview ? (
            <img src={preview} alt="Note preview" className="max-h-40 rounded-lg border border-void-line object-contain" />
          ) : (
            <>
              <UploadCloud className="h-7 w-7 text-ink-faint" />
              <p className="text-sm text-ink-dim">Drop a note photo or click to browse</p>
              <p className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">JPEG · PNG · WebP · max 10MB</p>
            </>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Denomination" required>
            <select className={inputClass} value={denomination} onChange={(e) => setDenomination(Number(e.target.value))}>
              {DENOMINATIONS.map((d) => <option key={d} value={d}>₹{d}</option>)}
            </select>
          </Field>
          <Field label="City" hint="optional">
            <input className={inputClass} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Bengaluru" />
          </Field>
          <Field label="State" hint="optional">
            <input className={inputClass} value={state} onChange={(e) => setState(e.target.value)} placeholder="Karnataka" />
          </Field>
        </div>

        {error && <p className="text-xs text-signal-soft">{error}</p>}

        <Button type="submit" loading={loading} disabled={!file} icon={Banknote} className="w-full sm:w-auto">
          Verify note
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
          icon={ImageIcon}
          title="Awaiting a note to scan"
          description="Upload a clear photo — watermark, security thread, microprint, and serial-number checks will appear here."
        />
      </Card>
    );
  }
  const tone = verdictTone[result.verdict] || "neutral";
  const Icon = verdictIcon[result.verdict] || HelpCircle;
  return (
    <Reveal>
      <Card className="p-5">
        <SectionLabel right={result.reported_to_rbi && <Badge tone="danger" dot>Flagged to RBI</Badge>}>Verdict</SectionLabel>
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
          <ConfidenceGauge value={result.confidence_score} tone={tone} size={112} sub={`${result.processing_time_ms}ms`} />
          <div className="flex-1 space-y-3 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <Badge tone={tone} dot><Icon className="h-3 w-3" /> {result.verdict}</Badge>
              <Badge tone="neutral">₹{result.denomination}</Badge>
              {result.serial_number_valid !== null && (
                <Badge tone={result.serial_number_valid ? "safe" : "danger"}>
                  serial {result.serial_number_valid ? "valid" : "invalid"}
                </Badge>
              )}
            </div>
            <p className="text-sm text-ink-dim">{result.recommendation}</p>
            {result.defects_detected?.length > 0 && (
              <div className="flex flex-wrap justify-center gap-1.5 sm:justify-start">
                {result.defects_detected.map((d) => (
                  <span key={d} className="rounded-md border border-signal-dim bg-signal-dim/20 px-2 py-1 font-mono text-[10px] text-signal-soft">
                    {d}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {result.security_checks && (
          <div className="mt-6 grid grid-cols-3 gap-4 border-t border-void-line pt-5">
            {Object.entries(result.security_checks).map(([k, v]) => (
              <div key={k} className="flex flex-col items-center">
                <ConfidenceGauge value={v} tone={v > 0.6 ? "safe" : v > 0.35 ? "gold" : "danger"} size={72} />
                <span className="mt-1 text-center font-mono text-[10px] uppercase tracking-wider text-ink-faint">{k.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </Reveal>
  );
}

function ReportsTable() {
  const [filters, setFilters] = useState({ verdict: "", denomination: "", state: "", days_back: 30, page: 1, page_size: 10 });
  const { data, loading, error, refetch } = useApi(() => Currency.reports(filters), [JSON.stringify(filters)]);
  const setF = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value, page: 1 }));

  return (
    <Card className="p-5">
      <SectionLabel right={<Button size="sm" variant="ghost" icon={RefreshCw} onClick={refetch}>Refresh</Button>}>
        Counterfeit reports
      </SectionLabel>
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <select className={inputClass} value={filters.verdict} onChange={setF("verdict")}>
          <option value="">All verdicts</option>
          {VERDICTS.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <select className={inputClass} value={filters.denomination} onChange={setF("denomination")}>
          <option value="">All denominations</option>
          {DENOMINATIONS.map((d) => <option key={d} value={d}>₹{d}</option>)}
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
        <EmptyState title="No reports match these filters" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-void-line text-[10px] uppercase tracking-wider text-ink-faint">
                <th className="pb-2 pr-4 font-medium">Note</th>
                <th className="pb-2 pr-4 font-medium">Verdict</th>
                <th className="pb-2 pr-4 font-medium">Confidence</th>
                <th className="pb-2 pr-4 font-medium">Location</th>
                <th className="pb-2 font-medium">Scanned</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.id} className="border-b border-void-line/60 last:border-0">
                  <td className="py-2.5 pr-4 font-mono text-xs text-ink">₹{r.denomination}</td>
                  <td className="py-2.5 pr-4"><Badge tone={verdictTone[r.verdict]}>{r.verdict}</Badge></td>
                  <td className="py-2.5 pr-4 font-mono tabular text-ink-dim">{Math.round(r.confidence_score * 100)}%</td>
                  <td className="py-2.5 pr-4 text-ink-dim">{[r.city, r.state].filter(Boolean).join(", ") || "—"}</td>
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
  const { data, loading } = useApi(() => Currency.stats(30), []);
  if (loading) return <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div>;
  if (!data) return null;
  return (
    <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
      {[
        { label: "Scanned · 30d", value: data.total_scanned },
        { label: "Confirmed counterfeit", value: data.confirmed_counterfeit },
        { label: "Detection rate", value: `${Math.round(data.detection_rate * 100)}%`, raw: true },
        { label: "Avg confidence", value: `${Math.round(data.avg_confidence * 100)}%`, raw: true },
      ].map((s) => (
        <Card key={s.label} className="p-4" hover={false}>
          <p className="font-display text-xl font-semibold text-ink">{s.raw ? s.value : <Counter value={s.value} />}</p>
          <p className="mt-0.5 text-[10px] uppercase tracking-wide text-ink-faint">{s.label}</p>
        </Card>
      ))}
    </div>
  );
}

export default function CounterfeitLens() {
  const [result, setResult] = useState(null);
  return (
    <div>
      <PageHeader
        eyebrow="Module 02 · Computer-vision note inspector"
        title="CounterfeitLens"
        description="Cross-checks watermark, security thread, microprint, colour-shift ink, and serial-number format against RBI note specifications for ₹100 / ₹200 / ₹500 / ₹2000."
        action={<Badge tone="gold" dot>₹100 · ₹200 · ₹500 · ₹2000</Badge>}
      />
      <StatsStrip />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <UploadForm onResult={setResult} />
        <ResultPanel result={result} />
      </div>
      <div className="mt-6">
        <ReportsTable />
      </div>
    </div>
  );
}
