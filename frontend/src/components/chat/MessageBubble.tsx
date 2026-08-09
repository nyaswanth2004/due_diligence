import * as React from "react";
import { motion } from "framer-motion";
import {
  User,
  Bot,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
  Clock,
} from "lucide-react";
import { Badge } from "../ui/badge";
import { Markdown } from "./Markdown";
import type { ChatMessage } from "../../lib/conversations";
import type { EvidenceChunk } from "../../api";
import { cn } from "../../lib/utils";

interface MessageBubbleProps {
  message: ChatMessage;
  onOpenEvidence: (chunk: EvidenceChunk) => void;
  onFeedback: (id: string, feedback: "up" | "down") => void;
}

export function MessageBubble({ message, onOpenEvidence, onFeedback }: MessageBubbleProps) {
  const [copied, setCopied] = React.useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  if (message.role === "user") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="flex justify-end gap-3"
      >
        <div className="max-w-[78%]">
          <div className="rounded-2xl rounded-tr-sm bg-gradient-to-br from-primary to-blue-600 px-4 py-3 text-sm leading-relaxed text-white shadow-lg shadow-primary/20">
            {message.content}
          </div>
          <div className="mt-1 flex items-center justify-end gap-1 pr-1 text-[10px] text-muted/50">
            <Clock className="h-2.5 w-2.5" />
            {new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </div>
        </div>
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
          <User className="h-4 w-4 text-muted" />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex gap-3"
    >
      <div className="relative mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-emerald-500 shadow-lg shadow-primary/20">
        <Bot className="h-4 w-4 text-white" />
      </div>

      <div className="max-w-[82%] min-w-0">
        <div className="rounded-2xl rounded-tl-sm border border-white/8 bg-white/[0.04] px-4 py-3 shadow-sm">
          {message.unanswerable && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-warning/25 bg-warning-soft px-3 py-2">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-warning" />
              <p className="text-[11px] text-warning">
                Not enough evidence in your documents to answer confidently. Refine the question or
                upload more source material.
              </p>
            </div>
          )}

          <Markdown content={message.content} />

          {message.citations && message.citations.length > 0 && (
            <div className="mt-3 border-t border-white/8 pt-2.5">
              <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted/60">
                <CheckCircle2 className="h-3 w-3 text-success" />
                Sources verified · {message.citations.length}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {message.citations.map((c, i) => (
                  <button
                    key={c.chunk_id}
                    onClick={() => onOpenEvidence(c)}
                    className="group inline-flex max-w-full items-center gap-1 rounded-lg border border-primary/25 bg-primary-soft px-2 py-1 text-[10px] font-medium text-primary transition-colors hover:border-primary/50 hover:bg-primary/20"
                  >
                    <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full bg-primary/20 text-[9px] font-bold">
                      {i + 1}
                    </span>
                    <span className="truncate">{c.filename}</span>
                    <span className="shrink-0 text-muted">· p{c.page_number}</span>
                    <ExternalLink className="h-2.5 w-2.5 shrink-0 opacity-60 group-hover:opacity-100" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {message.dropped && message.dropped.length > 0 && (
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-[10px] text-muted/60">
              <span className="font-medium">Excluded from answer:</span>
              {message.dropped.map((d) => (
                <Badge key={d} variant="outline" className="text-[9px]">
                  {d}
                </Badge>
              ))}
            </div>
          )}
        </div>

        <div className="mt-1.5 flex items-center gap-1 px-1">
          <span className="text-[10px] text-muted/50">
            {new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          <div className="ml-auto flex items-center gap-0.5">
            <button
              onClick={() => void copy()}
              className="flex h-6 w-6 items-center justify-center rounded-md text-muted/50 transition-colors hover:bg-white/5 hover:text-foreground"
            >
              {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
            </button>
            <button
              onClick={() => onFeedback(message.id, "up")}
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-md transition-colors hover:bg-white/5",
                message.feedback === "up" ? "text-success" : "text-muted/50 hover:text-foreground"
              )}
            >
              <ThumbsUp className="h-3 w-3" />
            </button>
            <button
              onClick={() => onFeedback(message.id, "down")}
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-md transition-colors hover:bg-white/5",
                message.feedback === "down" ? "text-danger" : "text-muted/50 hover:text-foreground"
              )}
            >
              <ThumbsDown className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
