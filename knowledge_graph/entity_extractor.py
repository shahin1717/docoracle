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
            text = chunks[i]["text"]
            lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 5]
            
            # STRIP HEADERS/FOOTERS: Often contain university names or page numbers
            if len(lines) > 8:
                lines = lines[2:-2] # Skip top 2 and bottom 2 lines
                
            parts.append("\n".join(lines))
            
        return "\n\n".join(parts)[:max_chars]

    def extract_hierarchy(self, text: str, title_hint: str = "", toc: list[list] = None) -> dict:
        """
        Ask LLM to extract a thematic topic map with a retry mechanism.
        """
        if not text or len(text.strip()) < 50:
            return self._fallback_extract(text, "Document (No text found)")

        toc_hint = ""
        if toc:
            toc_lines = [f"- {t}" for l, t, p in toc[:20] if l == 1]
            toc_hint = "\n\nDOCUMENT CHAPTERS:\n" + "\n".join(toc_lines)

        prompt = f"""You are a Knowledge Graph specialist. Analyze the document segments and build a THEMATIC TREE of the content.

STRICT FILTERING RULES:
1. NO METADATA: NEVER extract university names, professor names, or dates.
2. NO STRUCTURE: Ignore "Introduction", "Summary", or generic words like "Definition" or "Conclusion".
3. TECHNICAL FOCUS: Extract only the core technical subjects (e.g., "Vector Space Properties", "Rank-Nullity Theorem").
4. CONSOLIDATION: Do not list multiple examples or exercises. Use at most ONE "Examples & Exercises" node per major topic.
5. DESCRIPTIVE NAMES: Ensure nodes have meaningful names (e.g., "Matrix Inverse Properties" instead of "Properties").

{toc_hint}
DOCUMENT TITLE CONTEXT: {title_hint}
DOCUMENT CONTENT:
{text}

Return ONLY valid JSON:
{{
  "title": "Main Subject",
  "topics": [
    {{ "name": "Major Concept", "subtopics": ["Concept Detail A", "Concept Detail B", "Practice Problems"] }}
  ]
}}"""

        for attempt in range(2):
            try:
                current_prompt = prompt if attempt == 0 else f"Extract a deep technical topic tree. JSON only: {{'title': '...', 'topics': [{{'name': '...', 'subtopics': [...]}}]}}. Text: {text[:2000]}"
                
                response = requests.post(self.url, json={
                    "model": self.model,
                    "prompt": current_prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 1024},
                }, timeout=90)
                response.raise_for_status()

                raw = response.json()["response"].strip()
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start != -1 and end > start:
                    raw = raw[start:end]

                data = json.loads(raw)
                if "topics" in data and len(data["topics"]) > 0:
                    return data
            except Exception as e:
                if attempt == 1:
                    print(f"  [KG] Both extraction attempts failed: {e}")
                continue

        return self._fallback_extract(text)

    def _hierarchy_to_entities(self, hierarchy: dict) -> list[dict]:
        """Convert hierarchy dict to flat entity list for GraphBuilder."""
        entities = []
        title = str(hierarchy.get("title", "Document Analysis"))
        
        entities.append({
            "text": title,
            "type": "ROOT",
            "frequency": 10,
            "is_root": True,
        })

        for topic in hierarchy.get("topics", []):
            # Topics can sometimes be strings or dicts depending on LLM hallucination
            if isinstance(topic, str):
                t_name = topic
                subtopics = []
            else:
                t_name = str(topic.get("name") or topic.get("topic") or "Concept")
                subtopics = topic.get("subtopics", [])

            if not t_name: continue
            
            entities.append({
                "text": t_name,
                "type": "MAIN_TOPIC",
                "frequency": 5,
                "parent": title,
            })

            # Post-processing: Limit "Example" or "Exercise" nodes to 1 per topic
            practice_nodes_count = 0
            for sub in subtopics:
                if not sub: continue
                
                # Handle cases where subtopic is a dict like {'name': 'Rank'}
                if isinstance(sub, dict):
                    sub_text = str(sub.get("name") or sub.get("topic") or sub.get("text") or list(sub.values())[0])
                else:
                    sub_text = str(sub)

                # Filter redundant practice nodes
                is_practice = any(word in sub_text.lower() for word in ["example", "exercise", "practice", "problem"])
                if is_practice:
                    practice_nodes_count += 1
                    if practice_nodes_count > 1:
                        continue # Skip subsequent practice nodes

                entities.append({
                    "text": sub_text,
                    "type": "SUBTOPIC",
                    "frequency": 2,
                    "parent": t_name,
                })

        return entities

    def _fallback_extract(self, text: str, default_title: str = "Document Analysis") -> dict:
        """Smarter fallback: extract keywords using simple heuristics."""
        import re
        from collections import Counter
        
        # Blacklist of words that should never be nodes (common metadata noise)
        blacklist = {
            "french", "azerbaijan", "azerbaijani", "university", "ufaz", "strasbourg",
            "department", "faculty", "professor", "student", "author", "email",
            "page", "figure", "table", "section", "chapter", "exercise", "solution"
        }
        
        # Extract potential keywords (capitalized words > 4 chars)
        words = re.findall(r'\b[A-Z][a-z]{4,}\b', text)
        common = [w for w, c in Counter(words).most_common(12) if w.lower() not in blacklist]
        
        lines = [l for l in text.split("\n") if len(l) > 10]
        title = lines[0][:40] if lines else default_title
        
        return {
            "title": title,
            "topics": [
                {
                    "name": "Key Concepts", 
                    "subtopics": common[:6] if common else ["Technical Content"]
                }
            ]
        }