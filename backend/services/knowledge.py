import json
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, attributes

from backend.models.models import Knowledge


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_concept_id(name: str) -> str:
    lowered = name.strip().lower()
    lowered = re.sub(r"\s+", "_", lowered)
    lowered = re.sub(r"[^0-9a-z_\u4e00-\u9fff-]", "", lowered)
    return lowered[:64] or "concept"


def _extract_concepts(text: str) -> list[str]:
    stop_words = {
        "请先在设置中配置api",
        "api",
        "key",
        "please",
        "hello",
        "teacher",
        "student",
    }
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}", text or "")
    unique: list[str] = []
    for token in tokens:
        if token.lower() in stop_words:
            continue
        if token not in unique:
            unique.append(token)
        if len(unique) >= 3:
            break
    return unique


def _default_graph() -> dict[str, Any]:
    return {"concepts": {}, "episodes": []}


class KnowledgeService:
    def ensure_world_knowledge(self, db: Session, world_id: int) -> Knowledge:
        row = db.query(Knowledge).filter(Knowledge.world_id == world_id).first()
        if row is None:
            row = Knowledge(world_id=world_id, graph=_default_graph())
            db.add(row)
            db.flush()
        if not isinstance(row.graph, dict):
            row.graph = _default_graph()
            db.flush()
        return row

    def get_knowledge(self, db: Session, world_id: int) -> dict[str, Any]:
        row = self.ensure_world_knowledge(db, world_id)
        graph = row.graph if isinstance(row.graph, dict) else _default_graph()
        graph.setdefault("concepts", {})
        graph.setdefault("episodes", [])
        return graph

    def _filter_graph_by_time(
        self,
        graph: dict[str, Any],
        checkpoint_time: str | None = None,
        session_id: int | None = None,
    ) -> dict[str, Any]:
        checkpoint_dt = _parse_iso_datetime(checkpoint_time)
        if checkpoint_dt is None:
            return graph

        concepts = graph.get("concepts", {})
        filtered_concepts: dict[str, Any] = {}
        for concept_id, concept in concepts.items():
            if not isinstance(concept, dict):
                continue
            t_valid = _parse_iso_datetime(concept.get("t_valid"))
            t_invalid = _parse_iso_datetime(concept.get("t_invalid"))
            visible_by_checkpoint = True
            if t_valid and t_valid > checkpoint_dt:
                visible_by_checkpoint = False
            if t_invalid and t_invalid <= checkpoint_dt:
                visible_by_checkpoint = False

            visible_by_session = False
            if session_id is not None:
                for episode in concept.get("episodes") or []:
                    if not isinstance(episode, dict):
                        continue
                    if episode.get("session_id") != session_id:
                        continue
                    episode_time = _parse_iso_datetime(episode.get("time"))
                    if episode_time is None or episode_time >= checkpoint_dt:
                        visible_by_session = True
                        break

            if not (visible_by_checkpoint or visible_by_session):
                continue

            copied = dict(concept)
            copied_edges = {}
            for target, edge in (concept.get("edges") or {}).items():
                if isinstance(edge, str):
                    copied_edges[target] = {"type": edge}
                    continue
                if not isinstance(edge, dict):
                    continue
                edge_valid = _parse_iso_datetime(edge.get("t_valid"))
                edge_invalid = _parse_iso_datetime(edge.get("t_invalid"))
                edge_session_id = edge.get("session_id")
                same_session = session_id is not None and edge_session_id == session_id
                if edge_valid and edge_valid > checkpoint_dt and not same_session:
                    continue
                if edge_invalid and edge_invalid <= checkpoint_dt and not same_session:
                    continue
                copied_edges[target] = dict(edge)
            copied["edges"] = copied_edges
            filtered_concepts[concept_id] = copied

        return {
            "concepts": filtered_concepts,
            "episodes": graph.get("episodes", []),
        }

    def get_relevant_context(
        self,
        db: Session,
        world_id: int,
        query: str,
        checkpoint_time: str | None = None,
        session_id: int | None = None,
    ) -> str:
        graph = self.get_knowledge(db, world_id)
        filtered = self._filter_graph_by_time(graph, checkpoint_time, session_id=session_id)
        concepts = filtered.get("concepts", {})
        if not concepts:
            return ""

        query_tokens = _extract_concepts(query.lower())
        if not query_tokens:
            return json.dumps(self._limit_graph(filtered), ensure_ascii=False)

        ranked: list[tuple[int, str, dict[str, Any]]] = []
        for concept_id, concept in concepts.items():
            haystack = " ".join(
                [
                    concept_id,
                    str(concept.get("name", "")),
                    str(concept.get("content", "")),
                ]
            ).lower()
            score = sum(1 for token in query_tokens if token.lower() in haystack)
            if score > 0:
                ranked.append((score, concept_id, concept))

        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = {
            "concepts": {concept_id: concept for _, concept_id, concept in ranked[:8]},
            "episodes": filtered.get("episodes", []),
        }
        if not selected["concepts"]:
            selected = self._limit_graph(filtered)
        return json.dumps(selected, ensure_ascii=False)

    def _limit_graph(self, graph: dict[str, Any], max_nodes: int = 20, max_episodes: int = 30) -> dict[str, Any]:
        concepts = graph.get("concepts") or {}
        if not isinstance(concepts, dict):
            return {"concepts": {}, "episodes": []}

        ranked = sorted(
            concepts.items(),
            key=lambda item: float(item[1].get("mastery", 0.0)) if isinstance(item[1], dict) else 0.0,
            reverse=True,
        )[:max_nodes]
        selected_ids = {concept_id for concept_id, _ in ranked}

        limited_concepts: dict[str, Any] = {}
        for concept_id, concept in ranked:
            if not isinstance(concept, dict):
                continue
            copied = dict(concept)
            copied_edges = {}
            for target, edge in (concept.get("edges") or {}).items():
                if target in selected_ids:
                    copied_edges[target] = edge
            copied["edges"] = copied_edges
            limited_concepts[concept_id] = copied

        episodes = graph.get("episodes") or []
        episodes = episodes[-max_episodes:] if isinstance(episodes, list) else []

        return {"concepts": limited_concepts, "episodes": episodes}

    def update_after_chat(
        self,
        db: Session,
        world_id: int,
        user_msg: str,
        teacher_reply: str,
        emotion: dict[str, Any] | None,
        session_id: int | None = None,
    ) -> dict[str, Any]:
        row = self.ensure_world_knowledge(db, world_id)
        graph = self.get_knowledge(db, world_id)
        concepts = graph.setdefault("concepts", {})
        episodes = graph.setdefault("episodes", [])

        now = datetime.now(UTC).isoformat()
        candidates = _extract_concepts(f"{user_msg} {teacher_reply}")
        if not candidates and user_msg.strip():
            candidates = [user_msg.strip()[:12]]

        emotion_type = (emotion or {}).get("emotion_type", "neutral")
        delta_map = {
            "excitement": 0.10,
            "satisfaction": 0.08,
            "curiosity": 0.06,
            "neutral": 0.04,
            "confusion": -0.01,
            "frustration": -0.03,
            "anxiety": -0.02,
            "boredom": 0.0,
        }
        mastery_delta = delta_map.get(emotion_type, 0.03)

        touched: list[str] = []
        for name in candidates:
            concept_id = _normalize_concept_id(name)
            if not concept_id:
                continue

            concept = concepts.get(concept_id)
            if concept is None:
                concept = {
                    "type": "knowledge",
                    "name": name,
                    "mastery": max(0.0, min(1.0, 0.2 + mastery_delta)),
                    "status": "new",
                    "bloom_level": "remember",
                    "content": f"来自对话的概念：{name}",
                    "t_valid": now,
                    "t_invalid": None,
                    "episodes": [],
                    "edges": {},
                }
                concepts[concept_id] = concept
            else:
                old_mastery = float(concept.get("mastery", 0.2))
                new_mastery = max(0.0, min(1.0, old_mastery + mastery_delta))
                concept["mastery"] = round(new_mastery, 3)
                if concept["mastery"] >= 0.8:
                    concept["status"] = "mastered"
                elif concept["mastery"] >= 0.4:
                    concept["status"] = "learning"
                else:
                    concept["status"] = concept.get("status", "confused")
                concept.setdefault("episodes", [])
                concept.setdefault("edges", {})
                concept.setdefault("t_valid", now)
                concept["t_invalid"] = None

            if session_id is not None:
                concept["last_session_id"] = session_id

            concept_episode: dict[str, Any] = {"type": "chat", "time": now}
            if session_id is not None:
                concept_episode["session_id"] = session_id
            concept["episodes"].append(concept_episode)
            touched.append(concept_id)

        episode_record: dict[str, Any] = {
            "time": now,
            "type": "chat",
            "emotion": emotion_type,
            "concepts": touched,
        }
        if session_id is not None:
            episode_record["session_id"] = session_id
        episodes.append(episode_record)

        row.graph = graph
        attributes.flag_modified(row, "graph")
        db.flush()
        return {"updated_concepts": touched}

    def to_d3_graph(
        self,
        db: Session,
        world_id: int,
        checkpoint_time: str | None = None,
        session_id: int | None = None,
    ) -> dict[str, Any]:
        graph = self.get_knowledge(db, world_id)
        filtered = self._filter_graph_by_time(graph, checkpoint_time, session_id=session_id)
        concepts = filtered.get("concepts", {})

        nodes = []
        for concept_id, concept in concepts.items():
            nodes.append(
                {
                    "id": concept_id,
                    "name": concept.get("name", concept_id),
                    "mastery": float(concept.get("mastery", 0.0)),
                    "status": concept.get("status", "new"),
                    "type": concept.get("type", "knowledge"),
                }
            )

        visible_ids = {node["id"] for node in nodes}
        edges = []
        for concept_id, concept in concepts.items():
            for target, edge in (concept.get("edges") or {}).items():
                if target not in visible_ids:
                    continue
                edge_type = edge if isinstance(edge, str) else edge.get("type", "related_to")
                edges.append(
                    {
                        "source": concept_id,
                        "target": target,
                        "type": edge_type,
                    }
                )

        return {"nodes": nodes, "edges": edges, "links": edges}


knowledge_service = KnowledgeService()
