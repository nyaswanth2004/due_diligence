import { useCallback, useEffect, useState } from "react";
import {
  ChecklistRow,
  DocumentItem,
  generateReport,
  getReport,
  listReports,
  RatioRow,
  RedFlagRow,
  ReportItem,
  ReportPayload,
  TrendRow,
} from "../api";

function formatMoney(v: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}

function isRatio(row: RatioRow | TrendRow): row is RatioRow {
  return "value" in row && "interpretation" in row;
}

function isChecklist(row: ChecklistRow | { completion_pct: number }): row is ChecklistRow {
  return "item" in row;
}

function riskClass(level: string): string {
  return `risk ${level}`;
}

export function ReportPanel({ documents }: { documents: DocumentItem[] }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshList = useCallback(() => {
    listReports()
      .then((res) => setReports(res.items))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  const toggle = (id: string) =>
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  const run = async () => {
    if (selected.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const payload = await generateReport(selected);
      setReport(payload);
      refreshList();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const open = async (id: string) => {
    try {
      const item = await getReport(id);
      setReport(item.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const ready = documents.filter((d) => d.status === "ready");

  return (
    <section>
      <div className="card">
        <h2>Generate due diligence report</h2>
        <p className="muted">
          Runs the multi-agent pipeline: deterministic figure extraction,
          ratio analysis, risk scan, disclosure completeness, and report
          compilation.
        </p>
        {ready.length === 0 ? (
          <p className="muted">No processed documents available.</p>
        ) : (
          <div className="checklist">
            {ready.map((d) => (
              <label key={d.id}>
                <input
                  type="checkbox"
                  checked={selected.includes(d.id)}
                  onChange={() => toggle(d.id)}
                />
                {d.filename}
              </label>
            ))}
          </div>
        )}
        <button onClick={run} disabled={selected.length === 0 || loading}>
          {loading ? "Generating…" : `Generate report (${selected.length})`}
        </button>
        {error && <p className="error">{error}</p>}
      </div>

      {reports.length > 0 && (
        <div className="card">
          <h2>Previous reports</h2>
          {reports.map((r) => (
            <button key={r.id} className="link" onClick={() => open(r.id)}>
              {r.title} — {r.created_at.slice(0, 10)}
            </button>
          ))}
        </div>
      )}

      {report && <ReportView report={report} />}
    </section>
  );
}

function ReportView({ report }: { report: ReportPayload }) {
  const ratios = report.sections.financial_analysis?.filter(isRatio) ?? [];
  const trends = report.sections.financial_analysis?.filter((r) => !isRatio(r)) as TrendRow[];
  const flags = report.sections.risk ?? [];
  const checklist = report.sections.compliance?.filter(isChecklist) ?? [];
  const completion = report.sections.compliance?.find((c) => !isChecklist(c)) as
    | { completion_pct: number }
    | undefined;

  return (
    <div className="card">
      <h2>{report.title}</h2>
      <p className="muted">
        Generated {report.generated_on} · {report.document_count} document(s)
      </p>

      <h3>Executive summary</h3>
      <p className="pre-wrap">{report.executive_summary}</p>

      <h3>Summary</h3>
      <p>{report.summary}</p>

      <h3>Financial analysis</h3>
      {ratios.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>Ratio</th>
              <th>Value</th>
              <th>Formula</th>
              <th>Interpretation</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {ratios.map((r, i) => (
              <tr key={i}>
                <td>{r.name}</td>
                <td>{r.value}</td>
                <td className="muted">{r.formula}</td>
                <td>{r.interpretation}</td>
                <td>
                  <span className={riskClass(r.risk_level)}>{r.risk_level}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">No ratios could be computed from the available figures.</p>
      )}

      {trends.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th>Current</th>
              <th>Prior</th>
              <th>Direction</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {trends.map((t, i) => (
              <tr key={i}>
                <td>{t.metric}</td>
                <td>{formatMoney(t.current)}</td>
                <td>{t.prior === null ? "—" : formatMoney(t.prior)}</td>
                <td>{t.direction}</td>
                <td>{t.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Risk flags</h3>
      {flags.length > 0 ? (
        flags.map((f: RedFlagRow, i) => (
          <div key={i} className="flag">
            <div className="hit-meta">
              <span className={riskClass(f.severity)}>{f.severity}</span>{" "}
              {f.chunk_id && ` · p.${f.page}`}
            </div>
            <p>
              <strong>{f.finding}</strong>
            </p>
            <p className="muted pre-wrap">{f.evidence}</p>
          </div>
        ))
      ) : (
        <p className="muted">No risk flags identified.</p>
      )}

      <h3>Disclosure completeness</h3>
      <p className="muted">
        {completion ? `${completion.completion_pct}% of required line items found.` : ""}
      </p>
      <ul>
        {checklist.map((c, i) => (
          <li key={i}>
            <span className={c.status === "present" ? "ok" : "missing"}>
              {c.status === "present" ? "✓" : "✗"}
            </span>{" "}
            {c.item}
          </li>
        ))}
      </ul>
    </div>
  );
}
