import { useRef, useState } from "react";
import { deleteDocument, DocumentItem, uploadDocument } from "../api";

export function DocumentPanel({
  documents,
  onChanged,
}: {
  documents: DocumentItem[];
  onChanged: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file);
      }
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const ready = documents.filter((d) => d.status === "ready").length;

  return (
    <section>
      <div className="card">
        <h2>Upload financial documents</h2>
        <p className="muted">
          Supported: PDF (text & scanned), images, XLSX, XLS, CSV. Files are
          processed in the background and indexed for search.
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.csv"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {uploading && <p className="muted">Uploading…</p>}
        {error && <p className="error">{error}</p>}
      </div>

      <div className="card">
        <h2>
          Documents <span className="badge">{documents.length}</span>{" "}
          <span className="badge green">{ready} ready</span>
        </h2>
        {documents.length === 0 ? (
          <p className="muted">No documents uploaded yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>Pages</th>
                <th>Chunks</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td title={doc.id}>{doc.filename}</td>
                  <td>{doc.doc_type}</td>
                  <td>{doc.page_count}</td>
                  <td>{doc.chunk_count}</td>
                  <td>
                    <span className={`status ${doc.status}`}>{doc.status}</span>
                    {doc.error_message && (
                      <span className="error" title={doc.error_message}>
                        {" "}
                        — failed
                      </span>
                    )}
                  </td>
                  <td>
                    <button className="danger" onClick={() => handleDelete(doc.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
