import * as React from "react";
import { Send, Search, MessagesSquare, FolderKanban, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { cn } from "../../lib/utils";

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  mode: "chat" | "search";
  onModeChange: (mode: "chat" | "search") => void;
  project: string;
  onProjectChange: (project: string) => void;
  projects: string[];
  busy: boolean;
  error: string | null;
}

export interface ComposerHandle {
  focus: () => void;
}

export const Composer = React.forwardRef<ComposerHandle, ComposerProps>(function Composer(
  {
    value,
    onChange,
    onSubmit,
    mode,
    onModeChange,
    project,
    onProjectChange,
    projects,
    busy,
    error,
  }: ComposerProps,
  ref
) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
  }));

  const resize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  };

  React.useEffect(() => {
    resize();
  }, [value]);

  const submit = () => {
    if (!value.trim() || busy) return;
    onSubmit();
  };

  return (
    <div className="border-t border-white/8 bg-background/60 backdrop-blur-xl">
      <div className="mx-auto max-w-3xl px-4 pb-4 pt-3">
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-3 flex items-start gap-2 rounded-lg border border-danger/25 bg-danger-soft px-3 py-2 text-xs text-danger"
            >
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] shadow-xl shadow-black/20 transition-colors focus-within:border-primary/40 focus-within:bg-white/[0.05]">
          <div className="flex items-center gap-1 border-b border-white/5 px-2 py-1.5">
            <div className="flex rounded-lg bg-white/5 p-0.5">
              <button
                onClick={() => onModeChange("chat")}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                  mode === "chat" ? "bg-primary text-white shadow-sm" : "text-muted hover:text-foreground"
                )}
              >
                <MessagesSquare className="h-3 w-3" /> Chat
              </button>
              <button
                onClick={() => onModeChange("search")}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                  mode === "search" ? "bg-primary text-white shadow-sm" : "text-muted hover:text-foreground"
                )}
              >
                <Search className="h-3 w-3" /> Search
              </button>
            </div>

            <div className="ml-auto flex items-center gap-2">
              {projects.length > 0 && (
                <Select value={project} onValueChange={onProjectChange}>
                  <SelectTrigger className="h-7 gap-1.5 border-white/8 bg-white/5 px-2.5 text-[11px]">
                    <FolderKanban className="h-3 w-3 text-muted" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent align="end">
                    <SelectItem value="__all">All documents</SelectItem>
                    {projects.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>

          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder={
              mode === "chat"
                ? "Ask anything — answers come with verified sources…"
                : "Search across every ingested document…"
            }
            className="max-h-44 w-full resize-none bg-transparent px-4 py-3 text-sm text-foreground placeholder:text-muted/50 focus:outline-none"
          />

          <div className="flex items-center justify-between px-3 pb-2.5">
            <span className="text-[10px] text-muted/50">
              {mode === "chat" ? "Enter to send · Shift+Enter for newline" : "Semantic + keyword retrieval"}
            </span>
            <button
              onClick={submit}
              disabled={!value.trim() || busy}
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-xl transition-all",
                value.trim() && !busy
                  ? "bg-gradient-to-br from-primary to-blue-600 text-white shadow-lg shadow-primary/30 hover:shadow-primary/50 active:scale-95"
                  : "cursor-not-allowed bg-white/5 text-muted/40"
              )}
            >
              {busy ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              ) : mode === "chat" ? (
                <Send className="h-4 w-4" />
              ) : (
                <Search className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        <p className="mt-2 text-center text-[10px] text-muted/40">
          VeritasIQ generates answers only from cited evidence in your uploaded documents.
        </p>
      </div>
    </div>
  );
});
