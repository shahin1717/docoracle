import networkx as nx


class GraphBuilder:
    """
    Builds a NetworkX directed graph from entities and triples.

    Nodes = entities
    Edges = relations (subject → object, labeled with relation type)

    Why NetworkX?
    - Pure Python, no server needed
    - Supports directed graphs, node/edge attributes
    - Easy to serialize to JSON for the frontend
    - Can later be exported to Neo4j if you want a full graph DB
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, entities: list[dict], triples: list[dict]) -> nx.DiGraph:
        """
        Build the graph from extracted entities and relation triples.
        Returns the NetworkX DiGraph.
        """
        self.graph.clear()
        self._add_entities(entities)
        self._add_triples(triples)
        return self.graph

    def _add_entities(self, entities: list[dict]):
        """Each entity becomes a node with its metadata as attributes."""
        for entity in entities:
            node_id = entity["text"].lower()
            self.graph.add_node(node_id, **{
                "label":     entity["text"],
                "type":      entity.get("type", "UNKNOWN"),
                "frequency": entity.get("frequency", 1),
                "chunk_ids": entity.get("chunk_ids", []),
            })

    def _add_triples(self, triples: list[dict]):
        """
        Each triple becomes a directed edge: subject → object.
        If the edge already exists, increment its weight.
        """
        for triple in triples:
            subj = triple["subject"].lower()
            obj  = triple["object"].lower()
            rel  = triple["relation"]

            # Auto-add nodes for entities we may have missed
            if subj not in self.graph:
                self.graph.add_node(subj, label=triple["subject"], type="UNKNOWN", frequency=1)
            if obj not in self.graph:
                self.graph.add_node(obj, label=triple["object"], type="UNKNOWN", frequency=1)

            if self.graph.has_edge(subj, obj):
                self.graph[subj][obj]["weight"] += 1
            else:
                self.graph.add_edge(subj, obj, **{
                    "relation":  rel,
                    "weight":    1,
                    "sentences": [triple.get("sentence", "")],
                })

    def get_neighbors(self, entity: str) -> list[dict]:
        """
        Return all nodes directly connected to this entity.
        Useful for graph-augmented RAG context.
        """
        node_id = entity.lower()
        if node_id not in self.graph:
            return []

        neighbors = []
        for successor in self.graph.successors(node_id):
            edge = self.graph[node_id][successor]
            neighbors.append({
                "entity":   self.graph.nodes[successor]["label"],
                "relation": edge["relation"],
                "direction": "outgoing",
            })
        for predecessor in self.graph.predecessors(node_id):
            edge = self.graph[predecessor][node_id]
            neighbors.append({
                "entity":   self.graph.nodes[predecessor]["label"],
                "relation": edge["relation"],
                "direction": "incoming",
            })
        return neighbors

    def stats(self) -> dict:
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": round(nx.density(self.graph), 4),
        }