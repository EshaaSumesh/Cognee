"use client";

import { Citation } from "@/lib/api";

const KIND_COLOR: Record<string, string> = {
  incident: "#f87171",
  postmortem: "#fbbf24",
  runbook: "#34d399",
  event: "#5b8cff",
};

/**
 * Lightweight hub-and-spoke visualization of what Cognee recalled for this
 * incident: the alert in the center, each cited memory node around it.
 */
export function MemoryGraph({ citations }: { citations: Citation[] }) {
  const W = 460;
  const H = 300;
  const cx = W / 2;
  const cy = H / 2;
  const r = 110;
  const nodes = citations.slice(0, 8);

  return (
    <div className="graph-wrap">
      <svg width={W} height={H} role="img" aria-label="memory graph">
        {nodes.map((c, i) => {
          const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1) - Math.PI / 2;
          const x = cx + r * Math.cos(angle);
          const y = cy + r * Math.sin(angle);
          return (
            <line
              key={`l-${i}`}
              x1={cx}
              y1={cy}
              x2={x}
              y2={y}
              stroke="#232734"
              strokeWidth={1.5}
            />
          );
        })}
        <circle cx={cx} cy={cy} r={34} fill="#171a24" stroke="#5b8cff" strokeWidth={2} />
        <text x={cx} y={cy + 4} textAnchor="middle" fill="#e7e9ee" fontSize={12} fontWeight={700}>
          alert
        </text>
        {nodes.map((c, i) => {
          const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1) - Math.PI / 2;
          const x = cx + r * Math.cos(angle);
          const y = cy + r * Math.sin(angle);
          const color = KIND_COLOR[c.kind] || "#5b8cff";
          return (
            <g key={`n-${i}`}>
              <circle cx={x} cy={y} r={22} fill="#12141c" stroke={color} strokeWidth={2} />
              <text x={x} y={y - 2} textAnchor="middle" fill={color} fontSize={9} fontWeight={700}>
                [{c.index}]
              </text>
              <text x={x} y={y + 9} textAnchor="middle" fill="#8b91a3" fontSize={8}>
                {c.kind.slice(0, 8)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
