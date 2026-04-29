"""
backend/services/kg_service.py

Serves knowledge graph data to graph.py routes.
Loads saved graphs from disk and exports them in frontend-ready format.
"""

import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_graph_data(doc_id: int) -> dict:
    """
    Load the saved graph for doc_id and return it in
    react-force-graph JSON format: { nodes: [...], links: [...] }
    """
    try:
        from knowledge_graph.graph_store    import GraphStore
        from knowledge_graph.graph_exporter import GraphExporter

        graph = GraphStore().load(doc_id=doc_id)
        if graph is None:
            raise HTTPException(status_code=404, detail="Graph not found on disk")

        return GraphExporter().to_frontend_json(graph)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[kg_service] get_graph_data failed for doc {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load graph: {e}")


def get_subgraph_data(doc_id: int, query: str, depth: int = 2) -> dict:
    """
    Return a subgraph centred on nodes matching the query term,
    also in react-force-graph format.
    """
    try:
        from knowledge_graph.graph_store     import GraphStore
        from knowledge_graph.graph_retriever import GraphRetriever
        from knowledge_graph.graph_exporter  import GraphExporter

        graph     = GraphStore().load(doc_id=doc_id)
        if graph is None:
            raise HTTPException(status_code=404, detail="Graph not found on disk")

        retriever = GraphRetriever(graph)
        subgraph  = retriever.get_subgraph(query, depth=depth)

        return GraphExporter().to_frontend_json(subgraph)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[kg_service] get_subgraph_data failed for doc {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load subgraph: {e}")