import * as React from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Menu,
  BookOpenCheck,
  Sparkles,
  MessagesSquare,
  ShieldCheck,
  FileSearch,
  Hash,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import { Composer, type ComposerHandle } from "../components/chat/Composer";
import { MessageBubble } from "../components/chat/MessageBubble";
import { TypingIndicator } from "../components/chat/TypingIndicator";
import { ConversationHistory } from "../components/chat/ConversationHistory";
import { EvidencePanel } from "../components/chat/EvidencePanel";
import { Badge } from "../components/ui/badge";
import {
  saveConversation,
  deleteConversation,
  clearConversations,
  loadConversations,
  uid,
  type Conversation,
  type ChatMessage,
} from "../lib/conversations";
import { groupDocuments } from "../lib/projects";
import { askQuestion, search, listDocuments, type EvidenceChunk } from "../api";

const SUGGESTIONS = [
  {
    icon: FileSearch,
    title: "Financial performance",
    prompt: "What was the company's net income and revenue trend over the last three years?",
  },
  {
    icon: ShieldCheck,
    title: "Risk scan",
    prompt: "Highlight any red flags or unusual items in the financial statements.",
  },
  {
    icon: Hash,
    title: "Key ratios",
    prompt: "Calculate the liquidity, solvency and profitability ratios from the documents.",
  },
  {
    icon: MessagesSquare,
    title: "Compliance",
    prompt: "Which standard due diligence documents are present, and which are missing?",
  },
];

export function Chat() {
  const [searchParams] = useSearchParams();

  const [conversations, setConversations] = React.useState<Conversation[]>(() => loadConversations());
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [input, setInput] = React.useState("");
  const [mode, setMode] = React.useState<"chat" | "search">("chat");
  const [project, setProject] = React.useState("__all");
  const [projectNames, setProjectNames] = React.useState<string[]>([]);
  const [thinking, setThinking] = React.useState(false);
  const [searching, setSearching] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [searchResults, setSearchResults] = React.useState<EvidenceChunk[]>([]);
  const [evidenceChunks, setEvidenceChunks] = React.useState<EvidenceChunk[]>([]);
  const [historyOpen, setHistoryOpen] = React.useState(false);
  const [evidenceOpen, setEvidenceOpen] = React.useState(false);

  const bottomRef = React.useRef<HTMLDivElement>(null);
  const composerRef = React.useRef<ComposerHandle | null>(null);

  const active = conversations.find((c) => c.id === activeId) || null;

  React.useEffect(() => {
    void (async () => {
      try {
        const resp = await listDocuments();
        setProjectNames(groupDocuments(resp.items).filter((g) => g.name !== "Unassigned").map((g) => g.name));
      } catch {
        /* non-critical */
      }
    })();
  }, []);

  React.useEffect(() => {
    const initRef = sessionStorage.getItem("veritasiq_chat_init");
    if (initRef === "1") return;
    sessionStorage.setItem("veritasiq_chat_init", "1");
    const q = searchParams.get("q");
    const convId = searchParams.get("c");
    const proj = searchParams.get("project");
    if (proj) setProject(proj);
    if (convId) {
      setActiveId(convId);
      setHistoryOpen(false);
    } else if (q) {
      setInput(q);
      setActiveId(null);
      window.setTimeout(() => submitMessage(q), 50);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [active?.messages.length, thinking]);

  const persist = React.useCallback((convs: Conversation[]) => {
    setConversations(convs);
  }, []);

  const updateActive = React.useCallback(
    (conv: Conversation) => {
      const convs = saveConversation(conv);
      persist(convs);
      return convs;
    },
    [persist]
  );

  const runChat = async (query: string) => {
    setThinking(true);
    setError(null);
    let conv: Conversation;

    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: query,
      createdAt: new Date().toISOString(),
    };

    if (active) {
      conv = {
        ...active,
        updatedAt: new Date().toISOString(),
        messages: [...active.messages, userMsg],
      };
    } else {
      conv = {
        id: uid(),
        title: query.length > 48 ? query.slice(0, 48) + "…" : query,
        project,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [userMsg],
      };
    }
    const convs = updateActive(conv);
    setActiveId(conv.id);

    try {
      const history = conv.messages.slice(0, -1).map((m) => ({ role: m.role, content: m.content }));
      const projectDocs =
        project !== "__all"
          ? groupDocuments((await (await listDocuments()).items).filter((d) => d.status === "ready"))
              .find((g) => g.name === project)
              ?.documents.map((d) => d.id)
          : undefined;

      const resp = await askQuestion(query, projectDocs, history);
      const assistantMsg: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: resp.answer,
        citations: resp.citations,
        dropped: resp.dropped_citations,
        unanswerable: resp.unanswerable,
        createdAt: new Date().toISOString(),
      };
      const next = convs.map((c) =>
        c.id === conv.id ? { ...c, messages: [...c.messages, assistantMsg] } : c
      );
      saveConversation(next.find((c) => c.id === conv.id)!);
      persist(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed. Is the backend running?");
    } finally {
      setThinking(false);
    }
  };

  const runSearch = async (query: string) => {
    setSearching(true);
    setError(null);
    try {
      const resp = await search(query, 10);
      setSearchResults(resp.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const submitMessage = (value?: string) => {
    const query = (value ?? input).trim();
    if (!query || thinking || searching) return;
    setInput("");
    if (mode === "search") void runSearch(query);
    else void runChat(query);
  };

  const handleFeedback = (id: string, feedback: "up" | "down") => {
    if (!active) return;
    const convs = conversations.map((c) =>
      c.id === active.id
        ? { ...c, messages: c.messages.map((m) => (m.id === id ? { ...m, feedback } : m)) }
        : c
    );
    saveConversation(convs.find((c) => c.id === active.id)!);
    persist(convs);
  };

  const handleOpenEvidence = (chunk: EvidenceChunk) => {
    setEvidenceChunks((prev) =>
      prev.some((c) => c.chunk_id === chunk.chunk_id) ? prev : [chunk, ...prev]
    );
    setEvidenceOpen(true);
  };

  const handleDelete = (id: string) => {
    const next = deleteConversation(id);
    persist(next);
    if (id === activeId) setActiveId(null);
  };

  const handleClearAll = () => {
    persist(clearConversations());
    setActiveId(null);
  };

  const openConversation = (id: string) => {
    const conv = conversations.find((c) => c.id === id);
    if (conv) {
      setProject(conv.project);
      setSearchResults([]);
    }
    setActiveId(id);
  };

  const evidenceSearch = async (query: string): Promise<EvidenceChunk[]> => {
    const resp = await search(query, 8);
    return resp.results;
  };

  const busy = thinking || searching;

  return (
    <div className="-mx-4 -my-4 flex h-[calc(100vh-4rem)] overflow-hidden lg:-mx-6 lg:-my-6">
      <ConversationHistory
        conversations={conversations}
        activeId={activeId}
        onSelect={openConversation}
        onNew={() => {
          setActiveId(null);
          setInput("");
          setSearchResults([]);
          composerRef.current?.focus();
        }}
        onDelete={handleDelete}
        onClearAll={handleClearAll}
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
      />

      <section className="flex min-w-0 flex-1 flex-col bg-background/40">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-white/8 px-3">
          <button
            onClick={() => setHistoryOpen(true)}
            className="rounded-md p-1.5 text-muted hover:bg-white/10 hover:text-foreground lg:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-foreground">
              {active ? active.title : "New conversation"}
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-muted">
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
                Grounded Q&A
              </span>
              <span>·</span>
              <span className="max-w-[180px] truncate">
                {project === "__all" ? "All documents" : `Project: ${project}`}
              </span>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {mode === "chat" && active && (
              <Badge variant="success" className="hidden sm:inline-flex">
                <CheckCircle2 className="h-3 w-3" />
                {active.messages.filter((m) => m.role === "assistant" && m.citations?.length).length} answers verified
              </Badge>
            )}
            <button
              onClick={() => setEvidenceOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-white/8 bg-white/5 px-2.5 py-1.5 text-[11px] font-medium text-muted transition-colors hover:border-primary/40 hover:text-foreground lg:hidden"
            >
              <BookOpenCheck className="h-3.5 w-3.5 text-primary" /> Evidence
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto scroll-thin">
          <div className="mx-auto w-full max-w-3xl px-4 py-5">
            {active && active.messages.length > 0 ? (
              <div className="space-y-5">
                <AnimatePresence initial={false}>
                  {active.messages.map((m) => (
                    <MessageBubble key={m.id} message={m} onOpenEvidence={handleOpenEvidence} onFeedback={handleFeedback} />
                  ))}
                </AnimatePresence>
                {thinking && <TypingIndicator />}
                <div ref={bottomRef} />
              </div>
            ) : mode === "search" ? (
              <SearchLanding searching={searching} results={searchResults} onOpen={handleOpenEvidence} />
            ) : (
              <Welcome onPrompt={(p) => submitMessage(p)} />
            )}
          </div>
        </div>

        <Composer
          ref={composerRef}
          value={input}
          onChange={setInput}
          onSubmit={() => submitMessage()}
          mode={mode}
          onModeChange={(m) => {
            setMode(m);
            if (m === "search") setSearchResults([]);
          }}
          project={project}
          onProjectChange={setProject}
          projects={projectNames}
          busy={busy}
          error={error}
        />
      </section>

      <EvidencePanel
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
        activeChunks={evidenceChunks}
        project={project}
        onProjectChange={setProject}
        projects={projectNames}
        onSearchQuery={evidenceSearch}
      />
    </div>
  );
}

function Welcome({ onPrompt }: { onPrompt: (prompt: string) => void }) {
  return (
    <div className="flex flex-col items-center pt-8 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="relative mb-5"
      >
        <div className="absolute inset-0 rounded-2xl bg-primary/40 blur-2xl" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-emerald-500 shadow-xl shadow-primary/30">
          <Sparkles className="h-7 w-7 text-white" />
        </div>
      </motion.div>

      <h1 className="text-2xl font-bold tracking-tight text-foreground">
        Your documents, <span className="text-gradient">every answer verified</span>
      </h1>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted">
        Ask questions about your financial documents. Every answer is generated only from cited
        evidence — never from imagination.
      </p>

      <div className="mt-7 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((s, i) => (
          <motion.button
            key={s.title}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 + i * 0.05 }}
            onClick={() => onPrompt(s.prompt)}
            className="group rounded-xl border border-white/8 bg-white/[0.03] p-3.5 text-left transition-all hover:border-primary/40 hover:bg-primary-soft/30"
          >
            <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-primary-soft text-primary">
              <s.icon className="h-4 w-4" />
            </div>
            <div className="text-xs font-semibold text-foreground">{s.title}</div>
            <div className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-muted">{s.prompt}</div>
          </motion.button>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-[10px] text-muted/60">
        {["Hybrid retrieval", "Verified citations", "Multi-document", "Provenance tracked"].map((t) => (
          <span key={t} className="rounded-full border border-white/8 bg-white/[0.02] px-2.5 py-1">
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}

function SearchLanding({
  searching,
  results,
  onOpen,
}: {
  searching: boolean;
  results: EvidenceChunk[];
  onOpen: (chunk: EvidenceChunk) => void;
}) {
  if (searching) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <p className="mt-3 text-xs text-muted">Searching your corpus…</p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary-soft">
          <FileSearch className="h-6 w-6 text-primary" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">Semantic search</h3>
        <p className="mt-1 max-w-xs text-xs text-muted">
          Search across every ingested document. Results include exact page and section provenance.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 px-1 text-[11px] font-semibold uppercase tracking-widest text-muted/60">
        <FileSearch className="h-3.5 w-3.5" />
        {results.length} results
      </div>
      <AnimatePresence>
        {results.map((r, i) => (
          <motion.button
            key={r.chunk_id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            onClick={() => onOpen(r)}
            className="w-full rounded-xl border border-white/8 bg-white/[0.02] p-3.5 text-left transition-colors hover:border-primary/30 hover:bg-white/[0.04]"
          >
            <div className="flex items-center gap-2">
              <FileSearch className="h-3.5 w-3.5 shrink-0 text-primary" />
              <span className="truncate text-xs font-medium text-foreground">{r.filename}</span>
              <span className="ml-auto shrink-0 text-[10px] text-muted">p{r.page_number}</span>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted">{r.content}</p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="rounded bg-white/5 px-1.5 py-0.5 text-[9px] text-muted">
                {r.section || "Excerpt"}
              </span>
              <div className="ml-auto flex items-center gap-1.5">
                <div className="h-1 w-14 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${Math.round((r.score || 0) * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] font-medium text-primary">
                  {Math.round((r.score || 0) * 100)}%
                </span>
              </div>
            </div>
          </motion.button>
        ))}
      </AnimatePresence>
    </div>
  );
}
