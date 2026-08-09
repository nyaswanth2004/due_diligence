import { useState } from "react";
import { askQuestion, DocumentItem, EvidenceChunk, QAResponse } from "../api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations: EvidenceChunk[];
  unanswerable?: boolean;
  dropped?: string[];
}

export function QAPanel({ documents }: { documents: DocumentItem[] }) {
  const [documentId, setDocumentId] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async () => {
    const question = input.trim();
    if (!question || loading) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question, citations: [] }]);
    setLoading(true);
    const history = messages
      .filter((m) => m.role === "user" || m.content)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }));
    try {
      const res: QAResponse = await askQuestion(
        question,
        documentId ? [documentId] : undefined,
        history
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          unanswerable: res.unanswerable,
          dropped: res.dropped_citations,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Failed to get an answer.", citations: [] },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <div className="card">
        <h2>Grounded Q&amp;A</h2>
        <p className="muted">
          Answers are generated only from the uploaded documents and each
          citation is verified against the retrieved evidence.
        </p>
        <div className="row">
          <select value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
            <option value="">All documents</option>
            {documents.filter((d) => d.status === "ready").map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      <div className="card chat">
        {messages.length === 0 && (
          <p className="muted">
            Ask about the financials, e.g. “What were total assets for 2024?”
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="msg-role">{m.role === "user" ? "You" : "VeritasIQ"}</div>
            <p>{m.content}</p>
            {m.unanswerable && (
              <p className="muted">No evidence found — answer not cited.</p>
            )}
            {m.citations.length > 0 && (
              <div className="citations">
                <strong>Evidence ({m.citations.length}):</strong>
                {m.citations.map((c) => (
                  <div key={c.chunk_id} className="citation">
                    <span className="hit-meta">
                      {c.filename} · p.{c.page_number}
                      {c.section && ` · ${c.section}`}
                    </span>
                    <p className="pre-wrap">{c.content}</p>
                  </div>
                ))}
              </div>
            )}
            {m.dropped && m.dropped.length > 0 && (
              <p className="muted">
                Dropped citations: {m.dropped.length}
              </p>
            )}
          </div>
        ))}
        {loading && <p className="muted">VeritasIQ is thinking…</p>}
        <div className="row">
          <input
            value={input}
            placeholder="Ask a question…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
          />
          <button onClick={ask} disabled={loading || !input.trim()}>
            Ask
          </button>
        </div>
      </div>
    </section>
  );
}
