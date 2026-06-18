"""Dynamic peer handoff (OpenAI Swarm style) with strict bounds."""
import logging

from agent import subagent
from config import config

logger = logging.getLogger(__name__)

# In-memory handoff sessions (per process)
_SESSIONS: dict = {}


class HandoffSession:
    """Tracks a dynamic handoff chain with loop detection."""

    def __init__(self, session_id: str, goal: str, max_handoffs: int = None):
        self.session_id = session_id
        self.goal = goal
        self.max_handoffs = max_handoffs or getattr(config, "swarm_max_handoffs", 5)
        self.chain: list = []  # [(specialist, task_snippet)]
        self.context = ""
        self.handoff_count = 0
        self.done = False
        self.final_result = ""

    def _would_loop(self, specialist: str) -> bool:
        """Detect A->B->A loops."""
        if len(self.chain) < 2:
            return False
        recent = [s for s, _ in self.chain[-3:]]
        if recent.count(specialist) >= 2:
            return True
        if len(self.chain) >= 2 and self.chain[-1][0] == specialist and self.chain[-2][0] == specialist:
            return True
        return False

    async def handoff(self, to_specialist: str, reason: str = "", task: str = "") -> dict:
        if self.done:
            return {"error": "Session already completed.", "result": self.final_result}
        if self.handoff_count >= self.max_handoffs:
            self.done = True
            return {
                "error": f"Max handoffs ({self.max_handoffs}) reached.",
                "chain": self.chain,
                "result": self.final_result or self.context,
            }
        if to_specialist not in subagent.list_specialists():
            return {"error": f"Unknown specialist '{to_specialist}'.", "options": subagent.list_specialists()}
        if self._would_loop(to_specialist):
            self.done = True
            return {
                "error": "Handoff loop detected — terminating chain.",
                "chain": self.chain,
                "result": self.context,
            }

        full_task = task or self.goal
        if self.context:
            full_task = f"{full_task}\n\nContext from prior agents:\n{self.context[:3000]}"
        if reason:
            full_task = f"Handoff reason: {reason}\n\n{full_task}"

        result = await subagent.run_subagent(to_specialist, full_task)
        self.handoff_count += 1
        self.chain.append((to_specialist, full_task[:200]))
        self.context = result.get("result", str(result))
        self.final_result = self.context
        return {
            "session_id": self.session_id,
            "handoff_count": self.handoff_count,
            "specialist": to_specialist,
            "result": self.context,
            "remaining_handoffs": self.max_handoffs - self.handoff_count,
        }

    def complete(self, result: str = "") -> dict:
        self.done = True
        if result:
            self.final_result = result
        return {"session_id": self.session_id, "chain": self.chain, "result": self.final_result}


def create_handoff_session(goal: str, session_id: str = None) -> HandoffSession:
    import uuid
    sid = session_id or str(uuid.uuid4())[:12]
    session = HandoffSession(sid, goal)
    _SESSIONS[sid] = session
    return session


def get_handoff_session(session_id: str) -> HandoffSession:
    return _SESSIONS.get(session_id)


async def run_handoff_chain(goal: str, start_specialist: str = "researcher") -> dict:
    """Convenience: start a handoff session and run first specialist."""
    session = create_handoff_session(goal)
    first = await session.handoff(start_specialist, task=goal)
    return {"session_id": session.session_id, **first}
