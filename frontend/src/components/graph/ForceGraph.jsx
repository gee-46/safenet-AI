import { useEffect, useRef, useState } from "react";
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from "d3-force";
import { motion } from "framer-motion";

const typeColor = {
  phone_number: "#FF5A36",
  bank_account: "#C9A227",
  device: "#2FD9C4",
  ip_address: "#8B7CF6",
  person: "#F0B429",
  organisation: "#5C6680",
};

export function ForceGraph({ nodes = [], edges = [], height = 420, onNodeClick, seedId }) {
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ w: 640, h: height });
  const [positions, setPositions] = useState([]);
  const [links, setLinks] = useState([]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width;
      setDims({ w: Math.max(w, 280), h: height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [height]);

  useEffect(() => {
    if (!nodes.length) {
      setPositions([]);
      setLinks([]);
      return;
    }
    const simNodes = nodes.map((n) => ({ ...n }));
    const nodeIds = new Set(simNodes.map((n) => n.id));
    const simLinks = edges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e) => ({ ...e }));

    const sim = forceSimulation(simNodes)
      .force("link", forceLink(simLinks).id((d) => d.id).distance(90).strength(0.5))
      .force("charge", forceManyBody().strength(-220))
      .force("center", forceCenter(dims.w / 2, dims.h / 2))
      .force("collide", forceCollide(28))
      .stop();

    for (let i = 0; i < 260; i++) sim.tick();

    setPositions(simNodes);
    setLinks(simLinks);
  }, [nodes, edges, dims.w, dims.h]);

  if (!nodes.length) return null;

  return (
    <div ref={containerRef} className="w-full overflow-hidden rounded-xl border border-void-line bg-void-soft">
      <svg width="100%" height={dims.h} viewBox={`0 0 ${dims.w} ${dims.h}`}>
        <defs>
          <radialGradient id="nodeGlowSeed" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FF5A36" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#FF5A36" stopOpacity="0" />
          </radialGradient>
        </defs>
        {links.map((l, i) => {
          const s = l.source, t = l.target;
          if (!s?.x || !t?.x) return null;
          return (
            <motion.line
              key={i}
              x1={s.x} y1={s.y} x2={t.x} y2={t.y}
              stroke="#232B3D"
              strokeWidth={Math.min(1 + (l.weight || 1) * 0.6, 4)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: i * 0.01 }}
            />
          );
        })}
        {positions.map((n, i) => {
          const isSeed = n.id === seedId;
          const color = typeColor[n.type] || "#5C6680";
          const r = 6 + Math.min(n.risk_score ?? 0, 1) * 10 + (isSeed ? 4 : 0);
          return (
            <motion.g
              key={n.id}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: i * 0.02, ease: [0.16, 1, 0.3, 1] }}
              className="cursor-pointer"
              onClick={() => onNodeClick?.(n)}
            >
              {isSeed && <circle cx={n.x} cy={n.y} r={r + 14} fill="url(#nodeGlowSeed)" />}
              <circle cx={n.x} cy={n.y} r={r} fill={color} fillOpacity={0.85} stroke={isSeed ? "#fff" : "#0A0C12"} strokeWidth={isSeed ? 2 : 1.5} />
              <text
                x={n.x}
                y={n.y + r + 12}
                textAnchor="middle"
                fill="#9AA4BC"
                fontSize="9"
                fontFamily="IBM Plex Mono"
              >
                {(n.label || n.id).slice(0, 14)}
              </text>
            </motion.g>
          );
        })}
      </svg>
    </div>
  );
}

export function GraphLegend() {
  return (
    <div className="flex flex-wrap gap-3">
      {Object.entries(typeColor).map(([k, c]) => (
        <span key={k} className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
          <span className="h-2 w-2 rounded-full" style={{ background: c }} />
          {k.replace(/_/g, " ")}
        </span>
      ))}
    </div>
  );
}
