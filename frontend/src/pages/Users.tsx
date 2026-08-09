import * as React from "react";
import {
  UserPlus,
  Loader2,
  Search,
  ShieldCheck,
  ShieldAlert,
  Eye,
  Trash2,
  UserCog,
} from "lucide-react";
import { PageHeader, PageError } from "../components/PageHeader";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../components/ui/tooltip";
import { listUsers, createUser, updateUser, deleteUser, type UserOut } from "../api";
import { useAuth } from "../context/AuthContext";
import { cn } from "../lib/utils";

const ROLE_META: Record<string, { variant: "primary" | "success" | "outline"; icon: React.ReactNode; desc: string }> = {
  admin: { variant: "primary", icon: <ShieldCheck className="h-3 w-3" />, desc: "Full access incl. users & audit" },
  analyst: { variant: "success", icon: <ShieldAlert className="h-3 w-3" />, desc: "Upload, analyze, generate reports" },
  viewer: { variant: "outline", icon: <Eye className="h-3 w-3" />, desc: "Read-only access" },
};

export function Users() {
  const { user: me } = useAuth();
  const [users, setUsers] = React.useState<UserOut[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = React.useState("");
  const [addOpen, setAddOpen] = React.useState(false);
  const [adding, setAdding] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState<UserOut | null>(null);

  const [form, setForm] = React.useState({ username: "", email: "", password: "", role: "analyst" });

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listUsers();
      setUsers(resp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const toggleActive = async (user: UserOut, active: boolean) => {
    try {
      const updated = await updateUser(user.id, { is_active: active });
      setUsers((prev) => prev?.map((u) => (u.id === updated.id ? updated : u)) || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  const changeRole = async (user: UserOut, role: string) => {
    try {
      const updated = await updateUser(user.id, { role });
      setUsers((prev) => prev?.map((u) => (u.id === updated.id ? updated : u)) || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  const addUser = async () => {
    setAdding(true);
    setError(null);
    try {
      const created = await createUser(form);
      setUsers((prev) => (prev ? [created, ...prev] : [created]));
      setAddOpen(false);
      setForm({ username: "", email: "", password: "", role: "analyst" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setAdding(false);
    }
  };

  const removeUser = async () => {
    if (!confirmDelete) return;
    try {
      await deleteUser(confirmDelete.id);
      setUsers((prev) => prev?.filter((u) => u.id !== confirmDelete.id) || null);
      setConfirmDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      setConfirmDelete(null);
    }
  };

  if (loading) {
    return (
      <div className="glass flex h-64 items-center justify-center rounded-xl">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
      </div>
    );
  }

  if (error && !users) return <PageError message={error} onRetry={load} />;

  const filtered = (users || []).filter(
    (u) =>
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage access to your due diligence workspace"
        actions={
          <Button onClick={() => setAddOpen(true)}>
            <UserPlus className="h-4 w-4" /> Add user
          </Button>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg border border-danger/20 bg-danger-soft px-3 py-2 text-xs text-danger">{error}</div>
      )}

      <Card>
        <CardContent className="pt-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="relative w-full max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted/60" />
              <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search users…" className="pl-9" />
            </div>
            <Badge variant="outline" className="ml-auto">
              {filtered.length} users
            </Badge>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="hidden md:table-cell">Status</TableHead>
                  <TableHead className="hidden lg:table-cell">Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((user) => {
                  const meta = ROLE_META[user.role] || ROLE_META.viewer;
                  const isSelf = me?.id === user.id;
                  return (
                    <TableRow key={user.id} className={cn(!user.is_active && "opacity-50")}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-emerald-500 text-xs font-semibold text-white">
                            {user.username.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                              {user.username}
                              {isSelf && <Badge variant="primary" className="text-[9px]">you</Badge>}
                            </div>
                            <div className="text-[11px] text-muted">{user.email}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <Badge variant={meta.variant}>
                                {meta.icon} {user.role}
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent>{meta.desc}</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={user.is_active}
                            onCheckedChange={(v) => void toggleActive(user, v)}
                            disabled={isSelf}
                          />
                          <span className="text-xs text-muted">{user.is_active ? "Active" : "Disabled"}</span>
                        </div>
                      </TableCell>
                      <TableCell className="hidden text-xs text-muted lg:table-cell">
                        {new Date(user.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Select value={user.role} onValueChange={(role) => void changeRole(user, role)} disabled={isSelf}>
                            <SelectTrigger className="h-7 w-28 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">admin</SelectItem>
                              <SelectItem value="analyst">analyst</SelectItem>
                              <SelectItem value="viewer">viewer</SelectItem>
                            </SelectContent>
                          </Select>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7 text-muted hover:text-danger"
                                  disabled={isSelf}
                                  onClick={() => setConfirmDelete(user)}
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>{isSelf ? "You can't remove yourself" : "Remove user"}</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserCog className="h-4 w-4 text-primary" /> Add team member
            </DialogTitle>
            <DialogDescription>
              Create a user account. They'll sign in with these credentials.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="nu-username">Username</Label>
                <Input
                  id="nu-username"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  placeholder="jdoe"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="nu-email">Email</Label>
                <Input
                  id="nu-email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="jdoe@company.com"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="nu-password">Temporary password</Label>
              <Input
                id="nu-password"
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Minimum 8 characters"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Role</Label>
              <Select value={form.role} onValueChange={(role) => setForm({ ...form, role })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin — full access incl. users & audit</SelectItem>
                  <SelectItem value="analyst">Analyst — upload, analyze, report</SelectItem>
                  <SelectItem value="viewer">Viewer — read-only</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => void addUser()}
              disabled={adding || !form.username || !form.email || form.password.length < 8}
            >
              {adding && <Loader2 className="h-4 w-4 animate-spin" />}
              {adding ? "Creating…" : "Create user"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!confirmDelete} onOpenChange={() => setConfirmDelete(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Remove user?</DialogTitle>
            <DialogDescription>
              “{confirmDelete?.username}” will lose access to VeritasIQ immediately.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => void removeUser()}>
              <Trash2 className="h-4 w-4" /> Remove user
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
