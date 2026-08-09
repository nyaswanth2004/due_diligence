import * as React from "react";
import { motion } from "framer-motion";
import { Settings as SettingsIcon, Server, Database, Cpu, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { useAuth } from "../context/AuthContext";

export function Settings() {
  const { user } = useAuth();

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Workspace and account settings"
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SettingsIcon className="h-4 w-4 text-primary" /> Account
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <div className="text-xs text-muted">Username</div>
                  <div className="text-sm font-medium text-foreground">{user?.username}</div>
                </div>
                <Separator />
                <div>
                  <div className="text-xs text-muted">Email</div>
                  <div className="text-sm font-medium text-foreground">{user?.email}</div>
                </div>
                <Separator />
                <div>
                  <div className="text-xs text-muted">Role</div>
                  <Badge variant={user?.role === "admin" ? "primary" : user?.role === "analyst" ? "success" : "outline"} className="mt-1 capitalize">
                    {user?.role}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-4 w-4 text-primary" /> System health
              </CardTitle>
              <CardDescription>Backend service and language model status</CardDescription>
            </CardHeader>
            <CardContent>
              <SystemHealth />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-4 w-4 text-primary" /> Data & privacy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-sm font-medium text-foreground">Local-first architecture</div>
                <p className="mt-1 text-xs leading-relaxed text-muted">
                  All documents, embeddings and audit logs are stored in your own backend instance.
                  Query answers are generated only from evidence within your uploaded documents —
                  no data is sent to third parties.
                </p>
              </div>
              <Separator />
              <div>
                <div className="text-sm font-medium text-foreground">Model provider</div>
                <p className="mt-1 text-xs leading-relaxed text-muted">
                  The language model runs via Ollama on your machine (llama3:latest) by default.
                  Configure the provider in <code className="rounded bg-white/5 px-1 py-0.5 text-[11px] text-primary">backend/.env</code>.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function SystemHealth() {
  const [state, setState] = React.useState<"loading" | "ok" | "error">("loading");
  const [detail, setDetail] = React.useState<string>("");

  React.useEffect(() => {
    void (async () => {
      try {
        const resp = await fetch("/api/v1/health");
        const body = await resp.json();
        setState("ok");
        setDetail(`API v${body.version || "1"} · LLM backend: ${body.llm_backend || "unknown"}`);
      } catch {
        setState("error");
      }
    })();
  }, []);

  if (state === "loading") {
    return (
      <div className="flex items-center gap-3 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin text-primary" /> Checking backend health…
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3">
        {state === "ok" ? (
          <CheckCircle2 className="h-5 w-5 shrink-0 text-success" />
        ) : (
          <XCircle className="h-5 w-5 shrink-0 text-danger" />
        )}
        <div>
          <div className="text-sm font-medium text-foreground">
            {state === "ok" ? "Backend online" : "Backend unreachable"}
          </div>
          <div className="text-xs text-muted">{detail}</div>
        </div>
      </div>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex items-center gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3"
      >
        <Cpu className="h-5 w-5 shrink-0 text-primary" />
        <div>
          <div className="text-sm font-medium text-foreground">Grounded generation</div>
          <div className="text-xs text-muted">
            Answers are withheld ("unanswerable") when no supporting evidence exists in your documents.
          </div>
        </div>
      </motion.div>
    </div>
  );
}
