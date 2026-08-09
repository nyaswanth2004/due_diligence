import * as React from "react";
import { motion } from "framer-motion";

const STATUSES = [
  "Retrieving evidence from your documents…",
  "Ranking passages by relevance…",
  "Verifying citation accuracy…",
  "Composing grounded answer…",
];

export function TypingIndicator() {
  const [index, setIndex] = React.useState(0);

  React.useEffect(() => {
    const timer = setInterval(() => setIndex((i) => (i + 1) % STATUSES.length), 1600);
    return () => clearInterval(timer);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3"
    >
      <div className="relative mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-emerald-500 shadow-lg shadow-primary/20">
        <div className="absolute inset-0 animate-ping rounded-full bg-primary/30" />
        <motion.span
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
          className="h-3.5 w-3.5 rounded-full border-2 border-white/30 border-t-white"
        />
      </div>
      <div className="rounded-2xl rounded-tl-sm border border-white/8 bg-white/[0.04] px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="flex gap-1">
            {[0, 1, 2].map((dot) => (
              <motion.span
                key={dot}
                className="h-1.5 w-1.5 rounded-full bg-primary"
                animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
                transition={{ repeat: Infinity, duration: 1, delay: dot * 0.15 }}
              />
            ))}
          </span>
        </div>
        <div className="mt-2 text-[11px] font-medium text-primary/80">{STATUSES[index]}</div>
      </div>
    </motion.div>
  );
}
