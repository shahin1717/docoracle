import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_graph import (
    EntityExtractor, RelationExtractor,
    GraphBuilder, GraphStore
)

from ai.ingestion import parse_document
from ai.chunker import Chunker



def build_kg(pdf_path: str):
    doc_id = Path(pdf_path).stem

    print(f"\n[1] Parsing {pdf_path}...")
    doc    = parse_document(pdf_path)
    chunks = Chunker().chunk_document(doc)
    print(f"    {len(chunks)} chunks")

    chunk_dicts = [{"chunk_id": c.chunk_id, "text": c.text} for c in chunks]

    print("\n[2] Extracting entities...")
    entities = EntityExtractor().extract_from_chunks(chunk_dicts)
    print(f"    {len(entities)} entities")

    print("\n[3] Extracting relations...")
    triples = RelationExtractor().extract_from_chunks(chunk_dicts, entities)
    print(f"    {len(triples)} triples")

    print("\n[4] Building + saving graph...")
    graph = GraphBuilder().build(entities, triples)
    GraphStore("data/graphs").save(graph, doc_id)

    print(f"\n    Done → data/graphs/{doc_id}.json")
    print(f"    Nodes: {graph.number_of_nodes()}")
    print(f"    Edges: {graph.number_of_edges()}")

    # Print sample triples
    print("\n    Sample relations found:")
    for u, v, data in list(graph.edges(data=True))[:10]:
        print(f"    {graph.nodes[u]['label']} --[{data['relation']}]--> {graph.nodes[v]['label']}")

import matplotlib
matplotlib.use("Agg")  # no display needed
import matplotlib.pyplot as plt
import networkx as nx


def plot_kg(graph, doc_id: str):
    if graph.number_of_nodes() == 0:
        print("    No nodes to plot")
        return

    print("\n[5] Plotting graph...")

    # Color nodes by type
    color_map = {
        "ROOT":       "#7C6FCD",   # purple — center
        "MAIN_TOPIC": "#4A90D9",   # blue — branches  
        "SUBTOPIC":   "#5BA85A",   # green — leaves
        "UNKNOWN":    "#888780",
    }

    node_colors = [
        color_map.get(graph.nodes[n].get("type", "UNKNOWN"), "#888780")
        for n in graph.nodes
    ]

    # Size nodes by frequency
    node_sizes = [
        300 + graph.nodes[n].get("frequency", 1) * 150
        for n in graph.nodes
    ]

    labels = {n: graph.nodes[n].get("label", n) for n in graph.nodes}
    edge_labels = {(u, v): d["relation"] for u, v, d in graph.edges(data=True)}

    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor("#1a1a1a")
    ax.set_facecolor("#1a1a1a")

    pos = nx.spring_layout(graph, k=2.5, seed=42)

    nx.draw_networkx_nodes(graph, pos, node_color=node_colors,
                           node_size=node_sizes, alpha=0.9, ax=ax)

    nx.draw_networkx_edges(graph, pos, edge_color="#555550",
                           arrows=True, arrowsize=15,
                           width=0.8, alpha=0.7, ax=ax)

    nx.draw_networkx_labels(graph, pos, labels, font_size=8,
                            font_color="white", ax=ax)

    nx.draw_networkx_edge_labels(graph, pos, edge_labels,
                                 font_size=6, font_color="#BA7517", ax=ax)

    # Legend
    for label, color in color_map.items():
        ax.plot([], [], "o", color=color, label=label.replace("_", " ").title())
    ax.legend(loc="upper left", facecolor="#2a2a2a", labelcolor="white", fontsize=8)

    ax.set_title(f"Knowledge Graph — {doc_id}", color="white", fontsize=14, pad=15)
    ax.axis("off")

    out = f"data/graphs/{doc_id}_plot.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="#1a1a1a")
    plt.close()
    print(f"    Saved → {out}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python build_kg.py <pdf_path>")
        sys.exit(1)
    build_kg(sys.argv[1])
    plot_kg(GraphStore("data/graphs").load(Path(sys.argv[1]).stem), Path(sys.argv[1]).stem)