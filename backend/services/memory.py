"""Knowledge service — stub for Phase 1 replacement.

Previously used ChromaDB for vector memory. Now a no-op stub that
returns empty results. Phase 1 (#124) will implement JSON-based
knowledge storage in SQLite.
"""


class MemoryService:
    """Stub memory service — all methods return empty/no-op."""

    def add_memory(self, session_id: str, content: str, metadata: dict | None = None) -> str:
        return f"stub_{session_id}"

    def retrieve(self, session_id: str, query: str, top_k: int = 3) -> list[dict]:
        return []

    def delete_memory(self, session_id: str, memory_id: str):
        pass

    def clear_session(self, session_id: str):
        pass

    def get_memory_count(self, session_id: str) -> int:
        return 0


# Global instance
memory_service = MemoryService()
