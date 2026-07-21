import { useState } from "react";
import { FileText, Download, ScrollText, RefreshCw, Gavel } from "lucide-react";
import { Evidence as EvidenceApi } from "../lib/api";
import { useApi, useAsyncAction } from "../lib/useApi";
import {
  PageHeader, Card, SectionLabel, Field, inputClass, Button, Badge,
  EmptyState, ErrorState, Skeleton, Reveal,
} from "../components/ui/Primitives";

function GenerateForm() {
  const [caseId, setCaseId] = useState("");
  const [reportIds, setReportIds] = useState("");
  const [includeGraph, setIncludeGraph] = useState(true);
  const [includeTimeline, setIncludeTimeline] = useState(true);
  const [includeRegulatory, setIncludeRegulatory] = useState(true);
  const { act, loading, error, data: result } = useAsyncAction((p) => EvidenceApi.generate(p));

  const submit = async (e) => {
    e.preventDefault();
    await act({
      case_id: caseId || null,
      scam_report_ids: reportIds ? reportIds.split(",").map((s) => s.trim()).filter(Boolean) : null,
      include_graph: includeGraph,
      include_timeline: includeTimeline,
      include_regulatory_sections: includeRegulatory,
    });
  };

  return (
    <Card className="p-5">
      <SectionLabel>Generate evidence package</SectionLabel>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Case ID" hint="optional, UUID">
          <input className={inputClass} value={caseId} onChange={(e) => setCaseId(e.target.value)} placeholder="Leave blank to build from report IDs" />
        </Field>
        <Field label="Scam report IDs" hint="optional, comma-separated UUIDs">
          <input className={inputClass} value={reportIds} onChange={(e) => setReportIds(e.target.value)} placeholder="id-1, id-2, id-3" />
        </Field>
        <div className="flex flex-wrap gap-5">
          {[
            ["Include fraud graph", includeGraph, setIncludeGraph],
            ["Include timeline", includeTimeline, setIncludeTimeline],
            ["Include CrPC / IT Act sections", includeRegulatory, setIncludeRegulatory],
          ].map(([label, val, set]) => (
            <label key={label} className="flex items-center gap-2 text-sm text-ink-dim">
              <input type="checkbox" checked={val} onChange={(e) => set(e.target.checked)} className="h-4 w-4 rounded border-void-line bg-void-soft accent-signal" />
              {label}
            </label>
          ))}
        </div>
        {error && <p className="text-xs text-signal-soft">{error}</p>}
        <Button type="submit" loading={loading} icon={FileText}>Generate PDF package</Button>
      </form>

      {result && (
        <Reveal>
          <div className="mt-5 rounded-xl border border-verified-dim bg-verified-dim/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-wider text-verified-soft">{result.case_number}</p>
                <p className="text-sm text-ink">{result.pages} pages · generated {new Date(result.generated_at).toLocaleString("en-IN")}</p>
              </div>
              <a href={EvidenceApi.downloadUrl(result.package_id)} target="_blank" rel="noreferrer">
                <Button variant="verified" size="sm" icon={Download}>Download PDF</Button>
              </a>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <p className="eyebrow mb-1.5 flex items-center gap-1.5"><Gavel className="h-3 w-3" /> CrPC sections</p>
                <div className="flex flex-wrap gap-1.5">{result.crpc_sections.map((s) => <Badge key={s} tone="neutral">{s}</Badge>)}</div>
              </div>
              <div>
                <p className="eyebrow mb-1.5 flex items-center gap-1.5"><Gavel className="h-3 w-3" /> IT Act sections</p>
                <div className="flex flex-wrap gap-1.5">{result.it_act_sections.map((s) => <Badge key={s} tone="neutral">{s}</Badge>)}</div>
              </div>
            </div>
          </div>
        </Reveal>
      )}
    </Card>
  );
}

function AuditTrail() {
  const [filters, setFilters] = useState({ action: "", entity_type: "", entity_id: "", days_back: 7, page: 1, page_size: 15 });
  const { data, loading, error, refetch } = useApi(() => EvidenceApi.auditTrail(filters), [JSON.stringify(filters)]);
  const setF = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value, page: 1 }));

  return (
    <Card className="p-5">
      <SectionLabel right={<Button size="sm" variant="ghost" icon={RefreshCw} onClick={refetch}>Refresh</Button>}>
        <ScrollText className="mr-1.5 inline h-3.5 w-3.5" /> AI decision audit trail
      </SectionLabel>
      <p className="mb-4 text-xs text-ink-faint">Every automated verdict is logged with model, confidence, and latency for legal admissibility.</p>
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <input className={inputClass} placeholder="Action" value={filters.action} onChange={setF("action")} />
        <input className={inputClass} placeholder="Entity type" value={filters.entity_type} onChange={setF("entity_type")} />
        <input className={inputClass} placeholder="Entity ID" value={filters.entity_id} onChange={setF("entity_id")} />
        <select className={inputClass} value={filters.days_back} onChange={setF("days_back")}>
          {[1, 7, 30, 90].map((d) => <option key={d} value={d}>{d}d window</option>)}
        </select>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : loading ? (
        <div className="space-y-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}</div>
      ) : !data?.logs?.length ? (
        <EmptyState title="No audit entries in this window" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-void-line text-[10px] uppercase tracking-wider text-ink-faint">
                <th className="pb-2 pr-4 font-medium">Time</th>
                <th className="pb-2 pr-4 font-medium">Action</th>
                <th className="pb-2 pr-4 font-medium">Model</th>
                <th className="pb-2 pr-4 font-medium">Confidence</th>
                <th className="pb-2 font-medium">Latency</th>
              </tr>
            </thead>
            <tbody>
              {data.logs.map((l) => (
                <tr key={l.id} className="border-b border-void-line/60 last:border-0">
                  <td className="py-2 pr-4 font-mono text-ink-faint">{new Date(l.timestamp).toLocaleString("en-IN", { hour12: false })}</td>
                  <td className="py-2 pr-4 text-ink-dim">{l.action}</td>
                  <td className="py-2 pr-4 font-mono text-ink-dim">{l.model_name ? `${l.model_name} v${l.model_version}` : "—"}</td>
                  <td className="py-2 pr-4 font-mono tabular text-ink-dim">{l.confidence != null ? `${Math.round(l.confidence * 100)}%` : "—"}</td>
                  <td className="py-2 font-mono tabular text-ink-faint">{l.latency_ms != null ? `${l.latency_ms}ms` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export default function Evidence() {
  return (
    <div>
      <PageHeader
        eyebrow="Module 06 · Court-admissible documentation"
        title="Evidence Vault"
        description="Bundles incident timelines, fraud-network summaries, and applicable CrPC / IT Act citations into a PDF suitable for filing alongside an FIR."
      />
      <div className="space-y-6">
        <GenerateForm />
        <AuditTrail />
      </div>
    </div>
  );
}
