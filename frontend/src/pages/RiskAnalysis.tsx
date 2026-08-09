import * as React from "react";
import { motion } from "framer-motion";
import {
  ShieldAlert,
  Loader2,
  TriangleAlert,
  CheckCircle2,
  XCircle,
  FileText,
  AlertOctagon,
  ClipboardCheck,
} from "lucide-react";
import { PageHeader, PageError } from "../components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { listDocuments, generateReport, type DocumentItem, type ReportPayload, type RedFlagRow, type ChecklistRow } from "../api";
import { isAnalyst } from "../auth";

const SEVERITY_META: Record<string, { variant: "danger" | "warning" | "primary"; label: string }> = {
  high: { variant: "danger", label: "High" },
  medium: { variant: "warning", label: "Medium" },
  low: { variant: "primary", label: "Low" },
};

export function RiskAnalysis() {
  const canAnalyze = isAnalyst();
  const [docs, setDocs] = React.useState<DocumentItem[] | null>(null);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [report, setReport] = React.useState<ReportPayload | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listDocuments();
      setDocs(resp.items.filter((d) => d.status === "ready"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const payload = await generateReport(Array.from(selected));
      setReport(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="glass flex h-64 items-center justify-center rounded-xl">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
      </div>
    );
  }

  if (error && !docs) return <PageError message={error} onRetry={load} />;

  const readyDocs = docs || [];
  const redFlags: RedFlagRow[] = report?.sections.risk || [];
  const checklist = (report?.sections.compliance || []) as (ChecklistRow | { completion_pct: number })[];
  const completion = checklist.find((c) => "completion_pct" in c) as { completion_pct: number } | undefined;

  const riskScore = (() => {
    if (!redFlags.length) return 0;
    const weights: Record<string, number> = { high: 3, medium: 2, low: 1 };
    const raw = redFlags.reduce((sum, f) => sum + (weights[f.severity] || 1), 0);
    return Math.min(100, Math.round((raw / (redFlags.length * 3)) * 100));
  })();

  const riskTone = riskScore >= 66 ? "danger" : riskScore >= 33 ? "warning" : "success";

  return (
    <div>
      <PageHeader
        title="Risk Analysis"
        description="Multi-agent financial risk assessment over your selected documents"
      />

      {error && (
        <div className="mb-4 rounded-lg border border-danger/20 bg-danger-soft px-3 py-2 text-xs text-danger">
          {error}
        </div>
      )}

      <Card className="mb-4">
        <CardContent className="pt-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="mb-2 text-sm font-semibold text-foreground">
                Select documents to analyze
              </div>
              {readyDocs.length === 0 ? (
                <p className="text-xs text-muted">
                  No ready documents yet. Upload and process documents first.
                </p>
              ) : (
                <div className="flex max-w-2xl flex-wrap gap-2">
                  <button
                    onClick={() => setSelected(new Set(readyDocs.map((d) => d.id)))}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-muted hover:border-primary/40 hover:text-foreground"
                  >
                    Select all
                  </button>
                  {readyDocs.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => {
                        const next = new Set(selected);
                        if (next.has(d.id)) next.delete(d.id);
                        else next.add(d.id);
                        setSelected(next);
                      }}
                      className={selected.has(d.id) ? "rounded-full border border-primary bg-primary-soft px-3 py-1 text-xs font-medium text-primary" : "rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-muted hover:border-primary/40 hover:text-foreground"}
                    >
                      {d.filename.length > 24 ? d.filename.slice(0, 24) + "…" : d.filename}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Button onClick={() => void run()} disabled={!canAnalyze || running || selected.size === 0} className="shrink-0">
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldAlert className="h-4 w-4" />}
              {running ? "Analyzing…" : `Run risk analysis${selected.size ? ` (${selected.size})` : ""}`}
            </Button>
          </div>
          {!canAnalyze && (
            <p className="mt-3 text-xs text-warning">Running analysis requires analyst access.</p>
          )}
        </CardContent>
      </Card>

      {report ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle>Risk score</CardTitle>
                <CardDescription>{report.document_count} documents analyzed</CardDescription>
              </CardHeader>
              <CardContent className="text-center">
                <div className="relative mx-auto mb-4 h-40 w-40">
                  <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
                    <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
                    <motion.circle
                      cx="50"
                      cy="50"
                      r="42"
                      fill="none"
                      stroke={riskTone === "danger" ? "#EF4444" : riskTone === "warning" ? "#F59E0B" : "#10B981"}
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={2 * Math.PI * 42}
                      initial={{ strokeDashoffset: 2 * Math.PI * 42 }}
                      animate={{ strokeDashoffset: 2 * Math.PI * 42 * (1 - riskScore / 100) }}
                      transition={{ duration: 1, ease: "easeOut" }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl font-bold text-foreground">{riskScore}</span>
                    <span className="text-[10px] uppercase tracking-widest text-muted">/ 100</span>
                  </div>
                </div>
                <Badge variant={riskTone === "danger" ? "danger" : riskTone === "warning" ? "warning" : "success"} className="text-xs">
                  {riskTone === "danger" ? "Elevated risk" : riskTone === "warning" ? "Moderate risk" : "Low risk"}
                </Badge>
                <div className="mt-4 text-xs text-muted">
                  {redFlags.length} red flag{redFlags.length === 1 ? "" : "s"} detected
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Executive summary</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-foreground">{report.executive_summary}</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TriangleAlert className="h-4 w-4 text-warning" /> Red flags
              </CardTitle>
              <CardDescription>Anomalies and risk indicators with traceable evidence</CardDescription>
            </CardHeader>
            <CardContent>
              {redFlags.length === 0 ? (
                <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-white/10 py-10 text-sm text-success">
                  <CheckCircle2 className="h-4 w-4" /> No red flags detected in the selected documents.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Severity</TableHead>
                      <TableHead>Finding</TableHead>
                      <TableHead className="hidden md:table-cell">Evidence</TableHead>
                      <TableHead className="hidden lg:table-cell">Source</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {redFlags.map((flag, i) => {
                      const meta = SEVERITY_META[flag.severity] || SEVERITY_META.medium;
                      return (
                        <TableRow key={i}>
                          <TableCell>
                            <Badge variant={meta.variant}>{meta.label}</Badge>
                          </TableCell>
                          <TableCell className="text-sm font-medium text-foreground">{flag.finding}</TableCell>
                          <TableCell className="hidden max-w-sm text-xs text-muted md:table-cell">{flag.evidence}</TableCell>
                          <TableCell className="hidden text-xs text-muted lg:table-cell">
                            <span className="inline-flex items-center gap-1">
                              <FileText className="h-3 w-3" /> p{flag.page}
                            </span>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ClipboardCheck className="h-4 w-4 text-primary" /> Compliance checklist
              </CardTitle>
              <CardDescription>Documents checked against standard due diligence requirements</CardDescription>
            </CardHeader>
            <CardContent>
              {completion !== undefined && (
                <div className="mb-4 flex items-center gap-3">
                  <div className="w-full max-w-sm">
                    <Progress value={completion.completion_pct} indicatorClassName={completion.completion_pct >= 70 ? "bg-success" : completion.completion_pct >= 40 ? "bg-warning" : "bg-danger"} />
                  </div>
                  <span className="text-xs font-semibold text-foreground">{completion.completion_pct}% complete</span>
                </div>
              )}
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {checklist
                  .filter((c) => "status" in c)
                  .map((item, i) => {
                    const row = item as ChecklistRow;
                    return (
                      <div key={i} className="flex items-start gap-2 rounded-lg border border-white/5 bg-white/[0.02] p-3">
                        {row.status === "present" ? (
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                        ) : (
                          <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
                        )}
                        <div>
                          <div className="text-sm text-foreground">{row.item}</div>
                          {row.note && <div className="text-xs text-muted">{row.note}</div>}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="pt-5">
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-white/10 py-16 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-warning-soft text-warning">
                <AlertOctagon className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">No analysis yet</h3>
              <p className="mt-1 max-w-sm text-xs text-muted">
                Select one or more processed documents above to run the multi-agent risk assessment.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
