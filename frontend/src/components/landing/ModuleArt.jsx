import { motion } from "framer-motion";

const wrap = (children) => (
  <svg viewBox="0 0 120 80" className="h-full w-full">
    {children}
  </svg>
);

export function PhoneWaveArt() {
  return wrap(
    <>
      <rect x="40" y="10" width="30" height="60" rx="6" fill="none" stroke="#232B3D" strokeWidth="2" />
      <circle cx="55" cy="62" r="1.6" fill="#5C6680" />
      {[0, 1, 2, 3, 4, 5, 6].map((i) => (
        <motion.rect
          key={i}
          x={44 + i * 3.2}
          width="2"
          rx="1"
          fill="#FF5A36"
          initial={{ height: 4, y: 38 }}
          animate={{ height: [4, 18, 6, 22, 4][i % 5], y: [38, 24, 34, 20, 38][i % 5] }}
          transition={{ duration: 1.6, repeat: Infinity, delay: i * 0.12, ease: "easeInOut" }}
        />
      ))}
      <circle cx="90" cy="20" r="3" fill="#FF5A36" opacity="0.8" />
      <circle cx="90" cy="20" r="7" fill="none" stroke="#FF5A36" strokeWidth="1" opacity="0.4" />
    </>
  );
}

export function NoteArt() {
  return wrap(
    <>
      <rect x="18" y="22" width="84" height="38" rx="4" fill="none" stroke="#232B3D" strokeWidth="2" />
      <circle cx="60" cy="41" r="13" fill="none" stroke="#C9A227" strokeWidth="1.5" />
      <motion.circle
        cx="60" cy="41" r="13" fill="none" stroke="#E3C158" strokeWidth="2"
        strokeDasharray="4 4"
        animate={{ rotate: 360 }}
        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
        style={{ transformOrigin: "60px 41px" }}
      />
      <line x1="26" y1="30" x2="34" y2="30" stroke="#5C6680" strokeWidth="1.5" />
      <line x1="86" y1="52" x2="94" y2="52" stroke="#5C6680" strokeWidth="1.5" />
      <motion.rect
        x="18" y="22" width="6" height="38" fill="#2FD9C4"
        animate={{ x: [18, 96, 18] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        opacity="0.5"
      />
    </>
  );
}

export function GraphArt() {
  const nodes = [
    [30, 40], [58, 20], [58, 60], [90, 15], [90, 40], [90, 65],
  ];
  const edges = [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]];
  return wrap(
    <>
      {edges.map(([a, b], i) => (
        <motion.line
          key={i}
          x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]}
          stroke="#232B3D" strokeWidth="1.5"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1, delay: i * 0.15 }}
        />
      ))}
      {nodes.map(([x, y], i) => (
        <motion.circle
          key={i}
          cx={x} cy={y} r={i === 0 ? 6 : 4}
          fill={i === 0 ? "#FF5A36" : "#8B7CF6"}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.4, delay: i * 0.12 }}
        />
      ))}
    </>
  );
}

export function MapArt() {
  const hexes = [
    [40, 30], [56, 20], [56, 40], [72, 30], [40, 50], [72, 50],
  ];
  return wrap(
    <>
      {hexes.map(([cx, cy], i) => (
        <motion.polygon
          key={i}
          points={`${cx},${cy - 9} ${cx + 8},${cy - 4.5} ${cx + 8},${cy + 4.5} ${cx},${cy + 9} ${cx - 8},${cy + 4.5} ${cx - 8},${cy - 4.5}`}
          fill={i === 2 ? "rgba(255,90,54,0.35)" : "rgba(47,217,196,0.12)"}
          stroke={i === 2 ? "#FF5A36" : "#232B3D"}
          strokeWidth="1.5"
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: i * 0.08 }}
        />
      ))}
      <motion.circle
        cx="56" cy="40" r="2"
        fill="#FF5A36"
        animate={{ opacity: [1, 0.3, 1] }}
        transition={{ duration: 1.6, repeat: Infinity }}
      />
    </>
  );
}

export function ChatArt() {
  return wrap(
    <>
      <rect x="16" y="18" width="56" height="34" rx="8" fill="none" stroke="#232B3D" strokeWidth="2" />
      <polygon points="30,52 30,60 40,52" fill="none" stroke="#232B3D" strokeWidth="2" />
      {[26, 38, 50].map((x, i) => (
        <motion.rect
          key={i} x={x} y="32" width="10" height="3" rx="1.5" fill="#2FD9C4"
          initial={{ opacity: 0.2 }} animate={{ opacity: [0.2, 1, 0.2] }}
          transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.25 }}
        />
      ))}
      <rect x="70" y="42" width="34" height="22" rx="7" fill="none" stroke="#5C6680" strokeWidth="1.5" opacity="0.6" />
      <circle cx="87" cy="53" r="4" fill="#F0B429" opacity="0.7" />
    </>
  );
}

export function DocArt() {
  return wrap(
    <>
      <rect x="34" y="10" width="44" height="58" rx="4" fill="none" stroke="#232B3D" strokeWidth="2" />
      {[20, 28, 36, 44].map((y, i) => (
        <motion.line
          key={i} x1="42" y1={y} x2={i === 3 ? 60 : 70} y2={y} stroke="#5C6680" strokeWidth="1.5"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.5, delay: i * 0.1 }}
        />
      ))}
      <motion.g initial={{ scale: 0, rotate: -20 }} animate={{ scale: 1, rotate: -14 }} transition={{ duration: 0.5, delay: 0.5, type: "spring" }}>
        <circle cx="82" cy="52" r="13" fill="rgba(201,162,39,0.15)" stroke="#C9A227" strokeWidth="1.5" />
        <path d="M77 52l3.5 3.5L88 48" fill="none" stroke="#E3C158" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </motion.g>
    </>
  );
}
