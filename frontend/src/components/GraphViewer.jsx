import React, { useState, useEffect } from "react";
import { getDocumentGraph } from "../api/client";
import { RefreshCw, AlertCircle, Loader2, X } from "lucide-react";
import Tree from "react-d3-tree";

// Helper function to build a forest of trees from a graph
function buildTree(nodes, links) {
  if (!nodes || nodes.length === 0) return [];

  const inDegree = {};
  const outDegree = {};
  const adj = {};

  nodes.forEach((n) => {
    const id = n.id || n.label || n.name;
    adj[id] = [];
    inDegree[id] = 0;
    outDegree[id] = 0;
  });

  links.forEach((l) => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    if (adj[s]) {
      adj[s].push({ target: t });
      outDegree[s] = (outDegree[s] || 0) + 1;
      inDegree[t] = (inDegree[t] || 0) + 1;
    }
  });

  // Sort nodes to find the best roots: high out-degree, low in-degree
  const sortedNodes = [...nodes].sort((a, b) => {
    const idA = a.id || a.label || a.name;
    const idB = b.id || b.label || b.name;
    const scoreA = (outDegree[idA] || 0) - (inDegree[idA] || 0);
    const scoreB = (outDegree[idB] || 0) - (inDegree[idB] || 0);
    return scoreB - scoreA;
  });

  const visited = new Set();
  const trees = [];

  function dfs(nodeId) {
    if (visited.has(nodeId)) return null;
    visited.add(nodeId);

    const node = nodes.find((n) => (n.id || n.label || n.name) === nodeId);
    if (!node) return null;

    const children = [];
    if (adj[nodeId]) {
      adj[nodeId].forEach((edge) => {
        const childTree = dfs(edge.target);
        if (childTree) {
          children.push(childTree);
        }
      });
    }

    return { node, children };
  }

  sortedNodes.forEach((n) => {
    const id = n.id || n.label || n.name;
    if (!visited.has(id)) {
      const tree = dfs(id);
      if (tree) trees.push(tree);
    }
  });

  return trees;
}

function mapTreeToD3(tree) {
  if (!tree || !tree.node) return null;
  const name = tree.node.label || tree.node.name || tree.node.id;
  const children = (tree.children || []).map(mapTreeToD3).filter(Boolean);
  return {
    name,
    children: children.length > 0 ? children : undefined,
  };
}

// Custom Node for the Tree
const renderRectSvgNode = ({ nodeDatum, toggleNode, onNodeClick }) => {
  return (
    <g>
      {/* Background Bubble */}
      <rect
        width={160}
        height={36}
        x={-80}
        y={-18}
        rx={18} // fully rounded
        fill="#1a1a2e"
        stroke="#8b5cf6"
        strokeWidth={1.5}
        onClick={() => {
          onNodeClick(nodeDatum.name);
        }}
        className="cursor-pointer hover:fill-[#2d2d44] transition-colors"
      />
      {/* Node Text */}
      <text
        fill="#e2e8f0"
        strokeWidth="0"
        x="0"
        y="4"
        textAnchor="middle"
        fontSize="12px"
        pointerEvents="none"
        className="font-sans"
      >
        {nodeDatum.name.length > 20 ? nodeDatum.name.substring(0, 18) + '...' : nodeDatum.name}
      </text>
      {/* Expansion Indicator if it has children */}
      {nodeDatum.children && nodeDatum.children.length > 0 && (
        <circle 
          r={6} 
          cx={80} 
          cy={0} 
          fill="#8b5cf6" 
          className="cursor-pointer" 
          onClick={toggleNode}
        />
      )}
      {nodeDatum._children && nodeDatum._children.length > 0 && (
        <circle 
          r={6} 
          cx={80} 
          cy={0} 
          fill="#4c1d95" 
          stroke="#8b5cf6"
          strokeWidth={1}
          className="cursor-pointer" 
          onClick={toggleNode}
        />
      )}
    </g>
  );
};

export default function GraphViewer({ documents = [], onNodeClick, onClose }) {
  const [d3TreeData, setD3TreeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const readyDocs = documents.filter((d) => d.kg_ready && d.status === "ready");
  const hasPendingDocs = documents.some((d) => !d.kg_ready || d.status !== "ready");

  useEffect(() => {
    fetchMergedGraph();
  }, [documents]);

  async function fetchMergedGraph() {
    if (readyDocs.length === 0) {
      setD3TreeData(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
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
            const key = `${source}-${target}`;
            if (!linkSet.has(key)) {
              linkSet.add(key);
              mergedLinks.push({ source, target }); // Dropped relation labels
            }
          });
        }
      });

      const nodesArr = Array.from(mergedNodes.values());
      const trees = buildTree(nodesArr, mergedLinks);
      
      const mappedTrees = trees.map(mapTreeToD3).filter(Boolean);
      
      if (mappedTrees.length === 0) {
        setD3TreeData(null);
      } else if (mappedTrees.length === 1) {
        setD3TreeData(mappedTrees[0]);
      } else {
        // If there are multiple disconnected trees, wrap them in a central node
        setD3TreeData({
          name: "Workspace Graph",
          children: mappedTrees
        });
      }

    } catch (err) {
      setError("Failed to merge workspace graphs.");
      console.error("Failed to fetch merged graph:", err);
    } finally {
      setLoading(false);
    }
  }

  if (documents.length === 0) {
    return (
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="w-full max-w-5xl h-[80vh] bg-[#11111b] border border-white/10 rounded-2xl flex flex-col overflow-hidden shadow-2xl relative">
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 p-2 bg-white/5 hover:bg-white/10 rounded-full transition text-white/50 hover:text-white z-10"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
            <p className="text-sm text-white/40 mb-2">No documents uploaded</p>
            <p className="text-xs text-white/20">
              Upload documents to see the interactive knowledge tree
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-5xl h-[80vh] bg-[#11111b] border border-white/10 rounded-2xl flex flex-col overflow-hidden shadow-2xl">
        <div className="p-5 border-b border-white/10 flex items-center justify-between z-10 bg-[#11111b]">
        <div>
          <h2 className="font-semibold mb-1 flex items-center gap-2">
            Knowledge Map
            {hasPendingDocs && (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-400" title="Processing new documents..." />
            )}
          </h2>
          <p className="text-[11px] text-white/40">
            Click bubbles to query the AI
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchMergedGraph}
            disabled={loading || readyDocs.length === 0}
            className="p-2 hover:bg-white/10 rounded-lg transition disabled:opacity-50"
            title="Refresh Graph"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition text-white/50 hover:text-white"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="flex-1 relative overflow-hidden bg-black">
        {error && (
          <div className="absolute top-4 left-4 right-4 z-10 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {readyDocs.length === 0 && hasPendingDocs ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-8">
            <div className="animate-spin mb-4">
              <div className="w-8 h-8 border-2 border-violet-600 border-t-transparent rounded-full" />
            </div>
            <p className="text-sm font-medium text-white/80">Processing Workspace...</p>
            <p className="text-xs text-white/40 mt-2 max-w-[250px]">
              Building interactive node tree. This may take a moment.
            </p>
          </div>
        ) : loading && !d3TreeData ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="animate-spin">
              <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full" />
            </div>
          </div>
        ) : d3TreeData ? (
          <div className="w-full h-full">
            <Tree
              data={d3TreeData}
              orientation="horizontal"
              pathFunc="diagonal"
              translate={{ x: 100, y: 300 }} // starting offset so it's not hidden
              nodeSize={{ x: 200, y: 60 }} // horizontal and vertical spacing
              renderCustomNodeElement={(props) => renderRectSvgNode({ ...props, onNodeClick })}
              collapsible={true}
              zoomable={true}
              scaleExtent={{ min: 0.2, max: 2 }}
              separation={{ siblings: 1, nonSiblings: 1.5 }}
            />
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-white/30 text-sm">
            Graph loading...
          </div>
        )}
      </div>
    </div>
  </div>
);
}
