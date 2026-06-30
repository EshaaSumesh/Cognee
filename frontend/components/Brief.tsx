"use client";

import { Incident } from "@/lib/api";
import { MemoryGraph } from "./MemoryGraph";

export function Brief({ incident }: { incident: Incident }) {
  const b = incident.brief;
  if (!b) return <div className="muted">No brief yet.</div>;

  return (
    <div className="brief">
      <div className="row spread wrap" style={{ marginBottom: 12 }}>
        <div className="row wrap">
          <span className={`pill ${incident.severity.toLowerCase()}`}>{incident.severity}</span>
          <span className={`pill ${incident.status}`}>{incident.status.replace("_", " ")}</span>
          {b.recalled_from_memory && <span className="pill recall">memory recalled</span>}
        </div>
        <span className="small muted">ttc {b.time_to_context_ms} ms</span>
      </div>

      <p className="summary">{b.summary}</p>

      {b.likely_root_cause && (
        <div className="banner">
          <strong>Likely root cause:</strong> {b.likely_root_cause}
        </div>
      )}

      {b.similar_incidents.length > 0 && (
        <p className="small muted">
          Similar incidents recalled: {b.similar_incidents.join(", ")}
        </p>
      )}

      <h2 style={{ marginTop: 18 }}>Memory graph</h2>
      <div className="sub">What Cognee recalled (hybrid graph + vector), with citations.</div>
      <MemoryGraph citations={b.citations} />

      <h2 style={{ marginTop: 10 }}>Suggested actions</h2>
      <div className="sub">Each action routes through the HITL approval queue.</div>
      {b.suggested_actions.map((a) => (
        <div className="action" key={a.id}>
          <div className="row spread">
            <span className="title">{a.title}</span>
            {a.requires_approval ? (
              <span className="pill awaiting_approval">needs approval</span>
            ) : (
              <span className="pill resolved">auto</span>
            )}
          </div>
          <div className="detail">{a.detail}</div>
        </div>
      ))}

      <h2 style={{ marginTop: 10 }}>Citations</h2>
      <div className="sub">Every claim traces to a source in memory.</div>
      {b.citations.map((c) => (
        <div className="citation" key={c.index}>
          <div className="src">
            [{c.index}] {c.source} <span className="muted small">· {c.kind}</span>
          </div>
          <div className="snip">{c.snippet}</div>
        </div>
      ))}
    </div>
  );
}
