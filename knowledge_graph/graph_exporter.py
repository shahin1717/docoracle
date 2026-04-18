import json
from pathlib import Path
import networkx as nx


class GraphExporter:
    """
    Exports the knowledge graph to different formats.

    - JSON  → for react-force-graph in the frontend
    - GEXF  → for Gephi (desktop graph analysis tool)
    - CSV   → nodes.csv + edges.csv for spreadsheet analysis
    """

    def to_frontend_json(self, graph: nx.DiGraph) -> dict:
        """
        Format for react-force-graph:
        { nodes: [{id, label, type, val}], links: [{source, target, relation}] }
        """
        nodes = [
            {
                "id":    node_id,
                "label": attrs.get("label", node_id),
                "type":  attrs.get("type", "UNKNOWN"),
                "val":   attrs.get("frequency", 1),
            }
            for node_id, attrs in graph.nodes(data=True)
        ]
        links = [
            {
                "source":   src,
                "target":   tgt,
                "relation": attrs.get("relation", "RELATED"),
                "weight":   attrs.get("weight", 1),
            }
            for src, tgt, attrs in graph.edges(data=True)
        ]
        return {"nodes": nodes, "links": links}

    def to_json_file(self, graph: nx.DiGraph, path: str | Path):
        data = self.to_frontend_json(graph)
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def to_gexf(self, graph: nx.DiGraph, path: str | Path):
        """Export to GEXF format for Gephi visualization."""
        nx.write_gexf(graph, str(path))

    def to_csv(self, graph: nx.DiGraph, output_dir: str | Path):
        """Export nodes and edges as separate CSV files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # nodes.csv
        with open(output_dir / "nodes.csv", "w", encoding="utf-8") as f:
            f.write("id,label,type,frequency\n")
            for node_id, attrs in graph.nodes(data=True):
                label = attrs.get("label", node_id).replace(",", " ")
                ntype = attrs.get("type", "UNKNOWN")
                freq  = attrs.get("frequency", 1)
                f.write(f"{node_id},{label},{ntype},{freq}\n")

        # edges.csv
        with open(output_dir / "edges.csv", "w", encoding="utf-8") as f:
            f.write("source,target,relation,weight\n")
            for src, tgt, attrs in graph.edges(data=True):
                rel    = attrs.get("relation", "RELATED")
                weight = attrs.get("weight", 1)
                f.write(f"{src},{tgt},{rel},{weight}\n")