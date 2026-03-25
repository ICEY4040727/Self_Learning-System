"""Knowledge graph service using Graphiti for temporal knowledge graphs.

Wraps Graphiti to build and query per-user knowledge graphs from
learning conversations. Integrates with the existing ChromaDB memory
service — ChromaDB handles short-term semantic recall, Graphiti handles
structured concept relationships and temporal knowledge evolution.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid crash when graphiti is not installed
_graphiti_available = False
try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF
    _graphiti_available = True
except ImportError:
    logger.info("graphiti-core not installed, knowledge graph features disabled")


class KnowledgeGraphService:
    """Graphiti-based knowledge graph for tracking learner concepts."""

    def __init__(self):
        self._uri = "bolt://localhost:7687"
        self._user = "neo4j"
        self._password = "socratic_learning"
        self._graphiti: Optional[Any] = None
        self._initialized = False

    def configure(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "socratic_learning",
    ):
        """Set connection parameters before calling initialize()."""
        self._uri = neo4j_uri
        self._user = neo4j_user
        self._password = neo4j_password

    async def initialize(self):
        """Connect to Neo4j and build indices. Call once on startup."""
        if not _graphiti_available:
            logger.warning("Graphiti not available, skipping initialization")
            return

        try:
            self._graphiti = Graphiti(
                uri=self._uri,
                user=self._user,
                password=self._password,
            )
            await self._graphiti.build_indices_and_constraints()
            self._initialized = True
            logger.info("Knowledge graph service initialized")
        except Exception as e:
            logger.error("Failed to initialize knowledge graph: %s", e)
            self._initialized = False

    async def close(self):
        """Close connection on shutdown."""
        if self._graphiti:
            await self._graphiti.close()

    @property
    def available(self) -> bool:
        return self._initialized and self._graphiti is not None

    def _group_id(self, user_id: int, subject_id: int) -> str:
        """Generate partition key per user+subject."""
        return f"user_{user_id}_subject_{subject_id}"

    async def add_conversation_turn(
        self,
        user_id: int,
        subject_id: int,
        user_message: str,
        teacher_response: str,
        session_id: int,
    ) -> dict:
        """
        Add a conversation turn to the knowledge graph.
        Graphiti extracts concepts and relationships automatically.
        """
        if not self.available:
            return {"status": "disabled"}

        group_id = self._group_id(user_id, subject_id)
        now = datetime.now(timezone.utc)

        try:
            # Add user message
            await self._graphiti.add_episode(
                name=f"session_{session_id}_user_{now.timestamp():.0f}",
                episode_body=f"student: {user_message}",
                source_description="learning_conversation",
                source=EpisodeType.message,
                reference_time=now,
                group_id=group_id,
            )

            # Add teacher response
            result = await self._graphiti.add_episode(
                name=f"session_{session_id}_teacher_{now.timestamp():.0f}",
                episode_body=f"teacher: {teacher_response}",
                source_description="learning_conversation",
                source=EpisodeType.message,
                reference_time=now,
                group_id=group_id,
            )

            return {
                "status": "ok",
                "nodes_created": len(result.nodes),
                "edges_created": len(result.edges),
                "concepts": [n.name for n in result.nodes],
            }
        except Exception as e:
            logger.error("Failed to add conversation to knowledge graph: %s", e)
            return {"status": "error", "message": str(e)}

    async def get_relevant_knowledge(
        self,
        user_id: int,
        subject_id: int,
        query: str,
        num_results: int = 5,
    ) -> str:
        """
        Search the knowledge graph for facts relevant to the current query.
        Returns a formatted string for injection into the dynamic prompt layer.
        """
        if not self.available:
            return ""

        group_id = self._group_id(user_id, subject_id)

        try:
            edges = await self._graphiti.search(
                query=query,
                group_ids=[group_id],
                num_results=num_results,
            )

            if not edges:
                return ""

            lines = []
            for e in edges:
                validity = ""
                if e.invalid_at:
                    validity = " (已过时)"
                lines.append(f"- {e.fact}{validity}")

            return "\n".join(lines)
        except Exception as e:
            logger.error("Knowledge graph search failed: %s", e)
            return ""

    async def get_knowledge_snapshot(
        self,
        user_id: int,
        subject_id: int,
        limit: int = 50,
    ) -> dict:
        """
        Get a snapshot of the learner's knowledge graph for a subject.
        Used to populate LearnerProfile.knowledge_graph.
        """
        if not self.available:
            return {}

        group_id = self._group_id(user_id, subject_id)

        try:
            from graphiti_core.nodes import EntityNode
            from graphiti_core.edges import EntityEdge

            nodes = await EntityNode.get_by_group_ids(
                self._graphiti.driver, group_ids=[group_id], limit=limit
            )
            edges = await EntityEdge.get_by_group_ids(
                self._graphiti.driver, group_ids=[group_id], limit=limit
            )

            return {
                "concepts": [
                    {"name": n.name, "summary": n.summary}
                    for n in nodes
                ],
                "relationships": [
                    {
                        "fact": e.fact,
                        "relation": e.name,
                        "valid": e.invalid_at is None,
                    }
                    for e in edges
                ],
            }
        except Exception as e:
            logger.error("Knowledge snapshot failed: %s", e)
            return {}


# Global instance (lazy initialized)
knowledge_graph_service = KnowledgeGraphService()
