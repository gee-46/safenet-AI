import { useState } from "react";
import { Search, Share2, Link2, FolderPlus, RefreshCw, X } from "lucide-react";
import { Fraud } from "../lib/api";
import { useApi, useAsyncAction } from "../lib/useApi";
import {
  PageHeader, Card, SectionLabel, Field, inputClass, Button, Badge,
  EmptyState, ErrorState, Skeleton, Reveal,
} from "../components/ui/Primitives";
import { ConfidenceGauge } from "../components/ui/Gauge";
import { ForceGraph, GraphLegend } from "../components/graph/ForceGraph";

const ENTITY_TYPES = ["phone_number", "bank_account", "device", "ip_address", "person", "organisation"];
const RELATIONSHIPS = ["CALLED", "TRANSFERRED_TO", "SHARED_DEVICE", "MULE_LINK"];
const SEVERITIES = ["low", "medium", "high", "critical"];
const severityTone = { low: "safe", medium: "gold", high: "danger", critical: "danger" };

function GraphQuery() {
  const [entityId, setEntityId] = useState("+919812345678");
  const [entityType, setEntityType] = useState("phone_number");
  const [depth, setDepth] = useState(2);
  const [maxNodes, setMaxNodes] = useState(50);
  const [selectedNode, setSelectedNode] = useState(null);
  const { act, loading, error, data: result } = useAsyncAction((payload) => Fraud.queryGraph(payload));

  const submit = async (e) => {
    e.preventDefault();
    setSelectedNode(null);
    await act({ entity_id: entityId, entity_type: entityType, depth: Number(depth), max_nodes: Number(maxNodes) });
  };

  return (
    <Card className="p-5">
      <SectionLabel>Trace a fraud network</SectionLabel>
      <form onSubmit={submit} className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-5">
        <div className="sm:col-span-2">
          <Field label="Entity ID" required hint="phone, account, device…">
            <input required className={inputClass} value={entityId} onChange={(e) => setEntityId(e.target.value)} />
          </Field>
        </div>
        <Field label="Type">
          <select className={inputClass} value={entityType} onChange={(e) => setEntityType(e.target.value)}>
            {ENTITY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </Field>
        <Field label="Depth" hint={`${depth} hop${depth > 1 ? "s" : ""}`}>
          <input type="range" min="1" max="4" value={depth} onChange={(e) => setDepth(e.target.value)} className="mt-3 w-full accent-signal" />
        </Field>
        <Field label="Max nodes" hint={`${maxNodes}`}>
          <input type="range" min="5" max="200" step="5" value={maxNodes} onChange={(e) => setMaxNodes(e.target.value)} className="mt-3 w-full accent-signal" />
        </Field>
        <div className="sm:col-span-5">
          <Button type="submit" loading={loading} icon={Search}>Query network</Button>
        </div>
      </form>

      {error && <ErrorState message={error} />}

      {result && (
        <Reveal>
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ForceGraph nodes={result.nodes} edges={result.edges} seedId={result.entity_id} onNodeClick={setSelectedNode} />
              <div className="mt-3 flex items-center justify-between">
                <GraphLegend />
                {selectedNode && (
                  <button onClick={() => setSelectedNode(null)} className="flex items-center gap-1 font-mono text-[10px] uppercase text-ink-faint hover:text-ink-dim">
                    <X className="h-3 w-3" /> clear selection
                  </button>
                )}
              </div>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-center rounded-xl border border-void-line bg-void-soft py-5">
                <ConfidenceGauge
                  value={result.risk_score}
                  tone={result.risk_score > 0.65 ? "danger" : result.risk_score > 0.35 ? "gold" : "safe"}
                  size={104}
                  label="Network risk"
                  sub={`${result.fraud_network_size} linked entities`}
                />
              </div>
              <div className="rounded-xl border border-void-line bg-void-soft p-4">
                <p className="eyebrow mb-2">Recommended action</p>
                <p className="text-sm text-ink-dim">{result.recommended_action}</p>
              </div>
              {result.states_involved?.length > 0 && (
                <div className="rounded-xl border border-void-line bg-void-soft p-4">
                  <p className="eyebrow mb-2">States involved</p>
                  <div className="flex flex-wrap gap-1.5">
                    {result.states_involved.map((s) => <Badge key={s} tone="neutral">{s}</Badge>)}
                  </div>
                </div>
              )}
              {selectedNode && (
                <div className="rounded-xl border border-signal-dim bg-signal-dim/10 p-4">
                  <p className="eyebrow mb-2 text-signal-soft">Selected node</p>
                  <p className="font-mono text-sm text-ink">{selectedNode.label}</p>
                  <p className="mt-1 text-xs text-ink-faint capitalize">{selectedNode.type.replace(/_/g, " ")}</p>
                  <div className="mt-2 flex gap-2">
                    <Badge tone="danger">risk {Math.round((selectedNode.risk_score || 0) * 100)}%</Badge>
                    <Badge tone="neutral">{selectedNode.fraud_count} incidents</Badge>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Reveal>
      )}
    </Card>
  );
}

function AdminActions() {
  const [tab, setTab] = useState("register");
  const reg = useAsyncAction((p) => Fraud.register(p));
  const link = useAsyncAction((p) => Fraud.link(p));

  const [regForm, setRegForm] = useState({ entity_id: "", entity_type: "phone_number", scam_type: "unknown", confidence: 0.8, state: "" });
  const [linkForm, setLinkForm] = useState({ source_id: "", source_type: "phone_number", target_id: "", target_type: "bank_account", relationship: "TRANSFERRED_TO", amount_inr: "" });

  return (
    <Card className="p-5">
      <SectionLabel>Analyst actions</SectionLabel>
      <div className="mb-4 flex gap-1 rounded-lg border border-void-line bg-void-soft p-1 w-fit">
        <button onClick={() => setTab("register")} className={`rounded-md px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider ${tab === "register" ? "bg-void-raised text-ink" : "text-ink-faint"}`}>Register entity</button>
        <button onClick={() => setTab("link")} className={`rounded-md px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider ${tab === "link" ? "bg-void-raised text-ink" : "text-ink-faint"}`}>Link entities</button>
      </div>

      {tab === "register" ? (
        <form
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
          onSubmit={async (e) => { e.preventDefault(); await reg.act({ ...regForm, confidence: Number(regForm.confidence) }); }}
        >
          <Field label="Entity ID" required><input required className={inputClass} value={regForm.entity_id} onChange={(e) => setRegForm((f) => ({ ...f, entity_id: e.target.value }))} /></Field>
          <Field label="Type"><select className={inputClass} value={regForm.entity_type} onChange={(e) => setRegForm((f) => ({ ...f, entity_type: e.target.value }))}>{ENTITY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}</select></Field>
          <Field label="Confidence" hint={regForm.confidence}><input type="range" min="0" max="1" step="0.01" value={regForm.confidence} onChange={(e) => setRegForm((f) => ({ ...f, confidence: e.target.value }))} className="mt-3 w-full accent-signal" /></Field>
          <Field label="State" hint="optional"><input className={inputClass} value={regForm.state} onChange={(e) => setRegForm((f) => ({ ...f, state: e.target.value }))} /></Field>
          <div className="sm:col-span-2 flex items-center gap-3">
            <Button type="submit" loading={reg.loading} icon={Share2} size="sm">Register into graph</Button>
            {reg.data?.registered && <Badge tone="safe" dot>Linked into fraud network</Badge>}
          </div>
        </form>
      ) : (
        <form
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
          onSubmit={async (e) => { e.preventDefault(); await link.act({ ...linkForm, amount_inr: linkForm.amount_inr || undefined }); }}
        >
          <Field label="Source ID" required><input required className={inputClass} value={linkForm.source_id} onChange={(e) => setLinkForm((f) => ({ ...f, source_id: e.target.value }))} /></Field>
          <Field label="Target ID" required><input required className={inputClass} value={linkForm.target_id} onChange={(e) => setLinkForm((f) => ({ ...f, target_id: e.target.value }))} /></Field>
          <Field label="Source type"><select className={inputClass} value={linkForm.source_type} onChange={(e) => setLinkForm((f) => ({ ...f, source_type: e.target.value }))}>{ENTITY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}</select></Field>
          <Field label="Target type"><select className={inputClass} value={linkForm.target_type} onChange={(e) => setLinkForm((f) => ({ ...f, target_type: e.target.value }))}>{ENTITY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}</select></Field>
          <Field label="Relationship"><select className={inputClass} value={linkForm.relationship} onChange={(e) => setLinkForm((f) => ({ ...f, relationship: e.target.value }))}>{RELATIONSHIPS.map((r) => <option key={r} value={r}>{r}</option>)}</select></Field>
          <Field label="Amount (₹)" hint="optional"><input type="number" className={inputClass} value={linkForm.amount_inr} onChange={(e) => setLinkForm((f) => ({ ...f, amount_inr: e.target.value }))} /></Field>
          <div className="sm:col-span-2 flex items-center gap-3">
            <Button type="submit" loading={link.loading} icon={Link2} size="sm">Create link</Button>
            {link.data?.linked && <Badge tone="safe" dot>Relationship created</Badge>}
          </div>
        </form>
      )}
    </Card>
  );
}

function CasesPanel() {
  const [filters, setFilters] = useState({ status: "", fraud_type: "", severity: "", page: 1, page_size: 8 });
  const { data, loading, error, refetch } = useApi(() => Fraud.cases(filters), [JSON.stringify(filters)]);
  const [showCreate, setShowCreate] = useState(false);
  const create = useAsyncAction((p) => Fraud.createCase(p));
  const [form, setForm] = useState({ title: "", fraud_type: "digital_arrest", severity: "medium", description: "" });

  return (
    <Card className="p-5">
      <SectionLabel
        right={
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" icon={RefreshCw} onClick={refetch}>Refresh</Button>
            <Button size="sm" icon={FolderPlus} onClick={() => setShowCreate((v) => !v)}>New case</Button>
          </div>
        }
      >
        Investigation cases
      </SectionLabel>

      {showCreate && (
        <form
          className="mb-5 grid grid-cols-1 gap-3 rounded-lg border border-void-line bg-void-soft p-4 sm:grid-cols-4"
          onSubmit={async (e) => { e.preventDefault(); await create.act(form); setShowCreate(false); refetch(); }}
        >
          <input required placeholder="Case title" className={`${inputClass} sm:col-span-2`} value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
          <input required placeholder="Fraud type e.g. digital_arrest" className={inputClass} value={form.fraud_type} onChange={(e) => setForm((f) => ({ ...f, fraud_type: e.target.value }))} />
          <select className={inputClass} value={form.severity} onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value }))}>
            {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <Button type="submit" loading={create.loading} size="sm" className="sm:col-span-4 w-fit">Create case</Button>
        </form>
      )}

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <select className={inputClass} value={filters.status} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value, page: 1 }))}>
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
        </select>
        <select className={inputClass} value={filters.severity} onChange={(e) => setFilters((f) => ({ ...f, severity: e.target.value, page: 1 }))}>
          <option value="">All severities</option>
          {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input placeholder="Fraud type" className={inputClass} value={filters.fraud_type} onChange={(e) => setFilters((f) => ({ ...f, fraud_type: e.target.value, page: 1 }))} />
      </div>

      {error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : loading ? (
        <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
      ) : !data?.length ? (
        <EmptyState title="No cases yet" description="Cases you open will appear here for tracking and evidence generation." />
      ) : (
        <div className="space-y-2">
          {data.map((c) => (
            <div key={c.id} className="flex flex-col gap-2 rounded-lg border border-void-line bg-void-soft p-3.5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">{c.case_number}</p>
                <p className="text-sm font-medium text-ink">{c.title}</p>
                <p className="text-xs capitalize text-ink-faint">{c.fraud_type.replace(/_/g, " ")} · {c.states_involved?.join(", ") || "state unknown"}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone={severityTone[c.severity] || "neutral"}>{c.severity}</Badge>
                <Badge tone="neutral">{c.status}</Badge>
                {c.estimated_victims != null && <Badge tone="gold">{c.estimated_victims} victims</Badge>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function FraudGraph() {
  return (
    <div>
      <PageHeader
        eyebrow="Module 03 · Neo4j + GNN network intelligence"
        title="FraudGraph"
        description="Traverses phone numbers, bank accounts, devices, and IPs to surface mule networks, then scores each connected entity's fraud risk."
      />
      <div className="space-y-6">
        <GraphQuery />
        <AdminActions />
        <CasesPanel />
      </div>
    </div>
  );
}
