import * as React from "react";
import { motion } from "framer-motion";
import { useNavigate, useLocation } from "react-router-dom";
import { Sparkles, ShieldCheck, Search, FileText, Loader2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useAuth } from "../context/AuthContext";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  const from = (location.state as { from?: string } | null)?.from || "/";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-32 top-0 h-96 w-96 rounded-full bg-primary/20 blur-[120px]" />
        <div className="absolute -right-32 bottom-0 h-96 w-96 rounded-full bg-emerald-500/10 blur-[120px]" />
      </div>

      <div className="grid w-full max-w-4xl gap-10 lg:grid-cols-2 lg:items-center">
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35 }}
          className="hidden lg:block"
        >
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-emerald-500 shadow-xl shadow-primary/30">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="text-xl font-bold text-foreground">
                Veritas<span className="text-primary">IQ</span>
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-muted">
                Due Diligence Copilot
              </div>
            </div>
          </div>
          <h1 className="mb-3 text-3xl font-bold leading-tight text-foreground">
            AI-powered financial due diligence, <span className="text-gradient">grounded in your documents.</span>
          </h1>
          <p className="mb-8 text-sm leading-relaxed text-muted">
            VeritasIQ ingests financial statements, scanned reports and spreadsheets, then answers
            questions with verified citations — never hallucinated numbers.
          </p>
          <div className="space-y-3">
            {[
              { icon: FileText, title: "Document intelligence", desc: "PDF, OCR & spreadsheet ingestion with page-level provenance" },
              { icon: Search, title: "Hybrid retrieval", desc: "Semantic + keyword search over every ingested document" },
              { icon: ShieldCheck, title: "Every answer verified", desc: "Citations traceable to source pages, sections and files" },
            ].map((f) => (
              <div key={f.title} className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-soft">
                  <f.icon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <div className="text-sm font-medium text-foreground">{f.title}</div>
                  <div className="text-xs text-muted">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
        >
          <div className="glass-strong rounded-2xl p-8 shadow-2xl shadow-black/40">
            <div className="mb-6 lg:hidden">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-emerald-500">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div className="text-base font-bold text-foreground">
                  Veritas<span className="text-primary">IQ</span>
                </div>
              </div>
            </div>

            <h2 className="text-lg font-semibold text-foreground">Welcome back</h2>
            <p className="mb-6 text-sm text-muted">Sign in to your workspace</p>

            <form onSubmit={submit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  autoComplete="username"
                  placeholder="you@company.com"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              {error && (
                <div className="rounded-lg border border-danger/20 bg-danger-soft px-3 py-2 text-xs text-danger">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                {loading ? "Signing in…" : "Sign in"}
              </Button>
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
