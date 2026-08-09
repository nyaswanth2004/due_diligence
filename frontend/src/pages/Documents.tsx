import * as React from "react";
import { Link } from "react-router-dom";
import {
  UploadCloud,
  FileText,
  FileSpreadsheet,
  ScanLine,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  X,
  FolderPlus,
} from "lucide-react";
import { PageHeader, PageError, EmptyState } from "../components/PageHeader";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Progress } from "../components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../components/ui/tooltip";
import { listDocuments, uploadDocument, deleteDocument, type DocumentItem } from "../api";
import { isAnalyst } from "../auth";
import { assignProject, projectFor, allProjectNames } from "../lib/projects";
import { cn } from "../lib/utils";

const DOC_ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText className="h-4 w-4 text-danger" />,
  excel: <FileSpreadsheet className="h-4 w-4 text-success" />,
  image: <ScanLine className="h-4 w-4 text-primary" />,
};

const STATUS_META: Record<DocumentItem["status"], { label: string; variant: "success" | "primary" | "warning" | "danger" }> = {
  ready: { label: "Ready", variant: "success" },
  processing: { label: "Processing", variant: "primary" },
  pending: { label: "Queued", variant: "warning" },
  failed: { label: "Failed", variant: "danger" },
};

export function Documents() {
  const canUpload = isAnalyst();
  const [docs, setDocs] = React.useState<DocumentItem[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [filter, setFilter] = React.useState("");
  const [dragOver, setDragOver] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [selectedProject, setSelectedProject] = React.useState<string>("");

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listDocuments();
      setDocs(resp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const uploadFiles = async (files: FileList | File[]) => {
    setUploading(true);
    setError(null);
    try {
      const arr = Array.from(files);
      for (const file of arr) {
        const doc = await uploadDocument(file);
        if (selectedProject) assignProject(doc.id, selectedProject);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const remove = async (doc: DocumentItem) => {
    try {
      await deleteDocument(doc.id);
      setDocs((prev) => prev?.filter((d) => d.id !== doc.id) || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
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

  const all = docs || [];
  const filtered = all.filter((d) => d.filename.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div>
      <PageHeader
        title="Document Upload"
        description="Upload financial documents and group them into projects for analysis"
      />

      {error && docs && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-danger/20 bg-danger-soft px-3 py-2 text-xs text-danger">
          {error}
          <button onClick={() => setError(null)}>
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="pt-5">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto]">
              <label
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  if (canUpload) void uploadFiles(e.dataTransfer.files);
                }}
                className={cn(
                  "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
                  dragOver ? "border-primary bg-primary-soft" : "border-white/12 bg-white/[0.02] hover:border-primary/50 hover:bg-primary-soft/40"
                )}
              >
                <input
                  type="file"
                  multiple
                  accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg,.tiff"
                  disabled={!canUpload}
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files?.length) void uploadFiles(e.target.files);
                    e.target.value = "";
                  }}
                />
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary-soft text-primary">
                  {uploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <UploadCloud className="h-5 w-5" />}
                </div>
                <div className="text-sm font-medium text-foreground">
                  {uploading ? "Uploading documents…" : "Drop files here or click to browse"}
                </div>
                <div className="mt-1 text-xs text-muted">
                  PDF · Excel (XLSX/XLS) · scanned images (PNG, JPG, TIFF)
                </div>
                {!canUpload && (
                  <Badge variant="warning" className="mt-3">
                    Uploads require analyst access
                  </Badge>
                )}
              </label>

              <div className="flex flex-col gap-2">
                <div className="text-xs font-medium text-muted">Group into project</div>
                <Select value={selectedProject} onValueChange={setSelectedProject}>
                  <SelectTrigger className="w-full sm:w-52">
                    <SelectValue placeholder="Select project" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none">No project (unassigned)</SelectItem>
                    {allProjectNames()
                      .filter((n) => n !== "Unassigned")
                      .map((name) => (
                        <SelectItem key={name} value={name}>
                          {name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <Link to="/projects">
                  <Button variant="secondary" size="sm" className="w-full sm:w-52">
                    <FolderPlus className="h-4 w-4" /> Manage in Projects
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-5">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-success-soft text-success">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-lg font-bold text-foreground">{all.filter((d) => d.status === "ready").length}</div>
                  <div className="text-[11px] text-muted">Ready for analysis</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft text-primary">
                  <RefreshCw className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-lg font-bold text-foreground">{all.filter((d) => d.status === "processing" || d.status === "pending").length}</div>
                  <div className="text-[11px] text-muted">Queued / processing</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-danger-soft text-danger">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-lg font-bold text-foreground">{all.filter((d) => d.status === "failed").length}</div>
                  <div className="text-[11px] text-muted">Failed to process</div>
                </div>
              </div>
              <Progress
                value={all.length ? (all.filter((d) => d.status === "ready").length / all.length) * 100 : 0}
                className="mt-2"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardContent className="pt-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <h3 className="text-sm font-semibold text-foreground">
              Documents <span className="ml-1 text-muted">({filtered.length})</span>
            </h3>
            <div className="relative sm:ml-auto sm:w-64">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted/60" />
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter documents…"
                className="pl-9"
              />
            </div>
          </div>

          {filtered.length === 0 ? (
            <EmptyState
              icon={<FileText className="h-6 w-6" />}
              title="No documents yet"
              description="Upload financial statements, balance sheets, income statements or scanned reports to begin."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="hidden md:table-cell">Pages</TableHead>
                    <TableHead className="hidden lg:table-cell">Chunks</TableHead>
                    <TableHead className="hidden sm:table-cell">Project</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((doc) => {
                    const meta = STATUS_META[doc.status];
                    return (
                      <TableRow key={doc.id}>
                        <TableCell>
                          <div className="flex items-center gap-2.5">
                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/5">
                              {DOC_ICONS[doc.doc_type] || <FileText className="h-4 w-4 text-muted" />}
                            </div>
                            <div className="min-w-0">
                              <div className="max-w-[220px] truncate text-sm font-medium text-foreground">{doc.filename}</div>
                              <div className="text-[11px] text-muted">{new Date(doc.created_at).toLocaleString()}</div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{doc.doc_type}</Badge>
                        </TableCell>
                        <TableCell className="hidden text-muted md:table-cell">{doc.page_count}</TableCell>
                        <TableCell className="hidden text-muted lg:table-cell">{doc.chunk_count}</TableCell>
                        <TableCell className="hidden sm:table-cell">
                          <Select
                            value={projectFor(doc.id)}
                            onValueChange={(name) => {
                              assignProject(doc.id, name);
                              setDocs([...all]);
                            }}
                          >
                            <SelectTrigger className="h-7 w-36 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {allProjectNames().map((name) => (
                                <SelectItem key={name} value={name}>
                                  {name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger>
                                <Badge variant={meta.variant}>
                                  {doc.status === "processing" || doc.status === "pending" ? (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  ) : doc.status === "failed" ? (
                                    <AlertTriangle className="h-3 w-3" />
                                  ) : (
                                    <CheckCircle2 className="h-3 w-3" />
                                  )}
                                  {meta.label}
                                </Badge>
                              </TooltipTrigger>
                              {doc.error_message && <TooltipContent>{doc.error_message}</TooltipContent>}
                            </Tooltip>
                          </TooltipProvider>
                        </TableCell>
                        <TableCell className="text-right">
                          {canUpload && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 text-muted hover:text-danger"
                                    onClick={() => void remove(doc)}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Delete document</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
