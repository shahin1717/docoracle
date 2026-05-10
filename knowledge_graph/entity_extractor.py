import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "mistral:7b-instruct-q8_0"


class EntityExtractor:
    """
    LLM-powered hierarchical topic extractor.
    Instead of extracting every entity, asks the LLM to identify
    main topics and subtopics — like NotebookLM's mind map.
    """

    def __init__(self, model: str = DEFAULT_MODEL, ollama_url: str = OLLAMA_URL):
        self.model = model
        self.url = ollama_url

    def extract(self, text: str) -> list[dict]:
        """Extract flat entities — calls extract_hierarchy internally."""
        hierarchy = self.extract_hierarchy(text)
        return self._hierarchy_to_entities(hierarchy)

    def extract_from_chunks(self, chunks: list[dict]) -> list[dict]:
        """Extract hierarchy from all chunks combined."""
        full_text = "\n".join(c["text"] for c in chunks)
        hierarchy = self.extract_hierarchy(full_text)
        entities = self._hierarchy_to_entities(hierarchy)

        # attach chunk_ids to entities
        for entity in entities:
            entity["chunk_ids"] = [
                c["chunk_id"] for c in chunks
                if entity["text"].lower() in c["text"].lower()
            ]
            entity["frequency"] = max(1, len(entity["chunk_ids"]))

        return entities

    def extract_hierarchy(self, text: str) -> dict:
        """
        Ask LLM to extract a topic hierarchy from the text.
        Returns: {
            "title": "AI",
            "topics": [
                {
                    "name": "Machine Learning",
                    "subtopics": ["Decision Trees", "Neural Networks", "Clustering"]
                },
                ...
            ]
        }
        """
        doc_preview = text[:500]

        prompt = f"""You are a knowledge graph builder. Analyze this document and extract a clean concept hierarchy.

STRICT RULES:
- Extract only REAL CONCEPTS and TOPICS from the content
- IGNORE completely: author names, university names, course codes, city names, country names, dates, page numbers, slide numbers, words like "Introduction" "Definition" "Proposition" "Example" "Summary" "Conclusion" "Document" "Chapter" "Section"
- Main topics should be meaningful subject areas (3-6 words max)
- Subtopics should be specific concepts within that area
- If this is a math document: extract theorems, methods, formulas concepts, properties
- If this is a CS document: extract algorithms, data structures, techniques, models  
- If this is a science document: extract theories, experiments, phenomena, laws
- If this is a business document: extract processes, frameworks, strategies, metrics
- The title should be the actual subject matter, not the document name

Return ONLY this JSON with no explanation, no markdown, no extra text:
{{
  "title": "actual subject of the document",
  "topics": [
    {{
      "name": "Main Concept Area",
      "subtopics": ["specific concept", "specific concept", "specific concept"]
    }}
  ]
}}

Constraints:
- Maximum 7 main topics
- Maximum 5 subtopics per topic
- Every item must be a real concept from the content, not a formatting artifact

Document content:
{text[:3500]}

Return JSON only:"""


        try:
            response = requests.post(self.url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 1024},
            }, timeout=60)
            response.raise_for_status()

            raw = response.json()["response"].strip()

            # clean up — sometimes LLM wraps in markdown
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            # find the JSON object
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                raw = raw[start:end]

            return json.loads(raw)

        except Exception as e:
            print(f"  [KG] LLM extraction failed: {e}, using fallback")
            return self._fallback_extract(text)

    def _hierarchy_to_entities(self, hierarchy: dict) -> list[dict]:
        """Convert hierarchy dict to flat entity list for GraphBuilder."""
        entities = []

        # root node
        title = hierarchy.get("title", "Document")
        entities.append({
            "text": title,
            "type": "ROOT",
            "frequency": 10,
            "chunk_ids": [],
            "is_root": True,
        })

        for topic in hierarchy.get("topics", []):
            topic_name = topic.get("name", "")
            if not topic_name:
                continue

            entities.append({
                "text": topic_name,
                "type": "MAIN_TOPIC",
                "frequency": 5,
                "chunk_ids": [],
                "parent": title,
            })

            for subtopic in topic.get("subtopics", []):
                if not subtopic:
                    continue
                entities.append({
                    "text": subtopic,
                    "type": "SUBTOPIC",
                    "frequency": 2,
                    "chunk_ids": [],
                    "parent": topic_name,
                })

        return entities

    def _fallback_extract(self, text: str) -> dict:
        """Simple fallback if LLM fails."""
        import re
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 10]
        topics = list(set(lines[:6]))
        return {
            "title": "Document",
            "topics": [{"name": t[:40], "subtopics": []} for t in topics[:5]]
        }