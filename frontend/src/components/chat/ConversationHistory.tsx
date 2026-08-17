import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, MessageSquare, Trash2, Search, X, MessagesSquare } from "lucide-react";
import type { Conversation } from "../../lib/conversations";
import { dayGroup } from "../../lib/conversations";
import { cn } from "../../lib/utils";

interface HistoryProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onClearAll: () => void;
  open: boolean;
  onClose: () => void;
}

export function ConversationHistory({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onClearAll,
  open,
  onClose,
}: HistoryProps) {
  const [query, setQuery] = React.useState("");

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(query.toLowerCase())
  );

  const groups: { label: string; items: Conversation[] }[] = [];
  for (const c of filtered) {
    const label = dayGroup(c.updatedAt);
    const group = groups.find((g) => g.label === label);
    if (group) group.items.push(c);
    else groups.push({ label, items: [c] });
  }

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden animate-fade-in" onClick={onClose} />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/8 bg-surface/98 transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-[288px]"
        )}
      >
        <div className="flex items-center justify-between border-b border-white/8 p-3">
          <span className="px-1 text-[10px] font-semibold uppercase tracking-widest text-muted/60">
            Conversations
          </span>
          <button onClick={onClose} className="rounded-md p-1 text-muted hover:bg-white/10 hover:text-foreground lg:hidden">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="border-b border-white/8 p-3">
          <button
            onClick={onNew}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-primary to-blue-600 px-3 py-2.5 text-xs font-semibold text-white shadow-lg shadow-primary/25 transition-all hover:shadow-primary/40 active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" /> New conversation
          </button>

          <div className="relative mt-2.5">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted/50" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search conversations…"
              className="h-8 w-full rounded-lg border border-white/8 bg-white/5 pl-8 pr-3 text-xs text-foreground placeholder:text-muted/50 focus:border-primary/40 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-3 scroll-thin">
          {groups.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft">
                <MessagesSquare className="h-5 w-5 text-primary" />
              </div>
              <p className="text-xs text-muted">No conversations yet. Start a new one.</p>
            </div>
          ) : (
            groups.map((group) => (
              <div key={group.label}>
                <div className="px-1.5 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted/50">
                  {group.label}
                </div>
                <div className="space-y-0.5">
                  <AnimatePresence initial={false}>
                    {group.items.map((conv) => (
                      <motion.div
                        key={conv.id}
                        layout
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="group"
                      >
                        <div
                          onClick={() => {
                            onSelect(conv.id);
                            onClose();
                          }}
                          className={cn(
                            "flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 transition-colors",
                            conv.id === activeId
                              ? "bg-primary-soft"
                              : "hover:bg-white/5"
                          )}
                        >
                          <MessageSquare
                            className={cn("h-3.5 w-3.5 shrink-0", conv.id === activeId ? "text-primary" : "text-muted/60")}
                          />
                          <div className="min-w-0 flex-1">
                            <div
                              className={cn(
                                "truncate text-xs font-medium",
                                conv.id === activeId ? "text-primary" : "text-foreground/85"
                              )}
                            >
                              {conv.title}
                            </div>
                            <div className="text-[10px] text-muted/50">
                              {new Date(conv.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </div>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onDelete(conv.id);
                            }}
                            className="hidden h-6 w-6 items-center justify-center rounded-md text-muted/50 hover:bg-danger-soft hover:text-danger group-hover:flex"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            ))
          )}
        </div>

        {conversations.length > 0 && (
          <div className="border-t border-white/8 p-3">
            <button
              onClick={onClearAll}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-[11px] font-medium text-muted transition-colors hover:bg-danger-soft hover:text-danger"
            >
              <Trash2 className="h-3.5 w-3.5" /> Clear all conversations
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
