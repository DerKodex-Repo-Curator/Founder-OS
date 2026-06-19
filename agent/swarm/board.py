"""Blackboard / stigmergic coordination (bMAS-style control unit)."""
import json
import logging

from agent import subagent, store
from config import config
from llm.router import complete

logger = logging.getLogger(__name__)


class SwarmBoard:
    """Shared blackboard for stigmergic agent coordination."""

    def __init__(self, run_id: int, topic: str):
        self.run_id = run_id
        self.topic = topic

    def post(self, agent: str, entry_type: str, content: str, salience: float = 1.0,
             parent_id: int = None) -> int:
        return store.board_post(self.run_id, agent, entry_type, content, salience, parent_id)

    def read(self, limit: int = 20, min_salience: float = 0.0) -> list:
        return store.board_read(self.run_id, limit, min_salience)

    def claim(self, agent: str, task_desc: str) -> int:
        return self.post(agent, "claim", task_desc, salience=1.5)

    def validate(self, entry_id: int, agent: str, approved: bool, note: str = "") -> int:
        content = json.dumps({"entry_id": entry_id, "approved": approved, "note": note})
        salience = 2.0 if approved else 0.5
        return self.post(agent, "validation", content, salience=salience, parent_id=entry_id)

    def render(self) -> str:
        entries = self.read(limit=30)
        if not entries:
            return "(empty board)"
        lines = []
        for e in entries:
            lines.append(f"[{e['entry_type']}|{e['agent']}|s={e['salience']:.1f}] {e['content'][:300]}")
        return "\n".join(lines)


async def _select_agents(board: SwarmBoard, specialists: list, k: int = 3) -> list:
    """LLM control unit picks which agents to activate this round."""
    board_text = board.render()
    messages = [
        {"role": "system", "content":
            "You are the blackboard control unit. Select which specialist agents "
            "should act this round based on the board state. Respond ONLY with JSON."},
        {"role": "user", "content": f"""TOPIC: {board.topic}

BOARD:
{board_text[:3000]}

AVAILABLE: {specialists}

Respond: {{"agents": ["name1", "name2"], "rationale": "..."}}"""},
    ]
    try:
        raw = await complete(messages, task_type="analysis", max_tokens=200)
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        chosen = [a for a in data.get("agents", []) if a in specialists][:k]
        return chosen or specialists[:k]
    except Exception:
        return specialists[:k]


async def run_blackboard_round(topic: str, max_rounds: int = None) -> dict:
    """Run multi-round blackboard coordination until consensus or budget."""
    max_rounds = max_rounds or getattr(config, "swarm_max_rounds", 10)
    run_id = store.create_swarm_run(topic[:500], "blackboard", max_rounds)
    board = SwarmBoard(run_id, topic)
    specialists = subagent.list_specialists()
    board.post("control_unit", "init", f"Topic: {topic}", salience=2.0)

    for rnd in range(max_rounds):
        chosen = await _select_agents(board, specialists)
        for agent_name in chosen:
            task = (
                f"Blackboard round {rnd + 1}. Topic: {topic}\n\n"
                f"BOARD STATE:\n{board.render()[:2500]}\n\n"
                "Post your finding, plan, or critique. Be specific and actionable."
            )
            r = await subagent.run_subagent(agent_name, task)
            board.post(agent_name, "finding", r.get("result", "")[:2000], salience=1.0)

        # Check for consensus signal
        validations = [e for e in board.read(10) if e["entry_type"] == "validation"]
        if len(validations) >= 2:
            approved = sum(1 for v in validations if "approved\": true" in v["content"] or '"approved": true' in v["content"])
            if approved >= len(validations) * 0.6:
                break

    synthesis = board.render()
    store.finish_swarm_run(run_id, "done", synthesis[:4000])
    return {"run_id": run_id, "rounds": rnd + 1, "board": board.read(50), "synthesis": synthesis}
