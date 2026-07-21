import { useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip as LeafletTooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { MapPinned, RefreshCw, Crosshair } from "lucide-react";
import { Geo } from "../lib/api";
import { useApi } from "../lib/useApi";
import {
  PageHeader, Card, SectionLabel, inputClass, Button, Badge,
  EmptyState, ErrorState, Skeleton,
} from "../components/ui/Primitives";

const INDIA_CENTER = [22.9734, 78.6569];

function riskColor(risk) {
  if (risk > 0.66) return "#FF5A36";
  if (risk > 0.33) return "#F0B429";
  return "#2FD9C4";
}

function CrimeMap() {
  const [params, setParams] = useState({ h3_resolution: 7, days_back: 30, state: "" });
  const { data, loading, error, refetch } = useApi(() => Geo.crimes(params), [JSON.stringify(params)]);

  return (
    <Card className="p-5">
      <SectionLabel right={<Button size="sm" variant="ghost" icon={RefreshCw} onClick={refetch}>Refresh</Button>}>
        H3 crime heatmap
      </SectionLabel>
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <select className={inputClass} value={params.h3_resolution} onChange={(e) => setParams((p) => ({ ...p, h3_resolution: Number(e.target.value) }))}>
          <option value={5}>Res 5 · district</option>
          <option value={7}>Res 7 · neighbourhood</option>
          <option value={9}>Res 9 · street</option>
        </select>
        <select className={inputClass} value={params.days_back} onChange={(e) => setParams((p) => ({ ...p, days_back: Number(e.target.value) }))}>
          {[7, 30, 90, 365].map((d) => <option key={d} value={d}>{d}d window</option>)}
        </select>
        <input className={`${inputClass} sm:col-span-2`} placeholder="State filter (optional)" value={params.state} onChange={(e) => setParams((p) => ({ ...p, state: e.target.value }))} />
      </div>

      {error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <div className="relative overflow-hidden rounded-xl border border-void-line">
          {loading && <div className="absolute inset-0 z-[400] flex items-center justify-center bg-void/70"><Skeleton className="h-full w-full" /></div>}
          <MapContainer center={INDIA_CENTER} zoom={4.4} scrollWheelZoom style={{ height: 440, width: "100%", background: "#0F131C" }}>
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; OpenStreetMap &copy; CARTO'
            />
            {data?.clusters?.map((c) => (
              <CircleMarker
                key={c.h3_index}
                center={[c.center.lat, c.center.lng]}
                radius={6 + Math.min(c.scam_count + c.counterfeit_count, 40) * 0.5}
                pathOptions={{ color: riskColor(c.risk_score), fillColor: riskColor(c.risk_score), fillOpacity: 0.55, weight: 1.5 }}
              >
                <LeafletTooltip direction="top">
                  <div className="font-mono text-[11px]">
                    <strong>{c.city || "Unknown"}, {c.state || "—"}</strong><br />
                    Scam: {c.scam_count} · Counterfeit: {c.counterfeit_count}<br />
                    Risk: {Math.round(c.risk_score * 100)}% · {c.dominant_fraud_type || "mixed"}
                  </div>
                </LeafletTooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      )}
      {data && (
        <p className="mt-3 font-mono text-[11px] text-ink-faint">
          {data.total_incidents} incidents · {data.clusters?.length || 0} H3 clusters · generated {new Date(data.generated_at).toLocaleTimeString("en-IN")}
        </p>
      )}
    </Card>
  );
}

function PatrolPriorities() {
  const [state, setState] = useState("");
  const { data, loading, error, refetch } = useApi(() => Geo.patrolPriorities({ top_n: 8, days_back: 7, state }), [state]);
  return (
    <Card className="p-5">
      <SectionLabel right={<Crosshair className="h-4 w-4 text-ink-faint" />}>Patrol priorities · 7d</SectionLabel>
      <input className={`${inputClass} mb-4`} placeholder="Filter by state" value={state} onChange={(e) => setState(e.target.value)} />
      {error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
      ) : !data?.priorities?.length ? (
        <EmptyState title="No priority zones" description="Nothing above threshold in this window." />
      ) : (
        <ol className="space-y-2">
          {data.priorities.map((p, i) => (
            <li key={p.h3_index || i} className="flex items-center gap-3 rounded-lg border border-void-line bg-void-soft p-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-void-raised font-mono text-[11px] text-ink-dim">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-ink">{p.city || p.h3_index}, {p.state || ""}</p>
                <p className="font-mono text-[10px] text-ink-faint">{p.dominant_fraud_type || "mixed"}</p>
              </div>
              <Badge tone={p.risk_score > 0.66 ? "danger" : p.risk_score > 0.33 ? "gold" : "safe"}>
                {Math.round((p.risk_score || 0) * 100)}%
              </Badge>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function StateSummary() {
  const { data, loading, error, refetch } = useApi(() => Geo.stateSummary(30), []);
  return (
    <Card className="p-5">
      <SectionLabel>State summary · 30d</SectionLabel>
      {error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : loading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
      ) : !data?.states?.length ? (
        <EmptyState title="No state data yet" />
      ) : (
        <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
          {data.states.map((s) => {
            const max = data.states[0]?.total_incidents || 1;
            return (
              <div key={s.state}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-ink-dim">{s.state}</span>
                  <span className="font-mono tabular text-ink-faint">{s.total_incidents}</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-void-soft">
                  <div className="h-full rounded-full bg-gradient-to-r from-gold-dim to-gold" style={{ width: `${(s.total_incidents / max) * 100}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function CityHotspots() {
  const { data, loading, error, refetch } = useApi(() => Geo.cityHotspots({ days_back: 30, limit: 12 }), []);
  return (
    <Card className="p-5">
      <SectionLabel>City hotspots · 30d</SectionLabel>
      {error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : loading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
      ) : !data?.hotspots?.length ? (
        <EmptyState title="No city data yet" />
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {data.hotspots.map((h, i) => (
            <div key={`${h.city}-${i}`} className="flex items-center justify-between rounded-lg border border-void-line bg-void-soft px-3 py-2">
              <span className="truncate text-xs text-ink-dim">{h.city}<span className="text-ink-faint">, {h.state}</span></span>
              <span className="font-mono text-xs tabular text-ink">{h.incident_count}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function GeoIntel() {
  return (
    <div>
      <PageHeader
        eyebrow="Module 04 · H3 hexagonal geospatial intelligence"
        title="GeoIntel"
        description="Aggregates scam and counterfeit incidents into hexagonal clusters for patrol deployment and command-level state visibility."
        action={<Badge tone="safe" dot><MapPinned className="h-3 w-3" /> Live map</Badge>}
      />
      <div className="space-y-6">
        <CrimeMap />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <PatrolPriorities />
          <StateSummary />
          <CityHotspots />
        </div>
      </div>
    </div>
  );
}
