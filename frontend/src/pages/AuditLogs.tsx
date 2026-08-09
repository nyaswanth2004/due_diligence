import * as React from "react";
import {
  Loader2,
  Search,
  User,
  LogIn,
  FilePlus2,
  Trash2,
  FileText,
  MessageSquare,
  ShieldCheck,
  Pencil,
  Globe,
} from "lucide-react";
import { PageHeader, PageError } from "../components/PageHeader";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { listAudit, type AuditEntry } from "../api";

const ACTION_ICONS: Record<string, React.ReactNode> = {
  login: <LogIn className="h-3.5 w-3.5 text-success" />,
  create_document: <FilePlus2 className="h-3.5 w-3.5 text-primary" />,
  delete_document: <Trash2 className="h-3.5 w-3.5 text-danger" />,
  create_user: <User className="h-3.5 w-3.5 text-primary" />,
  update_user: <Pencil className="h-3.5 w-3.5 text-warning" />,
  delete_user: <Trash2 className="h-3.5 w-3.5 text-danger" />,
  generate_report: <FileText className="h-3.5 w-3.5 text-success" />,
  qa_question: <MessageSquare className="h-3.5 w-3.5 text-primary" />,
};

function actionBadge(action: string) {
  const icon = ACTION_ICONS[action];
  const isSystem = action === "system_init" || action === "system_startup";
  return (
    <Badge variant={isSystem ? "outline" : icon ? "default" : "outline"}>
      {icon}
      {action.replace(/_/g, " ")}
    </Badge>
  );
}

export function AuditLogs() {
  const [entries, setEntries] = React.useState<AuditEntry[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [filter, setFilter] = React.useState("");

  const load = React.useCallback(async (action?: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listAudit(action, 200);
      setEntries(resp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit log");
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

  if (error) return <PageError message={error} onRetry={() => load()} />;

  const items = entries || [];

  return (
    <div>
      <PageHeader
        title="Audit Logs"
        description="Immutable trail of every action across your workspace"
        actions={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted/60" />
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter by action…"
                className="w-48 pl-9"
              />
            </div>
          </div>
        }
      />

      <Card>
        <CardContent className="pt-5">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Action</TableHead>
                  <TableHead className="hidden sm:table-cell">User</TableHead>
                  <TableHead className="hidden md:table-cell">Resource</TableHead>
                  <TableHead className="hidden lg:table-cell">IP address</TableHead>
                  <TableHead>Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items
                  .filter((e) => e.action.toLowerCase().includes(filter.toLowerCase()))
                  .map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>{actionBadge(entry.action)}</TableCell>
                      <TableCell className="hidden sm:table-cell">
                        <div className="flex items-center gap-1.5 text-xs text-foreground">
                          <User className="h-3 w-3 text-muted" />
                          {entry.username || <span className="text-muted">system</span>}
                        </div>
                      </TableCell>
                      <TableCell className="hidden text-xs text-muted md:table-cell">
                        {entry.resource_type}
                        {entry.resource_id && <span className="text-muted/60"> · {entry.resource_id.slice(0, 8)}…</span>}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        <span className="inline-flex items-center gap-1 text-xs text-muted">
                          <Globe className="h-3 w-3" />
                          {entry.ip_address}
                        </span>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs text-muted">
                        {new Date(entry.created_at).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="mt-4 flex items-center gap-2 text-[11px] text-muted/70">
        <ShieldCheck className="h-3.5 w-3.5 text-success" />
        Audit entries are written server-side and include user, resource, IP and timestamp for every significant action.
      </div>
    </div>
  );
}
