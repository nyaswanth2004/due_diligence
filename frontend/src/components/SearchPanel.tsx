import { useState } from "react";
import { DocumentItem, search, SearchResponse } from "../api";

export function SearchPanel({ documents }: { documents: DocumentItem[] }) {
  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await search(query, 8, documentId || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <div className="card">
        <h2>Semantic search</h2>
        <div className="row">
          <input
            value={query}
            placeholder="e.g. What was revenue in 2024?"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
          />
          <select
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
          >
            <option value="">All documents</option>
            {documents.filter((d) => d.status === "ready").map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </select>
          <button onClick={run} disabled={loading || !query.trim()}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      {result && (
        <div className="card">
          <h2>
            {result.total} result{result.total === 1 ? "" : "s"} in{" "}
            {result.search_time_ms}ms
          </h2>
          {result.results.map((hit) => (
            <div key={hit.chunk_id} className="hit">
              <div className="hit-meta">
                <strong>{hit.filename}</strong> · p.{hit.page_number}
                {hit.section && ` · ${hit.section}`} · score{" "}
                {hit.score.toFixed(4)}
              </div>
              <p className="pre-wrap">{hit.content}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
