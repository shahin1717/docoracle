import networkx as nx


class GraphRetriever:
    """
    Queries the knowledge graph to augment RAG context.

    When a user asks a question, we extract key entities from the query,
    find their neighbors in the graph, and return that context to inject
    into the LLM prompt alongside the chunk text.

    This is called GraphRAG — it gives much better answers for
    multi-hop questions like "how does X relate to Y?"
    """

    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def get_context_for_query(self, query: str, top_k: int = 5) -> str:
        """
        Main entry point. Takes a query string, finds relevant graph
        context, returns it as a plain text string to inject into prompt.
        """
        entities = self._extract_query_entities(query)
        if not entities:
            return ""

        facts = []
        for entity in entities:
            node_id = entity.lower()
            if node_id not in self.graph:
                continue
            neighbors = self._get_neighbors(node_id)
            for n in neighbors[:top_k]:
                facts.append(
                    f"{self.graph.nodes[node_id].get('label', node_id)} "
                    f"--[{n['relation']}]--> {n['label']}"
                )

        if not facts:
            return ""

        return "Knowledge graph context:\n" + "\n".join(facts)

    def find_path(self, entity_a: str, entity_b: str) -> list[str]:
        """
        Find the shortest path between two entities in the graph.
        Useful for explaining how two concepts are connected.
        """
        a = entity_a.lower()
        b = entity_b.lower()

        if a not in self.graph or b not in self.graph:
            return []

        try:
            path = nx.shortest_path(self.graph, source=a, target=b)
            return [self.graph.nodes[n].get("label", n) for n in path]
        except nx.NetworkXNoPath:
            return []

    def get_subgraph(self, entity: str, depth: int = 2) -> nx.DiGraph:
        """
        Return a subgraph centered on an entity up to `depth` hops away.
        Used to generate focused graph visualizations in the UI.
        """
        node_id = entity.lower()
        if node_id not in self.graph:
            return nx.DiGraph()

        nodes = {node_id}
        frontier = {node_id}

        for _ in range(depth):
            next_frontier = set()
            for n in frontier:
                next_frontier.update(self.graph.successors(n))
                next_frontier.update(self.graph.predecessors(n))
            nodes.update(next_frontier)
            frontier = next_frontier

        return self.graph.subgraph(nodes).copy()

    def _get_neighbors(self, node_id: str) -> list[dict]:
        neighbors = []
        for successor in self.graph.successors(node_id):
            edge = self.graph[node_id][successor]
            neighbors.append({
                "label":    self.graph.nodes[successor].get("label", successor),
                "relation": edge.get("relation", "RELATED"),
                "direction": "outgoing",
            })
        for predecessor in self.graph.predecessors(node_id):
            edge = self.graph[predecessor][node_id]
            neighbors.append({
                "label":    self.graph.nodes[predecessor].get("label", predecessor),
                "relation": edge.get("relation", "RELATED"),
                "direction": "incoming",
            })
        return neighbors

    def _extract_query_entities(self, query: str) -> list[str]:
        """
        Simple entity extraction from query — capitalized words and
        hyphenated terms. Good enough for routing to the graph.
        """
        import re
        entities = []
        # Capitalized words
        for match in re.finditer(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query):
            entities.append(match.group())
        # Hyphenated terms
        for match in re.finditer(r'\b[a-z]+-[a-z]+\b', query):
            entities.append(match.group())
        # All words as fallback (lowercased, length > 4)
        if not entities:
            entities = [w for w in query.split() if len(w) > 4]
        return entities