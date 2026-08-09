import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Search,
  FileText,
  Loader2,
  BookOpenCheck,
  Hash,
  ChevronRight,
  FolderKanban,
} from "lucide-react";
import type { EvidenceChunk } from "../../api";
import { cn } from "../../lib/utils";

interface EvidencePanelProps {
  open: boolean;
  onClose: () => void;
  activeChunks: EvidenceChunk[];
  project: string;
  onProjectChange: (p: string) => void;
  projects: string[];
  onSearchQuery: (query: string) => Promise<EvidenceChunk[]>;
}

export function EvidencePanel({
  open,
  onClose,
  activeChunks,
  project,
  onProjectChange,
  projects,
  onSearchQuery,
}: EvidencePanelProps) {
  const [query, setQuery] = React.useState("");
  const [results, setResults] = React.useState<EvidenceChunk[]>([]);
  const [searching, setSearching] = React.useState(false);
  const [selected, setSelected] = React.useState<EvidenceChunk | null>(null);
  const searchTimeout = React.useRef<number | null>(null);

  React.useEffect(() => {
    if (activeChunks.length > 0) setSelected(activeChunks[0]);
  }, [activeChunks]);

  const runSearch = async (value: string) => {
    setSearching(true);
    try {
      const resp = await onSearchQuery(value);
      setResults(resp);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const debouncedSearch = (value: string) => {
    setQuery(value);
    if (searchTimeout.current) window.clearTimeout(searchTimeout.current);
    searchTimeout.current = window.setTimeout(() => {
      if (value.trim().length >= 2) void runSearch(value.trim());
      else setResults([]);
    }, 400);
  };

  React.useEffect(() => () => {
    if (searchTimeout.current) window.clearTimeout(searchTimeout.current);
  }, []);

  const renderChunk = (chunk: EvidenceChunk, isSelected: boolean) => (
    <div
      key={chunk.chunk_id}
      onClick={() => setSelected(chunk)}
      className={cn(
        "cursor-pointer rounded-lg border p-2.5 transition-all",
        isSelected
          ? "border-primary/40 bg-primary-soft"
          : "border-white/8 bg-white/[0.02] hover:border-white/15 hover:bg-white/[0.04]"
      )}
    >
      <div className="flex items-center gap-1.5">
        <FileText className="h-3 w-3 shrink-0 text-primary" />
        <span className="truncate text-[11px] font-medium text-foreground">{chunk.filename}</span>
        <span className="ml-auto flex shrink-0 items-center gap-0.5 text-[10px] text-muted">
          <Hash className="h-2.5 w-2.5" />
          p{chunk.page_number}
        </span>
      </div>
      <p className="mt-1.5 line-clamp-3 text-[11px] leading-relaxed text-muted">{chunk.content}</p>
      <div className="mt-1.5 flex items-center gap-1.5">
        <span className="truncate rounded bg-white/5 px-1.5 py-0.5 text-[9px] text-muted">{chunk.section || "Excerpt"}</span>
        <span className="ml-auto text-[9px] font-medium text-primary">
          {Math.round((chunk.score || 0) * 100)}%
        </span>
      </div>
    </div>
  );

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden animate-fade-in" onClick={onClose} />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 right-0 z-50 flex w-[340px] max-w-[85vw] flex-col border-l border-white/8 bg-surface/95 backdrop-blur-2xl transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0",
          open ? "translate-x-0" : "translate-x-[340px]"
        )}
      >
        <div className="flex items-center justify-between border-b border-white/8 p-3">
          <div className="flex items-center gap-2 px-1">
            <BookOpenCheck className="h-4 w-4 text-primary" />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-muted/70">
              Evidence explorer
            </span>
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-muted hover:bg-white/10 hover:text-foreground lg:hidden">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="border-b border-white/8 space-y-2.5 p-3">
          <div className="flex items-center gap-2 rounded-lg border border-white/8 bg-white/5 px-2.5 py-2">
            <Search className="h-3.5 w-3.5 shrink-0 text-muted" />
            <input
              value={query}
              onChange={(e) => debouncedSearch(e.target.value)}
              placeholder="Live search documents…"
              className="w-full bg-transparent text-xs text-foreground placeholder:text-muted/50 focus:outline-none"
            />
            {searching && <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />}
          </div>

          {projects.length > 0 && (
            <div className="flex items-center gap-2">
              <FolderKanban className="h-3.5 w-3.5 shrink-0 text-muted/60" />
              <div className="flex flex-wrap gap-1">
                {["__all", ...projects].map((p) => (
                  <button
                    key={p}
                    onClick={() => onProjectChange(p)}
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors",
                      project === p
                        ? "bg-primary text-white"
                        : "bg-white/5 text-muted hover:text-foreground"
                    )}
                  >
                    {p === "__all" ? "All docs" : p}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-3 scroll-thin">
          {query.trim().length >= 2 ? (
            <div className="space-y-2">
              <div className="flex items-center gap-1 px-1 text-[10px] font-semibold uppercase tracking-widest text-muted/50">
                <Search className="h-3 w-3" /> Search results
                {results.length > 0 && <span className="text-primary">{results.length}</span>}
              </div>
              {searching ? (
                <div className="space-y-2">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="h-24 animate-pulse rounded-lg bg-white/[0.05]" />
                  ))}
                </div>
              ) : results.length > 0 ? (
                <div className="space-y-2">
                  <AnimatePresence>
                    {results.map((r) => (
                      <motion.div key={r.chunk_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                        {renderChunk(r, selected?.chunk_id === r.chunk_id)}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              ) : (
                <p className="px-2 py-6 text-center text-[11px] text-muted/60">No matches found.</p>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-1 px-1 text-[10px] font-semibold uppercase tracking-widest text-muted/50">
                <BookOpenCheck className="h-3 w-3" /> Cited passages
                {activeChunks.length > 0 && <span className="text-primary">{activeChunks.length}</span>}
              </div>
              {activeChunks.length > 0 ? (
                <div className="space-y-2">
                  {activeChunks.map((c) => renderChunk(c, selected?.chunk_id === c.chunk_id))}
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft">
                    <ChevronRight className="h-5 w-5 text-primary" />
                  </div>
                  <p className="text-xs leading-relaxed text-muted">
                    Click a source chip on any answer to inspect the exact passage, or search the corpus
                    to explore evidence.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
