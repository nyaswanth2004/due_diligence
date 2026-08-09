import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  FileText,
  MessagesSquare,
  FolderKanban,
  UploadCloud,
  ArrowRight,
  CheckCircle2,
  Loader2,
  FolderOpen,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { PageError } from "../components/PageHeader";
import { RiskDonut, MetricBarChart, TrendAreaChart } from "../components/charts";
import { listDocuments, listReports, type DocumentItem, type ReportItem } from "../api";
import { cn } from "../lib/utils";

function StatCard({
  label,
  value,
  sub,
  icon,
  tone = "primary",
  to,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ReactNode;
  tone?: "primary" | "success" | "warning" | "danger";
  to?: string;
}) {
  const tones = {
    primary: "bg-primary-soft text-primary",
    success: "bg-success-soft text-success",
    warning: "bg-warning-soft text-warning",
    danger: "bg-danger-soft text-danger",
  };
  const inner = (
    <Card className="group relative overflow-hidden p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs font-medium text-muted">{label}</div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-foreground">{value}</div>
          {sub && <div className="mt-1 text-[11px] text-muted">{sub}</div>}
        </div>
        <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", tones[tone])}>{icon}</div>
      </div>
      {to && (
        <div className="mt-3 flex items-center gap-1 text-[11px] font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
          View <ArrowRight className="h-3 w-3" />
        </div>
      )}
    </Card>
  );
  return to ? <Link to={to}>{inner}</Link> : inner;
}

export function Dashboard() {
  const navigate = useNavigate();
  const [documents, setDocuments] = React.useState<DocumentItem[] | null>(null);
  const [reports, setReports] = React.useState<ReportItem[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [docResp, reportResp] = await Promise.all([listDocuments(), listReports()]);
      setDocuments(docResp.items);
      setReports(reportResp.items.slice(0, 5));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="glass h-32 animate-pulse rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) return <PageError message={error} onRetry={load} />;

  const docs = documents || [];
  const ready = docs.filter((d) => d.status === "ready");
  const processing = docs.filter((d) => d.status === "processing");
  const failed = docs.filter((d) => d.status === "failed");

  const typeCount = new Map<string, number>();
  for (const d of docs) {
    const key = d.doc_type === "pdf" ? "PDF" : d.doc_type === "excel" ? "Spreadsheet" : d.doc_type === "image" ? "Scanned" : d.doc_type.toUpperCase();
    typeCount.set(key, (typeCount.get(key) || 0) + 1);
  }
  const typeData = Array.from(typeCount.entries()).map(([name, value]) => ({ name, value }));

  const statusData = [
    { name: "Ready", value: ready.length, color: "#10B981" },
    { name: "Processing", value: processing.length, color: "#3B82F6" },
    { name: "Failed", value: failed.length, color: "#EF4444" },
  ];

  const byDay = new Map<string, number>();
  for (const d of docs) {
    const day = d.created_at.slice(0, 10);
    byDay.set(day, (byDay.get(day) || 0) + 1);
  }
  const trendData = Array.from(byDay.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-7)
    .map(([name, value]) => ({ name: name.slice(5), value }));

  const latestReport = reports[0];
  const metricNames = latestReport ? Object.keys(latestReport.data.financial_metrics).slice(0, 6) : [];
  const metricData = metricNames.map((key) => ({
    name: latestReport.data.financial_metrics[key].label,
    value: latestReport.data.financial_metrics[key].value,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">Dashboard</h1>
          <p className="mt-1 text-sm text-muted">Overview of your due diligence workspace</p>
        </div>
        <Button onClick={() => navigate("/documents")}>
          <UploadCloud className="h-4 w-4" /> Upload documents
        </Button>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        <StatCard label="Documents" value={docs.length} sub={`${ready.length} ready for analysis`} icon={<FileText className="h-5 w-5" />} tone="primary" to="/documents" />
        <StatCard label="Reports" value={reports.length} sub="Due diligence reports" icon={<FolderOpen className="h-5 w-5" />} tone="success" to="/reports" />
        <StatCard label="Processing" value={processing.length} sub={failed.length ? `${failed.length} failed` : "All caught up"} icon={processing.length ? <Loader2 className="h-5 w-5 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />} tone={failed.length ? "danger" : "warning"} />
        <StatCard label="Document types" value={typeData.length} sub="PDF, spreadsheet, scanned" icon={<FolderKanban className="h-5 w-5" />} tone="warning" />
      </motion.div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Document status</CardTitle>
            <CardDescription>Health of your corpus</CardDescription>
          </CardHeader>
          <CardContent>
            <RiskDonut
              data={statusData}
              centerLabel="Total"
              centerValue={String(docs.length)}
            />
            <div className="mt-2 space-y-2">
              {statusData.map((s) => (
                <div key={s.name} className="flex items-center gap-2 text-xs">
                  <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
                  <span className="flex-1 text-muted">{s.name}</span>
                  <span className="font-semibold text-foreground">{s.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Ingestion activity</CardTitle>
            <CardDescription>Documents processed over the last 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            {trendData.length ? (
              <TrendAreaChart data={trendData} height={200} />
            ) : (
              <div className="flex h-[200px] items-center justify-center text-xs text-muted">
                No ingestion activity yet — upload your first documents.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Latest reports</CardTitle>
              <CardDescription>Recently generated due diligence reports</CardDescription>
            </div>
            <Link to="/reports" className="text-xs font-medium text-primary hover:text-primary-hover">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {reports.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-white/10 py-10 text-center">
                <MessagesSquare className="mb-2 h-6 w-6 text-muted/50" />
                <p className="text-xs text-muted">No reports generated yet.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {reports.map((r) => (
                  <Link
                    key={r.id}
                    to={`/reports?open=${r.id}`}
                    className="group flex items-center gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3 transition-colors hover:border-white/10 hover:bg-white/5"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft">
                      <FileText className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-foreground">{r.title}</div>
                      <div className="truncate text-xs text-muted">
                        {r.data.document_count} documents · {new Date(r.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top metrics</CardTitle>
            <CardDescription>From latest report</CardDescription>
          </CardHeader>
          <CardContent>
            {metricData.length ? (
              <MetricBarChart data={metricData} height={200} />
            ) : (
              <div className="flex h-[200px] items-center justify-center text-center text-xs text-muted">
                Generate a report to see key financial metrics.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
