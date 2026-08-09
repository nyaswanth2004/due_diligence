import * as React from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FolderKanban,
  FolderOpen,
  Plus,
  FileText,
  ArrowRight,
  Trash2,
  Pencil,
  Check,
  X,
  Loader2,
} from "lucide-react";
import { PageHeader, PageError, EmptyState } from "../components/PageHeader";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../components/ui/dialog";
import { listDocuments, type DocumentItem } from "../api";
import { groupDocuments, renameProject, assignProject } from "../lib/projects";

const PROJECT_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#06B6D4", "#EF4444"];

export function Projects() {
  const [docs, setDocs] = React.useState<DocumentItem[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [newProject, setNewProject] = React.useState("");
  const [renameTarget, setRenameTarget] = React.useState<string | null>(null);
  const [renameValue, setRenameValue] = React.useState("");
  const [confirmDelete, setConfirmDelete] = React.useState<string | null>(null);

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

  if (loading) {
    return (
      <div className="glass flex h-64 items-center justify-center rounded-xl">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
      </div>
    );
  }

  if (error) return <PageError message={error} onRetry={load} />;

  const groups = groupDocuments(docs || []);
  const hasUnassigned = groups.some((g) => g.name === "Unassigned");

  const createProject = () => {
    const name = newProject.trim();
    if (!name) return;
    if (!groups.some((g) => g.name === name)) {
      groups.push({ name, documents: [] });
    }
    setNewProject("");
  };

  const handleRename = () => {
    if (!renameTarget || !renameValue.trim() || renameValue === renameTarget) {
      setRenameTarget(null);
      return;
    }
    renameProject(renameTarget, renameValue.trim());
    setRenameTarget(null);
    setDocs([...docs!]);
  };

  const handleDelete = (name: string) => {
    for (const d of groups.find((g) => g.name === name)?.documents || []) {
      assignProject(d.id, "Unassigned");
    }
    setConfirmDelete(null);
    setDocs([...docs!]);
  };

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Group your documents into due diligence engagements"
        actions={
          <div className="flex gap-2">
            <Input
              value={newProject}
              onChange={(e) => setNewProject(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createProject()}
              placeholder="New project name…"
              className="w-48 sm:w-60"
            />
            <Button onClick={createProject} disabled={!newProject.trim()}>
              <Plus className="h-4 w-4" /> Create
            </Button>
          </div>
        }
      />

      {groups.length === 0 ? (
        <EmptyState
          icon={<FolderKanban className="h-6 w-6" />}
          title="No projects yet"
          description="Create a project above, or upload documents and assign them to projects from the Document Upload page."
          action={
            <Link to="/documents">
              <Button size="sm">
                <Plus className="h-4 w-4" /> Upload documents
              </Button>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence>
            {groups.map((group, index) => {
              const color = PROJECT_COLORS[index % PROJECT_COLORS.length];
              return (
                <motion.div
                  key={group.name}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ duration: 0.2 }}
                >
                  <Card className="h-full p-5">
                    <div className="mb-4 flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className="flex h-10 w-10 items-center justify-center rounded-xl"
                          style={{ background: `${color}22`, color }}
                        >
                          {group.documents.length ? <FolderOpen className="h-5 w-5" /> : <FolderKanban className="h-5 w-5" />}
                        </div>
                        <div>
                          {renameTarget === group.name ? (
                            <div className="flex items-center gap-1">
                              <Input
                                autoFocus
                                value={renameValue}
                                onChange={(e) => setRenameValue(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && handleRename()}
                                className="h-7 w-36 text-sm"
                              />
                              <Button variant="ghost" size="icon" className="h-7 w-7 text-success" onClick={handleRename}>
                                <Check className="h-3.5 w-3.5" />
                              </Button>
                              <Button variant="ghost" size="icon" className="h-7 w-7 text-muted" onClick={() => setRenameTarget(null)}>
                                <X className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm font-semibold text-foreground">{group.name}</h3>
                              {group.name === "Unassigned" && hasUnassigned && (
                                <Badge variant="warning">unassigned</Badge>
                              )}
                            </div>
                          )}
                          <div className="text-xs text-muted">{group.documents.length} documents</div>
                        </div>
                      </div>
                      {group.name !== "Unassigned" && (
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted hover:text-primary"
                            onClick={() => {
                              setRenameTarget(group.name);
                              setRenameValue(group.name);
                            }}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted hover:text-danger"
                            onClick={() => setConfirmDelete(group.name)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      {group.documents.slice(0, 4).map((doc) => (
                        <div key={doc.id} className="flex items-center gap-2 rounded-lg bg-white/[0.02] px-2.5 py-2">
                          <FileText className="h-3.5 w-3.5 shrink-0 text-muted" />
                          <span className="truncate text-xs text-foreground">{doc.filename}</span>
                          <Badge
                            variant={doc.status === "ready" ? "success" : doc.status === "failed" ? "danger" : "primary"}
                            className="ml-auto"
                          >
                            {doc.status}
                          </Badge>
                        </div>
                      ))}
                      {group.documents.length > 4 && (
                        <div className="px-2.5 pt-1 text-[11px] text-muted">
                          +{group.documents.length - 4} more documents
                        </div>
                      )}
                      {group.documents.length === 0 && (
                        <div className="rounded-lg border border-dashed border-white/10 px-2.5 py-3 text-center text-[11px] text-muted">
                          No documents assigned yet
                        </div>
                      )}
                    </div>

                    {group.documents.length > 0 && (
                      <Link
                        to={`/chat?project=${encodeURIComponent(group.name)}`}
                        className="mt-4 flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary-hover"
                      >
                        Ask about this project <ArrowRight className="h-3 w-3" />
                      </Link>
                    )}
                  </Card>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}

      <Dialog open={!!confirmDelete} onOpenChange={() => setConfirmDelete(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete project?</DialogTitle>
            <DialogDescription>
              Documents in “{confirmDelete}” will be moved to Unassigned. No files are deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => handleDelete(confirmDelete!)}>
              <Trash2 className="h-4 w-4" /> Delete project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
