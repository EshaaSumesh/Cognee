export type Severity = "SEV1" | "SEV2" | "SEV3";

export interface Citation {
  index: number;
  source: string;
  snippet: string;
  kind: "incident" | "postmortem" | "runbook" | "event";
}

export interface SuggestedAction {
  id: string;
  title: string;
  detail: string;
  requires_approval: boolean;
}

export interface TriageBrief {
  summary: string;
  likely_root_cause: string | null;
  similar_incidents: string[];
  suggested_actions: SuggestedAction[];
  citations: Citation[];
  time_to_context_ms: number;
  recalled_from_memory: boolean;
}

export interface Incident {
  id: string;
  title: string;
  service: string;
  severity: Severity;
  description: string;
  source: string;
  status: "investigating" | "awaiting_approval" | "resolved";
  created_at: number;
  resolved_at: number | null;
  brief: TriageBrief | null;
  resolution: string | null;
  feedback_helpful: boolean | null;
}

export interface ApprovalItem {
  id: string;
  incident_id: string;
  action_id: string;
  action_title: string;
  action_detail: string;
  status: "pending" | "approve" | "edit" | "override" | "reject";
  decided_by: string | null;
  decided_at: number | null;
  edited_detail: string | null;
  created_at: number;
}

export interface AuditEntry {
  id: string;
  ts: number;
  actor: string;
  action: string;
  incident_id: string | null;
  detail: string;
  prev_hash: string;
  hash: string;
}

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch("/api/health").then(j<any>),
  incidents: () => fetch("/api/incidents").then(j<Incident[]>),
  createIncident: (body: unknown) =>
    fetch("/api/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<Incident>),
  resolve: (id: string, body: unknown) =>
    fetch(`/api/incidents/${id}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<Incident>),
  approvals: () => fetch("/api/approvals").then(j<ApprovalItem[]>),
  decide: (id: string, body: unknown) =>
    fetch(`/api/approvals/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<ApprovalItem>),
  audit: () => fetch("/api/audit").then(j<{ valid: boolean; entries: AuditEntry[] }>),
  demoSeed: () => fetch("/api/demo/seed", { method: "POST" }).then(j<any>),
  demoReplay: () => fetch("/api/demo/replay", { method: "POST" }).then(j<any>),
};
