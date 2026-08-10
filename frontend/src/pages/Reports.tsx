import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "react-router-dom";
import {
  FileText,
  FilePlus2,
  Loader2,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  ListChecks,
  Trash2,
} from "lucide-react";
import { PageHeader, PageError, EmptyState } from "../components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../components/ui/dialog";
import { listReports, getReport, generateReport, deleteReport, listDocuments, type ReportItem, type ReportPayload, type RatioRow, type RedFlagRow } from "../api";
import { isAnalyst } from "../auth";
import { cn } from "../lib/utils";

export function Reports() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [reports, setReports] = React.useState<ReportItem[] | null>(null);
  const [active, setActive] = React.useState<ReportItem | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [genOpen, setGenOpen] = React.useState(false);
  const [readyDocs, setReadyDocs] = React.useState<{ id: string; filename: string }[]>([]);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [generating, setGenerating] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState<ReportItem | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listReports();
      setReports(resp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  React.useEffect(() => {
    const openId = searchParams.get("open");
    if (openId && reports) {
      const found = reports.find((r) => r.id === openId);
      if (found) setActive(found);
      const params = new URLSearchParams(searchParams);
      params.delete("open");
      setSearchParams(params, { replace: true });
    }
  }, [searchParams, reports, setSearchParams]);

  React.useEffect(() => {
    if (genOpen) {
      void (async () => {
        const resp = await listDocuments();
        setReadyDocs(resp.items.filter((d) => d.status === "ready").map((d) => ({ id: d.id, filename: d.filename })));
        setSelected(new Set());
      })();
    }
  }, [genOpen]);

  const openDetail = async (id: string) => {
    try {
      const item = await getReport(id);
      setActive(item);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    }
  };

  const generate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const payload: ReportPayload = await generateReport(Array.from(selected));
      const resp = await listReports();
      setReports(resp.items);
      setGenOpen(false);
      const newest = resp.items.find((r) => r.data === payload || r.created_at === resp.items[0]?.created_at) || resp.items[0];
      if (newest) setActive(newest);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const removeReport = async () => {
    if (!confirmDelete) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteReport(confirmDelete.id);
      setActive((prev) => (prev?.id === confirmDelete.id ? null : prev));
      setReports((prev) => prev?.filter((r) => r.id !== confirmDelete.id) || null);
      setConfirmDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      setConfirmDelete(null);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="glass flex h-64 items-center justify-center rounded-xl">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
      </div>
    );
  }

  if (error && !reports) return <PageError message={error} onRetry={load} />;

  const items = reports || [];

  if (active) {
    return <ReportDetail report={active} onBack={() => setActive(null)} />;
  }

  return (
    <div>
      <PageHeader
        title="Reports"
        description="Generated due diligence reports with executive summaries and financial analysis"
        actions={
          isAnalyst() ? (
            <Button onClick={() => setGenOpen(true)}>
              <FilePlus2 className="h-4 w-4" /> Generate report
            </Button>
          ) : undefined
        }
      />

      {error && (
        <div className="mb-4 rounded-lg border border-danger/20 bg-danger-soft px-3 py-2 text-xs text-danger">{error}</div>
      )}

      {items.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-6 w-6" />}
          title="No reports generated"
          description="Generate a multi-agent due diligence report from your processed documents."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence>
            {items.map((r) => (
              <motion.div
                key={r.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={() => void openDetail(r.id)}
                className="group cursor-pointer text-left"
              >
                <Card className="h-full p-5 transition-all hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex items-center gap-1.5 text-[11px] text-muted">
                      <Calendar className="h-3 w-3" />
                      {new Date(r.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <h3 className="mb-1 text-sm font-semibold text-foreground">{r.title}</h3>
                  <p className="mb-4 line-clamp-3 text-xs leading-relaxed text-muted">{r.summary}</p>
                  <div className="flex items-center justify-between">
                    <Badge variant="outline">{r.data.document_count} documents</Badge>
                    <div className="flex items-center gap-2">
                      {isAnalyst() && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-danger"
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmDelete(r);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      <span className="text-[11px] font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                        Open report →
                      </span>
                    </div>
                  </div>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      <Dialog open={genOpen} onOpenChange={setGenOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate due diligence report</DialogTitle>
            <DialogDescription>Select processed documents to include in the multi-agent analysis.</DialogDescription>
          </DialogHeader>
          {readyDocs.length === 0 ? (
            <p className="rounded-lg border border-dashed border-white/10 p-4 text-center text-xs text-muted">
              No processed documents available. Upload and process documents first.
            </p>
          ) : (
            <div className="max-h-72 space-y-1.5 overflow-y-auto pr-1 scroll-thin">
              <button
                onClick={() => setSelected(new Set(readyDocs.map((d) => d.id)))}
                className="mb-2 rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-muted hover:text-foreground"
              >
                Select all
              </button>
              {readyDocs.map((d) => (
                <label
                  key={d.id}
                  className={cn(
                    "flex cursor-pointer items-center gap-2.5 rounded-lg border p-2.5 transition-colors",
                    selected.has(d.id) ? "border-primary/40 bg-primary-soft" : "border-white/8 bg-white/[0.02] hover:bg-white/5"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(d.id)}
                    onChange={() => {
                      const next = new Set(selected);
                      if (next.has(d.id)) next.delete(d.id);
                      else next.add(d.id);
                      setSelected(next);
                    }}
                    className="accent-blue-500"
                  />
                  <FileText className="h-4 w-4 shrink-0 text-muted" />
                  <span className="truncate text-xs text-foreground">{d.filename}</span>
                </label>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button variant="secondary" onClick={() => setGenOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void generate()} disabled={generating || selected.size === 0}>
              {generating && <Loader2 className="h-4 w-4 animate-spin" />}
              {generating ? "Generating…" : `Generate (${selected.size})`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!confirmDelete} onOpenChange={() => !deleting && setConfirmDelete(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete report?</DialogTitle>
            <DialogDescription>
              “{confirmDelete?.title}” and its generated data will be permanently deleted. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setConfirmDelete(null)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => void removeReport()} disabled={deleting}>
              {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
              <Trash2 className="h-4 w-4" /> {deleting ? "Deleting…" : "Delete report"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ReportDetail({ report, onBack }: { report: ReportItem; onBack: () => void }) {
  const payload = report.data;
  const ratios = (payload.sections.financial_analysis || []).filter((r): r is RatioRow => "formula" in r);
  const redFlags: RedFlagRow[] = payload.sections.risk || [];
  const metrics = Object.entries(payload.financial_metrics);

  return (
    <div>
      <button onClick={onBack} className="mb-4 flex items-center gap-1.5 text-xs font-medium text-muted transition-colors hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to reports
      </button>

      <div className="mb-6">
        <h1 className="text-xl font-bold tracking-tight text-foreground">{payload.title}</h1>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
          <Calendar className="h-3.5 w-3.5" />
          Generated {new Date(payload.generated_on).toLocaleString()}
          <Badge variant="outline" className="ml-1">
            {payload.document_count} documents
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Executive summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-foreground">{payload.executive_summary}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Key financial metrics</CardTitle>
            <CardDescription>With prior-period comparison</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {metrics.map(([key, m]) => (
                <div key={key} className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div>
                    <div className="text-xs font-medium text-muted">{m.label}</div>
                    <div className="text-[10px] text-muted/60">
                      {m.filename} · p{m.page}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-foreground">{formatNumber(m.value)}</div>
                    {m.prior_value !== null && (
                      <div
                        className={cn(
                          "flex items-center justify-end gap-1 text-[11px]",
                          m.value > m.prior_value ? "text-success" : m.value < m.prior_value ? "text-danger" : "text-muted"
                        )}
                      >
                        {m.value > m.prior_value ? <TrendingUp className="h-3 w-3" /> : m.value < m.prior_value ? <TrendingDown className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
                        {m.value > m.prior_value ? "+" : ""}
                        {formatNumber(m.value - m.prior_value)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {metrics.length === 0 && <p className="text-xs text-muted">No financial metrics extracted.</p>}
            </div>
          </CardContent>
        </Card>
      </div>

      {ratios.length > 0 && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ListChecks className="h-4 w-4 text-primary" /> Financial ratios
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {ratios.map((r, i) => (
                <div key={i} className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-medium text-foreground">{r.name}</div>
                    <Badge variant={r.risk_level === "high" ? "danger" : r.risk_level === "medium" ? "warning" : "success"}>
                      {r.risk_level}
                    </Badge>
                  </div>
                  <div className="mt-1 text-lg font-bold text-foreground">{formatNumber(r.value)}</div>
                  <div className="text-[10px] text-muted">{r.formula}</div>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-muted">{r.interpretation}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {redFlags.length > 0 && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-warning">Red flags ({redFlags.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {redFlags.map((f, i) => (
                <div key={i} className="flex items-start gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <Badge variant={f.severity === "high" ? "danger" : f.severity === "medium" ? "warning" : "primary"} className="mt-0.5 shrink-0 capitalize">
                    {f.severity}
                  </Badge>
                  <div>
                    <div className="text-sm font-medium text-foreground">{f.finding}</div>
                    <div className="text-xs text-muted">{f.evidence}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function formatNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return (value / 1_000_000_000).toFixed(2) + "B";
  if (abs >= 1_000_000) return (value / 1_000_000).toFixed(2) + "M";
  if (abs >= 1_000) return (value / 1_000).toFixed(2) + "K";
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
