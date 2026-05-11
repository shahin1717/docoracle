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

    def extract_from_chunks(self, chunks: list[dict], toc: list[list] = None) -> list[dict]:
        """Extract hierarchy from sampled chunks throughout the document."""
        # Step 1: Get title from the very beginning
        title_text = chunks[0]["text"][:1000]
        
        # Step 2: Get thematic content from the middle/end (skip potentially noisy start)
        thematic_text = self._get_sampled_text(chunks, skip_start=True)
        
        hierarchy = self.extract_hierarchy(thematic_text, title_hint=title_text, toc=toc)
        entities = self._hierarchy_to_entities(hierarchy)

        # Step 3: Fuzzy link entities to chunks
        for entity in entities:
            e_text = entity["text"].lower()
            chunk_ids = []
            for c in chunks:
                c_text = c["text"].lower()
                if e_text in c_text:
                    chunk_ids.append(c["chunk_id"])
                elif " " in e_text:
                    words = e_text.split()
                    if all(w in c_text for w in words) and len(words) > 1:
                        chunk_ids.append(c["chunk_id"])
            
            entity["chunk_ids"] = list(set(chunk_ids))
            entity["frequency"] = max(1, len(entity["chunk_ids"]))

        return entities

    def _get_sampled_text(self, chunks: list[dict], max_chars: int = 6000, skip_start: bool = False) -> str:
        """Sample chunks from throughout the document, focusing on the body content."""
        if not chunks:
            return ""
        
        n = len(chunks)
        if n <= 5:
            return "\n\n".join(c["text"] for c in chunks)[:max_chars]
            
        indices = []
        # If we want to skip the noisy intro (authors, TOC), start from 10% in
        start_idx = int(n * 0.1) if skip_start and n > 10 else 0
        
        for i in range(1, 7):
            idx = start_idx + int((i / 7) * (n - start_idx))
            if idx < n:
                indices.append(idx)
                
        parts = []
        for i in sorted(list(set(indices))):
            # Clean each chunk — keep lines > 5 chars for presentations/bullets
            text = chunks[i]["text"]
            lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 5]
            if not lines:
                lines = [text[:300]] # Fallback to raw if filter was too aggressive
            parts.append("\n".join(lines))
            
        return "\n\n".join(parts)[:max_chars]

    def extract_hierarchy(self, text: str, title_hint: str = "", toc: list[list] = None) -> dict:
        """
        Ask LLM to extract a thematic topic map.
        """
        toc_hint = ""
        if toc:
            toc_lines = [f"- {t}" for l, t, p in toc[:20] if l == 1]
            toc_hint = "\n\nDOCUMENT CHAPTERS:\n" + "\n".join(toc_lines)

        prompt = f"""You are a Knowledge Graph specialist. Analyze the document segments and build a 1-to-1 THEMATIC TREE of the actual content.

GOAL: Map out the technical knowledge hierarchy.
(Example: For "Linear Algebra", nodes should be "Matrices", "Vector Spaces", etc.)

STRICT RULES:
1. NO METADATA: Do not extract authors, university names, or dates.
2. NO STRUCTURE: Do not extract "Introduction", "Summary", "Table of Contents", or "Slide X".
3. BRANCHING: 
   - "title" = Main Subject (e.g. "Linear Algebra")
   - "topics" = Major areas (e.g. "Matrices", "Linear Independence")
   - "subtopics" = Core details (e.g. "Determinant", "Inverse")

{toc_hint}

DOCUMENT TITLE CONTEXT:
{title_hint}

DOCUMENT CONTENT SEGMENTS:
{text}

Return ONLY valid JSON in this format:
{{
  "title": "Main Subject",
  "topics": [
    {{
      "name": "Major Concept Area",
      "subtopics": ["Specific Concept A", "Specific Concept B"]
    }}
  ]
}}"""

        try:
            response = requests.post(self.url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1024},
            }, timeout=90)
            response.raise_for_status()

            raw = response.json()["response"].strip()
            # find the JSON object
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                raw = raw[start:end]

            data = json.loads(raw)
            if "topics" not in data or not isinstance(data["topics"], list) or len(data["topics"]) == 0:
                raise ValueError("Incomplete hierarchy")
            return data

        except Exception as e:
            print(f"  [KG] LLM extraction failed: {e}, using fallback")
            return self._fallback_extract(text)

    def _hierarchy_to_entities(self, hierarchy: dict) -> list[dict]:
        """Convert hierarchy dict to flat entity list for GraphBuilder."""
        entities = []
        title = hierarchy.get("title", "Document Analysis")
        
        entities.append({
            "text": title,
            "type": "ROOT",
            "frequency": 10,
            "is_root": True,
        })

        for topic in hierarchy.get("topics", []):
            t_name = topic.get("name")
            if not t_name: continue
            
            entities.append({
                "text": t_name,
                "type": "MAIN_TOPIC",
                "frequency": 5,
                "parent": title,
            })

            for sub in topic.get("subtopics", []):
                if not sub: continue
                entities.append({
                    "text": sub,
                    "type": "SUBTOPIC",
                    "frequency": 2,
                    "parent": t_name,
                })

        return entities

    def _fallback_extract(self, text: str) -> dict:
        """Smarter fallback: try to find at least one subject from the first lines."""
        lines = [l for l in text.split("\n") if len(l) > 10]
        subject = lines[0][:30] if lines else "Document"
        return {
            "title": subject,
            "topics": [
                {"name": "Content Overview", "subtopics": ["Check Document Body", "Technical Concept"]}
            ]
        }