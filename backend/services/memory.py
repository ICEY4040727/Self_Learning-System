"""Memory service using ChromaDB for vector storage"""

import os
import uuid

import chromadb
from chromadb.config import Settings


class MemoryService:
    """ChromaDB-based memory service for conversation history"""

    def __init__(self, persist_directory: str = "./chroma_data"):
        chroma_host = os.environ.get("CHROMA_HOST")
        if chroma_host:
            chroma_port = int(os.environ.get("CHROMA_PORT", "8000"))
            self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        else:
            self.client = chromadb.Client(Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False
            ))
        self.collection_name = "conversation_memory"

    def get_or_create_collection(self, session_id: str):
        """Get or create a collection for a specific session"""
        return self.client.get_or_create_collection(
            name=f"{self.collection_name}_{session_id}",
            metadata={"session_id": session_id}
        )

    def add_memory(self, session_id: str, content: str, metadata: dict = None):
        """Add a memory to the vector store"""
        collection = self.get_or_create_collection(session_id)

        memory_id = f"memory_{uuid.uuid4().hex[:16]}"

        collection.add(
            ids=[memory_id],
            documents=[content],
            metadatas=[metadata or {}]
        )

        return memory_id

    def retrieve(self, session_id: str, query: str, top_k: int = 3) -> list[dict]:
        """Retrieve relevant memories based on query"""
        collection = self.get_or_create_collection(session_id)

        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )

        memories = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                memories.append({
                    "id": results["ids"][0][i] if results.get("ids") else None,
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}
                })

        return memories

    def delete_memory(self, session_id: str, memory_id: str):
        """Delete a specific memory"""
        collection = self.get_or_create_collection(session_id)
        collection.delete(ids=[memory_id])

    def clear_session(self, session_id: str):
        """Clear all memories for a session"""
        import contextlib

        with contextlib.suppress(Exception):
            self.client.delete_collection(name=f"{self.collection_name}_{session_id}")

    def get_memory_count(self, session_id: str) -> int:
        """Get count of memories in session"""
        collection = self.get_or_create_collection(session_id)
        return collection.count()


# Global instance
memory_service = MemoryService()
