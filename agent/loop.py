"""Shared tool-calling executor loop.

Extracted so both the top-level AgentCore and delegated sub-agents run the exact
same execution semantics (tool calls, approval gating, action logging) over
whatever tool subset they're given. Wrapped with self-healing control plane.
"""
import json
import logging

from agent import registry, approvals, critic, policy, safety, trace
from agent.store import log_action
from llm.tool_client import complete_with_tools
from config import config

logger = logging.getLogger(__name__)

MAX_STEPS = 8


async def _healed_llm_call(messages, schemas):
    from agent.healing.orchestrator import heal_call, healing_enabled
    if not healing_enabled():
        return await complete_with_tools(messages, schemas)
    return await heal_call(
        lambda: complete_with_tools(messages, schemas),
        kind="llm",
        ctx={"circuit_key": "llm:tool_client", "tool_name": "llm"},
    )


async def _healed_tool_call(name, args, actor, step):
    from agent.healing.orchestrator import heal_call, healing_enabled
    from agent.healing.router import route_around

    async def _call():
        return await registry.call(name, args)

    if not healing_enabled():
        return await _call()

    result = await heal_call(
        _call,
        kind="tool",
        ctx={"tool_name": name, "args": args, "actor": actor, "step": step,
             "circuit_key": f"tool:{name}"},
    )

    # Handle substitution from healing orchestrator
    if isinstance(result, dict):
        if result.get("_substitute"):
            alt = result["_substitute"]
            logger.info(f"[loop] healing substituted {name} -> {alt}")
            return await registry.call(alt, args)
        if result.get("_degraded_response"):
            return {"error": result.get("error", ""), "degraded": result["_degraded_response"]}

    return result


async def execute_loop(messages: list, schemas: list, actor: str = "agent",
                       on_status=None, tools_used: list = None,
                       max_steps: int = MAX_STEPS, turn_id: str = None) -> str:
    """Run the tool-calling loop until the model returns a final answer."""
    from agent.healing.orchestrator import RecoveryBudget, set_budget, detect_stuck_loop
    from agent.healing import metacog as metacog_mod
    from agent.healing.checkpoint import checkpoint as save_checkpoint

    tools_used = tools_used if tools_used is not None else []
    set_budget(RecoveryBudget())
    recent_call_sigs = []
    history_text = ""

    for step in range(max_steps):
        try:
            resp = await _healed_llm_call(messages, schemas)
        except Exception as e:
            logger.error(f"[loop] LLM call failed after healing: {e}")
            from agent.healing.escalate import degrade
            return degrade(reason=str(e)[:200])

        messages.append(resp["raw"])
        calls = resp.get("tool_calls") or []
        if not calls:
            return (resp.get("content") or "").strip()

        for tc in calls:
            name, args, call_id = tc["name"], tc["arguments"], tc["id"]
            tools_used.append(name)

            # Stuck-loop detection
            sig = f"{name}:{json.dumps(args, sort_keys=True, default=str)[:100]}"
            recent_call_sigs.append(sig)
            if detect_stuck_loop(recent_call_sigs):
                logger.warning(f"[loop] stuck loop detected on {name}")
                from agent.healing.escalate import degrade
                return degrade(
                    reason=f"stuck loop on tool '{name}'",
                    partial_result=history_text[:500],
                )

            # Metacognitive anomaly check
            if getattr(config, "healing_metacog", True):
                step_text = f"call {name} with {json.dumps(args, default=str)[:200]}"
                anomaly = metacog_mod.score_step(history_text, step_text)
                if anomaly.get("anomaly"):
                    logger.debug(f"[loop] metacog anomaly on step {step}: {anomaly}")

            tool = registry.get(name)

            if on_status:
                try:
                    await on_status(f"⚙️ {name}…")
                except Exception:
                    pass

            if tool is None:
                # Try route-around for unknown tools
                from agent.healing.router import route_around
                alt = route_around(name)
                if alt:
                    name = alt
                    tool = registry.get(name)
                if tool is None:
                    result = {"error": f"Unknown tool: {name}"}
                else:
                    decision = policy.decide(tool, args)
                    if decision == "deny":
                        result = {"denied": f"Policy blocked '{name}'."}
                    elif decision == "approve":
                        check = await critic.precheck_action(name, args)
                        note = "" if check.get("ok", True) else check.get("note", "")
                        result = approvals.enqueue(name, args, risk_note=note)
                    else:
                        result = await _healed_tool_call(name, args, actor, step)
                        log_action(actor, name, args, json.dumps(result, default=str)[:1500])
                        result = safety.wrap_tool_result(name, result)
                    trace.add_tool_event(name, args, decision, result)
            else:
                decision = policy.decide(tool, args)
                if decision == "deny":
                    result = {"denied": f"Policy blocked '{name}'."}
                elif decision == "approve":
                    check = await critic.precheck_action(name, args)
                    note = "" if check.get("ok", True) else check.get("note", "")
                    result = approvals.enqueue(name, args, risk_note=note)
                else:
                    result = await _healed_tool_call(name, args, actor, step)
                    log_action(actor, name, args, json.dumps(result, default=str)[:1500])
                    result = safety.wrap_tool_result(name, result)

                trace.add_tool_event(name, args, decision, result)

            # Checkpoint after each tool action
            if turn_id:
                try:
                    save_checkpoint(turn_id, step, {
                        "tool": name, "args": args,
                        "result_preview": str(result)[:300],
                        "messages_len": len(messages),
                    })
                except Exception:
                    pass

            history_text += f"\n{name}: {str(result)[:200]}"
            metacog_mod.update_prototype(actor, history_text[-500:])

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result, default=str)[:6500],
            })

    return "I did a lot of work but didn't wrap up cleanly. Ask me to continue."
