import sqlite3
import json
from pathlib import Path


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    title       TEXT,
    file_type   TEXT,
    page_num    INTEGER,
    chunk_index INTEGER,
    text        TEXT NOT NULL,
    token_count INTEGER,
    metadata    TEXT
);
"""


class MetadataStore:
    """
    Stores chunk text and metadata in SQLite.
    FAISS stores vectors, this stores everything else.
    Keyed by chunk_id so the two stores stay in sync.
    """

    def __init__(self, db_path: str | Path = "data/docs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(CREATE_TABLE)
        self._conn.commit()

    def insert_chunks(self, chunks: list[dict]):
        """
        Each dict must have: chunk_id, source_path, title, file_type,
        page_num, chunk_index, text, token_count, metadata (dict).
        """
        rows = [
            (
                c["chunk_id"],
                c["source_path"],
                c.get("title", ""),
                c.get("file_type", ""),
                c.get("page_num"),
                c.get("chunk_index", 0),
                c["text"],
                c.get("token_count", 0),
                json.dumps(c.get("metadata", {})),
            )
            for c in chunks
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?,?,?)", rows
        )
        self._conn.commit()

    def get_chunk(self, chunk_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_chunks(self, chunk_ids: list[str]) -> list[dict]:
        placeholders = ",".join("?" * len(chunk_ids))
        rows = self._conn.execute(
            f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})", chunk_ids
        ).fetchall()
        by_id = {r[0]: self._row_to_dict(r) for r in rows}
        # Return in the same order as chunk_ids
        return [by_id[cid] for cid in chunk_ids if cid in by_id]

    def get_by_source(self, source_path: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM chunks WHERE source_path = ? ORDER BY chunk_index",
            (source_path,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete_source(self, source_path: str):
        self._conn.execute(
            "DELETE FROM chunks WHERE source_path = ?", (source_path,)
        )
        self._conn.commit()

    def _row_to_dict(self, row) -> dict:
        return {
            "chunk_id":    row[0],
            "source_path": row[1],
            "title":       row[2],
            "file_type":   row[3],
            "page_num":    row[4],
            "chunk_index": row[5],
            "text":        row[6],
            "token_count": row[7],
            "metadata":    json.loads(row[8]),
        }

    def close(self):
        self._conn.close()