import json
from pathlib import Path
import networkx as nx
from networkx.readwrite import json_graph


class GraphStore:
    """
    Persists and loads knowledge graphs to/from disk.

    One JSON file per document — stored in data/graphs/{doc_id}.json
    Format: NetworkX node-link JSON (nodes + links arrays)

    This is simple and frontend-friendly — the same JSON gets
    served directly to react-force-graph in the UI.
    """

    def __init__(self, graphs_dir: str | Path = "data/graphs"):
        self.graphs_dir = Path(graphs_dir)
        self.graphs_dir.mkdir(parents=True, exist_ok=True)

    def save(self, graph: nx.DiGraph, doc_id: str):
        """Serialize graph to JSON and save to disk."""
        data = json_graph.node_link_data(graph)
        path = self._path(doc_id)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, doc_id: str) -> nx.DiGraph | None:
        """Load a graph from disk. Returns None if not found."""
        path = self._path(doc_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return json_graph.node_link_graph(data, directed=True)

    def exists(self, doc_id: str) -> bool:
        return self._path(doc_id).exists()

    def delete(self, doc_id: str):
        path = self._path(doc_id)
        if path.exists():
            path.unlink()

    def list_docs(self) -> list[str]:
        """Return all doc_ids that have a stored graph."""
        return [p.stem for p in self.graphs_dir.glob("*.json")]

    def export_for_frontend(self, doc_id: str) -> dict | None:
        """
        Load graph and return a clean dict ready for react-force-graph.

        react-force-graph expects:
        {
            "nodes": [{"id": "...", "label": "...", "type": "...", "val": 1}, ...],
            "links": [{"source": "...", "target": "...", "relation": "..."}, ...]
        }
        """
        graph = self.load(doc_id)
        if graph is None:
            return None

        nodes = []
        for node_id, attrs in graph.nodes(data=True):
            nodes.append({
                "id":        node_id,
                "label":     attrs.get("label", node_id),
                "type":      attrs.get("type", "UNKNOWN"),
                "val":       attrs.get("frequency", 1),  # controls node size in UI
                "chunk_ids": attrs.get("chunk_ids", []),
            })

        links = []
        for source, target, attrs in graph.edges(data=True):
            links.append({
                "source":   source,
                "target":   target,
                "relation": attrs.get("relation", "RELATED"),
                "weight":   attrs.get("weight", 1),
            })

        return {"nodes": nodes, "links": links}

    def _path(self, doc_id: str) -> Path:
        # Sanitize doc_id to be safe as a filename
        safe = doc_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
        return self.graphs_dir / f"{safe}.json"