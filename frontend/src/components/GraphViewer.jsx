import { useState, useEffect } from "react";
import { getDocumentGraph } from "../api/client";
import { RefreshCw, AlertCircle, Loader2 } from "lucide-react";

export default function GraphViewer({ documents = [], onNodeClick }) {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [entities, setEntities] = useState([]);

  const readyDocs = documents.filter((d) => d.kg_ready && d.status === "ready");
  const hasPendingDocs = documents.some((d) => !d.kg_ready || d.status !== "ready");

  useEffect(() => {
    fetchMergedGraph();
  }, [documents]); // re-fetch if documents array changes (like adding a doc, or one becomes ready)

  async function fetchMergedGraph() {
    if (readyDocs.length === 0) {
      setGraphData(null);
      setEntities([]);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      // Fetch graphs for all ready documents in parallel
      const allGraphs = await Promise.all(
        readyDocs.map((d) => getDocumentGraph(d.id).catch(() => null))
      );

      const mergedNodes = new Map();
      const mergedLinks = [];
      const linkSet = new Set();

      allGraphs.forEach((g) => {
        if (!g) return;
        if (g.nodes) {
          g.nodes.forEach((n) => {
            const id = n.id || n.label || n.name;
            if (!mergedNodes.has(id)) {
              mergedNodes.set(id, n);
            }
          });
        }
        if (g.links) {
          g.links.forEach((l) => {
            const source = typeof l.source === "object" ? l.source.id : l.source;
            const target = typeof l.target === "object" ? l.target.id : l.target;
            const rel = l.label || l.relation || "";
            const key = `${source}-${target}-${rel}`;
            if (!linkSet.has(key)) {
              linkSet.add(key);
              mergedLinks.push(l);
            }
          });
        }
      });

      setGraphData({
        nodes: Array.from(mergedNodes.values()),
        links: mergedLinks,
        type: "Merged Knowledge Graph",
      });

      // Extract unique entities for buttons
      const entitySet = new Set();
      mergedNodes.forEach((n) => {
        if (n.label || n.name) {
          entitySet.add(n.label || n.name);
        }
      });
      setEntities(Array.from(entitySet).slice(0, 15)); // Top 15

    } catch (err) {
      setError("Failed to merge workspace graphs.");
      console.error("Failed to fetch merged graph:", err);
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
      <div className="p-5 border-b border-white/10 flex items-center justify-between">
        <div>
          <h2 className="font-semibold mb-1 flex items-center gap-2">
            Knowledge Graph
            {hasPendingDocs && (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-400" title="Processing new documents..." />
            )}
          </h2>
          <p className="text-sm text-white/40">
            Workspace entities & relationships
          </p>
        </div>
        <button
          onClick={fetchMergedGraph}
          disabled={loading || readyDocs.length === 0}
          className="p-2 hover:bg-white/10 rounded-lg transition disabled:opacity-50"
          title="Refresh Graph"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="flex-1 p-5 overflow-y-auto space-y-5">
        {error && (
          <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* If no docs are ready, but some are pending, show big spinner */}
        {readyDocs.length === 0 && hasPendingDocs ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="animate-spin mb-4">
              <div className="w-8 h-8 border-2 border-violet-600 border-t-transparent rounded-full" />
            </div>
            <p className="text-sm font-medium text-white/80">Processing Workspace...</p>
            <p className="text-xs text-white/40 mt-2 max-w-[250px]">
              Extracting knowledge graph entities and relationships. This may take a moment.
            </p>
          </div>
        ) : loading && !graphData ? (
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
                  No entities extracted yet.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {entities.map((entity) => (
                    <button
                      key={entity}
                      onClick={() => {
                        if (onNodeClick) onNodeClick(entity);
                      }}
                      className="text-xs px-3 py-1 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20 hover:bg-violet-500/20 transition cursor-pointer"
                    >
                      {entity}
                    </button>
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
                    <span className="text-white/80">Total Nodes:</span> {graphData.nodes.length}
                  </div>
                  <div>
                    <span className="text-white/80">Total Relationships:</span>{" "}
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
                <p className="text-white/80 font-medium mb-2">Workspace Graph</p>
                <p>Merged from {readyDocs.length} document{readyDocs.length > 1 ? "s" : ""}</p>
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
