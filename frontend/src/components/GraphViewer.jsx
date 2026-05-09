import { useState, useEffect } from "react";
import { getDocumentGraph } from "../api/client";
import { AlertCircle } from "lucide-react";

export default function GraphViewer({ documents = [] }) {
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [entities, setEntities] = useState([]);

  useEffect(() => {
    if (selectedDocId) {
      fetchGraph(selectedDocId);
    } else if (documents.length > 0) {
      setSelectedDocId(documents[0].id);
    }
  }, [selectedDocId, documents]);

  async function fetchGraph(docId) {
    setLoading(true);
    setError(null);
    try {
      const graph = await getDocumentGraph(docId);
      setGraphData(graph);

      // Extract unique entities
      const entitySet = new Set();
      if (graph.nodes) {
        graph.nodes.forEach((node) => {
          if (node.label || node.name) {
            entitySet.add(node.label || node.name);
          }
        });
      }
      setEntities(Array.from(entitySet).slice(0, 10)); // Top 10
    } catch (err) {
      setError(err.message);
      console.error("Failed to fetch graph:", err);
    } finally {
      setLoading(false);
    }
  }

  if (documents.length === 0) {
    return (
      <aside className="w-[360px] border-l border-white/10 bg-[#11111b] hidden xl:flex flex-col items-center justify-center">
        <div className="text-center p-8">
          <p className="text-sm text-white/40 mb-2">No documents uploaded</p>
          <p className="text-xs text-white/20">
            Upload documents to see knowledge graphs
          </p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-[360px] border-l border-white/10 bg-[#11111b] hidden xl:flex flex-col">
      <div className="p-5 border-b border-white/10">
        <h2 className="font-semibold mb-1">Knowledge Graph</h2>
        <p className="text-sm text-white/40">
          Relationships extracted from documents
        </p>
      </div>

      {/* Document Selector */}
      {documents.length > 1 && (
        <div className="px-5 py-3 border-b border-white/10">
          <select
            value={selectedDocId || ""}
            onChange={(e) => setSelectedDocId(parseInt(e.target.value))}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-violet-500/50 transition"
          >
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex-1 p-5 overflow-y-auto space-y-5">
        {error && (
          <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin">
              <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full" />
            </div>
          </div>
        ) : (
          <>
            {/* Detected Entities */}
            <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
              <h3 className="text-sm font-medium mb-4">Detected Entities</h3>

              {entities.length === 0 ? (
                <p className="text-xs text-white/40">
                  No entities extracted yet. The graph will update as you query documents.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {entities.map((entity) => (
                    <span
                      key={entity}
                      className="text-xs px-3 py-1 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20"
                    >
                      {entity}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Graph Preview */}
            <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
              <h3 className="text-sm font-medium mb-4">Graph Structure</h3>

              {graphData && graphData.nodes ? (
                <div className="space-y-2 text-xs text-white/60">
                  <div>
                    <span className="text-white/80">Nodes:</span> {graphData.nodes.length}
                  </div>
                  <div>
                    <span className="text-white/80">Relationships:</span>{" "}
                    {graphData.links ? graphData.links.length : 0}
                  </div>

                  {/* Simple ASCII graph preview */}
                  <div className="mt-4 p-3 bg-white/5 rounded-lg font-mono text-[10px] text-white/40 max-h-[120px] overflow-auto">
                    {graphData.nodes.slice(0, 5).map((node, i) => (
                      <div key={i}>
                        → {node.label || node.name || `Node ${i}`}
                      </div>
                    ))}
                    {graphData.nodes.length > 5 && (
                      <div>... and {graphData.nodes.length - 5} more</div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="h-[120px] rounded-xl border border-dashed border-white/10 flex items-center justify-center text-white/30 text-sm">
                  Graph loading...
                </div>
              )}
            </div>

            {/* Graph Stats */}
            {graphData && (
              <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 text-xs text-white/60">
                <p className="text-white/80 font-medium mb-2">Graph Type</p>
                <p>{graphData.type || "Knowledge Graph"}</p>
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
