import { useCallback, useEffect, useState } from "react";
import { AuditEntry, listAudit } from "../api";

const ACTIONS = [
  "auth.login",
  "document.upload",
  "document.delete",
  "document.search",
  "qa.ask",
  "report.generate",
];

export function AuditPanel() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [action, setAction] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (selectedAction: string) => {
    try {
      const res = await listAudit(selectedAction || undefined, 200);
      setEntries(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    load(action);
  }, [action, load]);

  return (
    <section>
      <div className="card">
        <h2>Audit log</h2>
        <div className="row">
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">All actions</option>
            {ACTIONS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <span className="muted">{total} event(s)</span>
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      <div className="card">
        {entries.length === 0 ? (
          <p className="muted">No audit events recorded.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Time (UTC)</th>
                <th>User</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Details</th>
                <th>IP</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>{e.created_at.replace("T", " ").slice(0, 19)}</td>
                  <td>{e.username || "—"}</td>
                  <td>
                    <span className="badge">{e.action}</span>
                  </td>
                  <td>
                    {e.resource_type && (
                      <>
                        {e.resource_type}
                        {e.resource_id ? `:${e.resource_id.slice(0, 8)}` : ""}
                      </>
                    )}
                  </td>
                  <td className="muted small">{JSON.stringify(e.details)}</td>
                  <td className="muted">{e.ip_address}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
