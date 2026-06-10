"""XHLS Brain: Self-Growing Engineer Knowledge Graph
Inherited from XDLS DesignBrain and extended for hacker-engineer architecture.

The fundamental learning operation: learn() → connect via tags → recall by relevance → reinforce by success.
"""
import json, os
from datetime import datetime


class EngineerBrain:
    """
    Knowledge graph engine for 小黑.

    Nodes = knowledge atoms (code patterns, content formulas, architecture decisions, security rules)
    Edges = auto-connections via shared tags
    Confidence = Bayesian prior (0.5) → reinforced by successful application
    """

    def __init__(self, brain_dir):
        self.dir = brain_dir
        self.memory_file = os.path.join(brain_dir, "synaptic_memory.json")
        self.skills_file = os.path.join(brain_dir, "skill_tree.json")
        self.memory = self._load(self.memory_file, {"nodes": [], "edges": []})
        self.skills = self._load(self.skills_file, {"techniques": {}, "domains": {}})

    def _load(self, path, default):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    def _save(self, data, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def learn(self, topic, content, source, tags=None, domain="general"):
        """
        Ingest new knowledge — the fundamental learning operation.

        Returns node_id for reinforcement.
        """
        node = {
            "id": f"node_{len(self.memory['nodes'])}",
            "topic": topic,
            "content": content[:2000],
            "source": source,
            "domain": domain,
            "tags": tags or [],
            "learned_at": datetime.now().isoformat(),
            "access_count": 0,
            "confidence": 0.5,  # Bayesian prior
            "reinforcement_history": [],
        }
        self.memory["nodes"].append(node)

        # Auto-connect to related nodes via tag overlap
        for existing in self.memory["nodes"][:-1]:
            overlap = set(node["tags"]) & set(existing.get("tags", []))
            if overlap:
                self.memory["edges"].append({
                    "from": node["id"],
                    "to": existing["id"],
                    "weight": len(overlap),
                    "shared_tags": list(overlap),
                })

        self._save(self.memory, self.memory_file)
        return node["id"]

    def recall(self, query_tags, domain=None, top_k=10):
        """
        Retrieve knowledge by tag relevance.

        Returns nodes sorted by score = tag_match * confidence.
        """
        results = []
        for node in self.memory["nodes"]:
            if domain and node.get("domain") != domain:
                continue
            score = len(set(query_tags) & set(node.get("tags", [])))
            if score > 0:
                node["access_count"] += 1
                results.append((score * node["confidence"], node))
        results.sort(key=lambda x: x[0], reverse=True)
        self._save(self.memory, self.memory_file)
        return [r[1] for r in results[:top_k]]

    def reinforce(self, node_id, success=True):
        """
        Reinforce or weaken a knowledge node.

        Success → confidence += 0.1 (max 1.0)
        Failure → confidence -= 0.05 (min 0.1)
        """
        for node in self.memory["nodes"]:
            if node["id"] == node_id:
                old_conf = node["confidence"]
                if success:
                    node["confidence"] = min(1.0, old_conf + 0.1)
                else:
                    node["confidence"] = max(0.1, old_conf - 0.05)
                node["reinforcement_history"].append({
                    "time": datetime.now().isoformat(),
                    "success": success,
                    "confidence_delta": node["confidence"] - old_conf,
                })
                break
        self._save(self.memory, self.memory_file)

    def grow_skill_tree(self, technique, domain, level):
        """Track skill development per technique."""
        if technique not in self.skills["techniques"]:
            self.skills["techniques"][technique] = {
                "level": "novice",
                "domains": [],
                "practice_count": 0,
            }
        t = self.skills["techniques"][technique]
        t["level"] = level
        if domain not in t["domains"]:
            t["domains"].append(domain)
        t["practice_count"] += 1
        self.skills["domains"][domain] = self.skills["domains"].get(domain, 0) + 1
        self._save(self.skills, self.skills_file)

    def find_weak_nodes(self, threshold=0.3):
        """Find knowledge nodes with low confidence — learning gaps."""
        return [n for n in self.memory["nodes"] if n["confidence"] <= threshold]

    def find_isolated_nodes(self):
        """Find nodes with no connections — islands of knowledge."""
        connected_ids = set()
        for edge in self.memory["edges"]:
            connected_ids.add(edge["from"])
            connected_ids.add(edge["to"])
        return [n for n in self.memory["nodes"] if n["id"] not in connected_ids]

    def summary(self):
        """Return brain health summary."""
        return {
            "knowledge_nodes": len(self.memory["nodes"]),
            "connections": len(self.memory["edges"]),
            "avg_confidence": round(
                sum(n["confidence"] for n in self.memory["nodes"]) / max(1, len(self.memory["nodes"])),
                3,
            ),
            "weak_nodes": len(self.find_weak_nodes()),
            "isolated_nodes": len(self.find_isolated_nodes()),
            "domains": list(self.skills["domains"].keys()),
            "techniques_tracked": len(self.skills["techniques"]),
        }


if __name__ == "__main__":
    brain = EngineerBrain(os.path.dirname(__file__))

    # Seed initial knowledge domains if empty
    if len(brain.memory["nodes"]) == 0:
        # Pipeline architecture
        brain.learn(
            topic="Pipeline: S1-S7 Content Creation Flow",
            content="7-stage pipeline: Topic → Script → Assets → Composite → Publish → BD → Operations",
            source="AGENTS.md",
            tags=["pipeline", "architecture", "content"],
            domain="architecture",
        )
        # Memory system
        brain.learn(
            topic="Memory: Correction Loop Pattern",
            content="Every user correction → permanent rule. Tagged: bug/style/process/rule/security/content.",
            source="memory.py",
            tags=["memory", "correction", "learning", "self-evolution"],
            domain="architecture",
        )
        # Security redline
        brain.learn(
            topic="Security: Data Safety Redlines",
            content="Non-XHLS files: read+mark only, no write/delete/move. 小黑 territory: full access.",
            source="AGENTS.md",
            tags=["security", "boundary", "redline"],
            domain="security",
        )
        # Multi-agent
        brain.learn(
            topic="Agents: 7-Person Hacker Engineer Team",
            content="Orchestrator + Writer + Artist + Producer + Voice + Editor + Marketing",
            source="AGENTS.md",
            tags=["agents", "parallel", "orchestration"],
            domain="architecture",
        )
        # Code patterns
        brain.learn(
            topic="Code: Atomic File I/O Pattern",
            content="temp file + atomic rename = crash-safe writes. Used in memory.py.",
            source="memory.py",
            tags=["code-pattern", "python", "io", "crash-safety"],
            domain="code",
        )

        print("[BRAIN] Seeded with initial knowledge nodes.")

    summary = brain.summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
