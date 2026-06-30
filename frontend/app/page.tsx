"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  ApprovalItem,
  AuditEntry,
  Incident,
} from "@/lib/api";
import { Brief } from "@/components/Brief";
import { CompoundingChart } from "@/components/CompoundingChart";

type Tab = "console" | "audit";

export default function Home() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [audit, setAudit] = useState<{ valid: boolean; entries: AuditEntry[] }>({
    valid: true,
    entries: [],
  });
  const [replay, setReplay] = useState<any>(null);
  const [backend, setBackend] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<Tab>("console");

  const refresh = useCallback(async () => {
    try {
      const [inc, appr, aud, health] = await Promise.all([
        api.incidents(),
        api.approvals(),
        api.audit(),
        api.health(),
      ]);
      setIncidents(inc);
      setApprovals(appr);
      setAudit(aud);
      setBackend(health.memory_backend);
      setSelected((prev) =>
        prev ? inc.find((i) => i.id === prev.id) || prev : inc[0] || null
      );
    } catch {
      /* backend not up yet */
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  const runDemo = async () => {
    setBusy(true);
    try {
      await api.demoSeed();
      const r = await api.demoReplay();
      setReplay(r);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const newIncident = async () => {
    setBusy(true);
    try {
      const inc = await api.createIncident({
        title: "charge endpoint returning 500s, db connections maxed",
        service: "payments-api",
        severity: "SEV2",
        description: "Customers report failed payments; connection slots reserved.",
        source: "pagerduty",
      });
      setSelected(inc);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const decide = async (id: string, decision: string) => {
    await api.decide(id, { decision, decided_by: "on-call" });
    await refresh();
  };

  const resolve = async (id: string) => {
    await api.resolve(id, {
      resolution:
        "Scaled pgbouncer pool 20 -> 60 and rolled payments-api; 5xx cleared.",
      feedback_helpful: true,
    });
    await refresh();
  };

  return (
    <div>
      <section className="hero container">
        <h1>
          Your on-call has a hangover.
          <br />
          <span className="grad">Recall remembers last night.</span>
        </h1>
        <p>
          A self-hosted, open-source Cognee memory layer for incident response.
          Every alert recalls similar past incidents with citations, drafts a
          triage brief through human-in-the-loop gates, and feeds the outcome
          back so the next incident resolves faster.
        </p>
        <div className="cta">
          <button className="btn primary" onClick={runDemo} disabled={busy}>
            {busy ? "Running…" : "Run the compounding demo"}
          </button>
          <button className="btn" onClick={newIncident} disabled={busy}>
            Trigger an alert
          </button>
          {backend && (
            <span className="pill" style={{ alignSelf: "center" }}>
              memory: {backend}
            </span>
          )}
        </div>
      </section>

      <div className="container">
        <div className="tabs">
          <div
            className={`tab ${tab === "console" ? "active" : ""}`}
            onClick={() => setTab("console")}
          >
            Incident console
          </div>
          <div
            className={`tab ${tab === "audit" ? "active" : ""}`}
            onClick={() => setTab("audit")}
          >
            Audit log {audit.valid ? "· verified" : "· TAMPERED"}
          </div>
        </div>

        {replay && (
          <div className="card">
            <h2>Memory compounding</h2>
            <div className="sub">{replay.compounding.headline}</div>
            <CompoundingChart
              coldMs={replay.compounding.cold_time_to_context_ms}
              warmMs={replay.compounding.warm_time_to_context_ms}
              coldRecalled={replay.compounding.cold_recalled_from_memory}
              warmRecalled={replay.compounding.warm_recalled_from_memory}
              improvementPct={replay.compounding.time_to_context_improvement_pct}
            />
          </div>
        )}

        {tab === "console" ? (
          <div className="grid">
            <div>
              <div className="card">
                <h2>Incident feed</h2>
                <div className="sub">
                  {incidents.length} incident(s). Click to inspect the cited brief.
                </div>
                {incidents.length === 0 && (
                  <div className="muted small">
                    No incidents yet — run the demo or trigger an alert.
                  </div>
                )}
                {incidents.map((inc) => (
                  <div
                    key={inc.id}
                    className={`incident-item ${
                      selected?.id === inc.id ? "active" : ""
                    }`}
                    onClick={() => setSelected(inc)}
                  >
                    <div className="row spread">
                      <span className="small muted">{inc.id}</span>
                      <span className={`pill ${inc.severity.toLowerCase()}`}>
                        {inc.severity}
                      </span>
                    </div>
                    <div className="title">{inc.title}</div>
                    <div className="row spread">
                      <span className="small muted">{inc.service}</span>
                      <span className={`pill ${inc.status}`}>
                        {inc.status.replace("_", " ")}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="card">
                <h2>HITL approval queue</h2>
                <div className="sub">
                  Actions pause for a human. Every decision is signed in the audit log.
                </div>
                {approvals.filter((a) => a.status === "pending").length === 0 && (
                  <div className="muted small">Nothing pending.</div>
                )}
                {approvals
                  .filter((a) => a.status === "pending")
                  .map((a) => (
                    <div className="action" key={a.id}>
                      <div className="title">{a.action_title}</div>
                      <div className="detail">{a.action_detail}</div>
                      <div className="row wrap">
                        <button className="btn sm primary" onClick={() => decide(a.id, "approve")}>
                          Approve
                        </button>
                        <button className="btn sm" onClick={() => decide(a.id, "override")}>
                          Override
                        </button>
                        <button className="btn sm ghost" onClick={() => decide(a.id, "reject")}>
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            <div>
              <div className="card">
                <div className="row spread">
                  <h2>Case brief</h2>
                  {selected && selected.status !== "resolved" && (
                    <button className="btn sm" onClick={() => resolve(selected.id)}>
                      Mark resolved → improve()
                    </button>
                  )}
                </div>
                <div className="sub">
                  Source-cited triage, built from Cognee&apos;s hybrid graph-vector recall.
                </div>
                {selected ? (
                  <Brief incident={selected} />
                ) : (
                  <div className="muted small">Select an incident.</div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="card">
            <h2>Signed audit log</h2>
            <div className="sub">
              Hash-chained, HMAC-signed. Chain integrity:{" "}
              {audit.valid ? "verified" : "TAMPERED"}.
            </div>
            <div className="audit-row" style={{ fontWeight: 700, color: "var(--muted)" }}>
              <span>actor</span>
              <span>action</span>
              <span>detail</span>
            </div>
            {audit.entries.map((e) => (
              <div className="audit-row" key={e.id}>
                <span className="muted">{e.actor}</span>
                <span className="act">{e.action}</span>
                <span>{e.detail}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
