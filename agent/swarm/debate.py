"""Multi-agent debate, maker-checker, and consensus with anti-sycophancy."""
import logging

from agent import subagent, critic
from config import config
from llm.router import complete

logger = logging.getLogger(__name__)

_DEBATE_ROLES = {
    "advocate": "You strongly advocate FOR the proposed approach. Give concrete reasons.",
    "skeptic": "You challenge the proposal. Find flaws, risks, and counterarguments. Be rigorous, not contrarian for its own sake.",
    "judge": "You synthesize the debate fairly. Weigh both sides, resolve conflicts, give a clear recommendation.",
    "maker": "You produce the best possible draft/output for the task.",
    "checker": "You review the draft critically. Flag errors, gaps, and improvements. Do NOT simply agree.",
}


async def run_debate(topic: str, rounds: int = None, roles: list = None) -> dict:
    """Run structured multi-agent debate with a judge synthesis."""
    rounds = rounds or getattr(config, "debate_rounds", 2)
    roles = roles or ["advocate", "skeptic"]
    transcript = []
    positions = {}

    for rnd in range(rounds):
        for role in roles:
            brief = _DEBATE_ROLES.get(role, f"You are the {role}.")
            prior = "\n".join(f"[{t['role']}]: {t['content'][:400]}" for t in transcript[-6:])
            prior_block = f"PRIOR ARGUMENTS:\n{prior}\n\n" if prior else ""
            task = (
                f"{brief}\n\nTOPIC:\n{topic}\n\n"
                f"{prior_block}"
                f"Round {rnd + 1}/{rounds}. Be specific. Do not repeat prior points verbatim."
            )
            r = await subagent.run_subagent("analyst", task)
            content = r.get("result", "")
            transcript.append({"round": rnd + 1, "role": role, "content": content})
            positions[f"{role}_r{rnd+1}"] = content

    # Judge synthesis with anti-sycophancy instruction
    judge_task = (
        f"{_DEBATE_ROLES['judge']}\n\n"
        "IMPORTANT: Do not default to agreement. If the skeptic raised valid points, "
        "acknowledge them. If evidence is insufficient, say so.\n\n"
        f"TOPIC: {topic}\n\nDEBATE TRANSCRIPT:\n"
        + "\n\n".join(f"[{t['role']} r{t['round']}]: {t['content'][:600]}" for t in transcript)
    )
    judge_result = await subagent.run_subagent("analyst", judge_task)
    verdict = judge_result.get("result", "")

    # Critic verification
    verification = await critic.verify_answer(topic, verdict, str(transcript)[:800])

    return {
        "topic": topic,
        "rounds": rounds,
        "transcript": transcript,
        "verdict": verdict,
        "verification": verification,
    }


async def run_maker_checker(task: str, max_iterations: int = 3) -> dict:
    """Maker-checker loop until critic approves or max iterations."""
    draft = ""
    history = []

    for i in range(max_iterations):
        maker_task = (
            f"{_DEBATE_ROLES['maker']}\n\nTASK:\n{task}\n"
            + (f"\nPrior draft to improve:\n{draft[:1500]}" if draft else "")
            + (f"\nChecker feedback:\n{history[-1]['feedback']}" if history else "")
        )
        maker = await subagent.run_subagent("analyst", maker_task)
        draft = maker.get("result", "")

        checker_task = (
            f"{_DEBATE_ROLES['checker']}\n\nTASK:\n{task}\n\nDRAFT:\n{draft[:2000]}\n"
            "Respond with JSON: {\"approved\": true/false, \"feedback\": \"...\"}"
        )
        checker = await subagent.run_subagent("analyst", checker_task)
        feedback = checker.get("result", "")

        approved = "approved\": true" in feedback.lower() or '"approved": true' in feedback.lower()
        history.append({"iteration": i + 1, "draft": draft[:500], "feedback": feedback[:500], "approved": approved})

        if approved:
            break

    verification = await critic.verify_answer(task, draft, str(history)[:600])
    return {"task": task, "final_draft": draft, "iterations": len(history), "history": history, "verification": verification}
