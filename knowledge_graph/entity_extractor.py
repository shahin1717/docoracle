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
        prompt = f"""Analyze this document and extract the main topic hierarchy.
Return ONLY a JSON object with this exact structure, no other text:
{{
  "title": "main subject of the document",
  "topics": [
    {{
      "name": "Main Topic 1",
      "subtopics": ["Subtopic A", "Subtopic B", "Subtopic C"]
    }},
    {{
      "name": "Main Topic 2", 
      "subtopics": ["Subtopic D", "Subtopic E"]
    }}
  ]
}}

Rules:
- Maximum 8 main topics
- Maximum 6 subtopics per topic
- Topics should be meaningful concepts, not single words
- Focus on the actual content, ignore slide numbers and formatting
- Do not include generic words like "Introduction" or "Summary" unless they contain real content

Document text:
{text[:4000]}

Return only the JSON:"""

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