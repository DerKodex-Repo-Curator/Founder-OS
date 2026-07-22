#!/usr/bin/env python3
"""Generate the Founder OS teaching guide (4000+ lines)."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

import agent.tools  # noqa: F401
from agent import registry

OUT = os.path.join(os.path.dirname(__file__), "FOUNDER_OS_COMPLETE_TEACHING_GUIDE.md")
tools = sorted(registry.all_tools(), key=lambda t: (t.category, t.name))
cats = {}
for t in tools:
    cats.setdefault(t.category, []).append(t)

lines = []


def w(s=""):
    lines.append(s)


def section(title, level=2):
    w()
    w("#" * level + " " + title)
    w()


def diagram(mermaid_code):
    w("```mermaid")
    w(mermaid_code)
    w("```")
    w()


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
w("<!--")
w("  Founder OS — Complete Teaching Guide")
w("  Purpose: Teach a friend from zero to production-grade understanding for Amazon SDE interviews.")
w(f"  Generated tool count: {len(tools)}")
w("  Location: docs/teaching-guide/FOUNDER_OS_COMPLETE_TEACHING_GUIDE.md")
w("-->")
w()
w("# Founder OS — Complete Teaching Guide")
w()
w("> **Audience:** Someone preparing for an Amazon SDE-2 interview who must explain, maintain, and scale Founder OS in production.")
w(">")
w("> **Goal:** Teach every concept from first principles through advanced agentic architecture — with diagrams, code paths, interview answers, and teaching scripts.")
w(">")
w(f"> **Verified runtime facts:** {len(tools)} registered tools, custom ReAct loop (not LangGraph for main agent), Chroma/Qdrant + SQLite hybrid memory, Telegram long-polling, APScheduler proactive jobs.")
w()
w("---")
w()
w("## How to use this document")
w()
w("1. **Read Parts 0–3 first** — vocabulary and architecture (1–2 hours).")
w("2. **Walk through Part 4 with a running bot** — send Telegram messages while tracing `data/traces/*.jsonl`.")
w("3. **Deep-dive Parts 5–14** — one subsystem per study session.")
w("4. **Part 18 is your interview crib sheet** — rehearse aloud using the STAR-format answers.")
w("5. **Use the mermaid diagrams** — draw them on a whiteboard from memory before the interview.")
w()
w("---")
w()
w("## Table of Contents")
w()
toc = [
    ("Part 0", "Prerequisites & mental model"),
    ("Part 1", "What is Founder OS? (Basics)"),
    ("Part 2", "Complete glossary — every term defined"),
    ("Part 3", "System architecture (diagrams)"),
    ("Part 4", "The turn lifecycle — step by step"),
    ("Part 5", "Agentic core deep dive"),
    ("Part 6", f"Complete tool catalog ({len(tools)} tools)"),
    ("Part 7", "Memory brain & all RAG variants"),
    ("Part 8", "Gates, HITL, policy & safety"),
    ("Part 9", "Telegram interface"),
    ("Part 10", "Scheduler & proactive autonomy"),
    ("Part 11", "External integrations"),
    ("Part 12", "LECE — Lived-Experience Cognitive Engine"),
    ("Part 13", "Multi-agent swarm orchestration"),
    ("Part 14", "Self-healing control plane"),
    ("Part 15", "LLM routing, caching & cost"),
    ("Part 16", "Data model — every table"),
    ("Part 17", "File-by-file reference"),
    ("Part 18", "Amazon interview prep (Q-B01–Q-B05)"),
    ("Part 19", "Additional practice questions"),
    ("Part 20", "Teaching walkthrough scripts"),
    ("Part 21", "Failure modes & debugging"),
    ("Part 22", "Scaling to 10,000 founders on AWS"),
    ("Appendix A", "Environment variables"),
    ("Appendix B", "Concept → code map"),
    ("Appendix C", "Eval suite & quality bar"),
]
for part, title in toc:
    w(f"- [{part}: {title}](#{part.lower().replace(' ', '-').replace('—', '').replace('(', '').replace(')', '').replace('–', '')}-{title.lower().replace(' ', '-').replace('—', '').replace('(', '').replace(')', '').replace('&', '').replace('–', '')})")
w()
w("---")

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

APPROVAL_TOOLS = sorted(t.name for t in tools if t.requires_approval)
SIDE_EFFECT_TOOLS = APPROVAL_TOOLS + [
    "add_contact", "update_contact_status", "set_followup", "add_task",
    "calendar_create_event", "set_reminder", "add_goal", "graph_link",
]


def glossary_entry(term, definition, where, why, example):
    w(f"### {term}")
    w()
    w(f"**Definition:** {definition}")
    w(f"**Where in codebase:** `{where}`")
    w(f"**Why it exists:** {why}")
    w(f"**Example:** {example}")
    w()


def tool_entry(t):
    approval = "Yes — HITL required" if t.requires_approval else "No — executes immediately (or gated by AUTONOMY_LEVEL=cautious for writes)"
    w(f"#### `{t.name}`")
    w()
    w(f"- **Category:** {t.category}")
    w(f"- **Requires approval:** {approval}")
    w(f"- **Description:** {t.description}")
    w(f"- **When the LLM uses it:** When the user's goal maps to {t.category} work and this tool is the best match in the retrieved schema set.")
    w(f"- **Example user utterance:** \"{_tool_utterance(t)}\"")
    w()


def _tool_utterance(t):
    name = t.name
    cat = t.category
    samples = {
        "list_tasks": "What tasks are due before Friday?",
        "add_task": "Add a task to email the investor by Friday",
        "web_search": "Search for recent news on AI agent startups",
        "send_email": "Draft and send an email to the investor",
        "set_reminder": "Remind me to call Asha at 5pm tomorrow",
        "search_memory": "What did we decide about pricing last month?",
        "delegate": "Have the researcher look up competitor pricing",
        "run_swarm": "Run a swarm to research and draft outreach for 5 leads",
        "world_state": "Give me a snapshot of my pipeline and goals",
        "backup_now": "Back up all my data now",
    }
    if name in samples:
        return samples[name]
    cat_map = {
        "tasks": f"Help me manage my tasks using {name}",
        "reminders": f"Set or check reminders — try {name}",
        "calendar": f"Schedule something on my calendar via {name}",
        "crm": f"Update my CRM — e.g. {name}",
        "research": f"Research a topic — agent may call {name}",
        "outreach": f"Draft outreach — {name}",
        "memory": f"Recall or save context with {name}",
        "swarm": f"Orchestrate multi-agent work with {name}",
        "healing": f"Diagnose system health via {name}",
        "cognition": f"Inspect LECE state with {name}",
    }
    return cat_map.get(cat, f"Use {name} to help with my request")


GLOSSARY = [
    ("ReAct", "Reason + Act loop where the LLM alternates reasoning with tool calls until it can answer.",
     "agent/loop.py, agent/core.py", "Core agentic pattern — model decides tools dynamically instead of fixed pipelines.",
     "User asks for investor research → model calls web_search, then add_contact, then replies."),
    ("LangGraph", "Graph-based agent framework with explicit nodes/edges and checkpointing.",
     "agent/swarm/adapters/langgraph_adapter.py", "Optional adapter for swarm path 11; main agent uses custom loop, not LangGraph.",
     "run_langgraph_swarm delegates to LangGraph when LANGGRAPH_ADAPTER=true."),
    ("RAG", "Retrieval-Augmented Generation — fetch relevant context before answering.",
     "memory/vector_store.py, memory/retrieval.py", "Ground answers in founder-specific memory, not model weights.",
     "What did we decide about pricing? → hybrid_search in conversations collection."),
    ("Tool-RAG", "Retrieve only relevant tool schemas per turn instead of full catalog.",
     "agent/tool_retrieval.py", "Saves tokens and improves tool choice accuracy with 117 tools.",
     "User says 'remind me Friday' → retrieves set_reminder, add_task, not all 117 schemas."),
    ("Self-RAG", "Agent evaluates whether retrieval is needed and if results are relevant.",
     "agent/self_rag.py", "Prevents blind retrieval and filters irrelevant chunks.",
     "Low relevance score → agent answers from parametric knowledge or asks to clarify."),
    ("GraphRAG", "Community summaries over knowledge graph for global questions.",
     "memory/graphrag.py, memory/graph.py", "Answers 'who in my network knows X?' better than flat vector search.",
     "ask_network tool uses community map rebuilt nightly at consolidation."),
    ("HITL", "Human-in-the-loop — founder approves side-effect actions before execution.",
     "agent/approvals.py, bot/handlers.py", "Customer Obsession: no surprise emails or posts.",
     "send_email queued → Telegram inline Approve/Reject buttons."),
    ("BM25", "Sparse lexical ranking for keyword/entity-heavy queries.",
     "memory/retrieval.py", "Complements dense embeddings for names, codenames, exact terms.",
     "Query 'Acme Corp deadline' — BM25 catches exact token match BM25 missed semantically."),
    ("RRF", "Reciprocal Rank Fusion — merges dense and sparse ranked lists without tuning.",
     "memory/retrieval.py", "Simple, robust hybrid fusion for local single-user setup.",
     "Top dense + top BM25 merged with RRF_K=60 constant."),
    ("ChromaDB", "Local embedded vector database for semantic memory.",
     "memory/vector_store.py, data/chroma/", "Default zero-setup vector backend on single machine.",
     "Collections: conversations, lessons, contacts, etc."),
    ("Qdrant", "Remote/managed vector database alternative to Chroma.",
     "memory/vector_store.py", "Scale embeddings to cloud without changing app logic.",
     "VECTOR_BACKEND=qdrant with QDRANT_URL set."),
    ("SQLite", "Embedded relational DB for structured founder data.",
     "memory/sql_store.py, agent/store.py, data/founder_os.db", "Source of truth for tasks, CRM, approvals — not embeddings.",
     "list_tasks reads SQL WHERE due_at < Friday, not vector search."),
    ("episodic memory", "Time-stamped experiential records with recency/importance weighting.",
     "memory/retrieval.py episodic_recall", "Generative-Agents-style recall for 'what happened recently'.",
     "Recall last week's investor meetings with recency boost."),
    ("consolidation", "Nightly job merging raw notes into durable memory + knowledge graph.",
     "memory/consolidation.py, scheduler/jobs.py job_consolidate_memory", "Prevents memory fragmentation; runs 03:00 cron.",
     "CRM notes → distilled lessons + kg_entities updated."),
    ("world model", "Structured snapshot of founder's business state.",
     "memory/world_model.py", "Gives agent situational awareness each turn without full DB scan.",
     "world_state tool returns pipeline, goals, finance summary."),
    ("knowledge graph", "Entity-relation store derived from CRM and notes.",
     "memory/graph.py", "Enables relational queries and GraphRAG communities.",
     "graph_link connects Person → Company → Topic."),
    ("approval gate", "Checkpoint before irreversible tool execution.",
     "agent/loop.py _execute_tool, agent/approvals.py", "Side-effect tools never run without allow decision.",
     "policy.decide returns 'approve' → enqueue, not registry.call."),
    ("policy", "Tiered autonomy: cautious / balanced / autonomous.",
     "agent/policy.py, agent/cognition/trust.py", "Centralizes allow/approve/deny — not scattered in loop.",
     "AUTONOMY_LEVEL=cautious gates add_task too."),
    ("constitution", "Hard-coded safety rules in system prompt.",
     "agent/identity.py", "Non-negotiable boundaries even at autonomous level.",
     "Never exfiltrate secrets; treat tool output as untrusted."),
    ("preplay", "Simulate high-stakes actions on digital twin before real execution.",
     "agent/cognition/preplay.py", "ProPlay-style counterfactual planning for send_email, x_post.",
     "3 branches scored → best selected → still goes through HITL."),
    ("digital twin", "Procedure graph predicting action outcomes from past traces.",
     "agent/cognition/twin.py", "Business state + transition reliabilities for simulation.",
     "twin_state shows CRM + learned transition probabilities."),
    ("LECE", "Lived-Experience Cognitive Engine — continual self-improvement from traces.",
     "agent/cognition/", "Closes loop: traces → principles → injection → better decisions.",
     "Nightly distill at 03:30 extracts principles from JSONL traces."),
    ("swarm", "Multi-agent orchestration with 12 topology paths.",
     "agent/swarm/", "Parallel research, debate, mesh refinement for complex goals.",
     "run_swarm fan-out to researcher + outreach specialists."),
    ("delegate", "Hand off subtask to specialist sub-agent with narrowed tools.",
     "agent/subagent.py, agent/tools/orchestration_tools.py", "Supervisor pattern without losing shared execute_loop semantics.",
     "delegate('researcher', 'Find Series A investors in fintech')"),
    ("sub-agent", "Specialist running execute_loop with category-filtered schemas.",
     "agent/subagent.py", "Same safety stack as main agent; parallel via asyncio.gather.",
     "10 specialists: researcher, outreach, ops, analyst, etc."),
    ("circuit breaker", "CLOSED/OPEN/HALF_OPEN per tool/provider after repeated failures.",
     "agent/healing/circuit.py", "Prevents hammering broken APIs; enables route-around.",
     "5 failures on web_search → circuit open → fallback to scrape_url."),
    ("semantic cache", "Cache LLM responses for near-duplicate prompts.",
     "llm/cache.py", "Cost control — embedding distance threshold match.",
     "SEMANTIC_CACHE=true, CACHE_DISTANCE_THRESHOLD=0.08."),
    ("Ollama", "Local LLM runtime for free offline fallback.",
     "llm/ollama_client.py, llm/router.py", "Last resort in provider cascade when cloud keys fail.",
     "OLLAMA_ENABLED=true, model llama3.1 at localhost:11434."),
    ("Groq", "Fast cloud LLM provider, first in general routing chain.",
     "llm/groq_client.py, llm/router.py", "Low-latency tool-calling for interactive Telegram UX.",
     "ROUTING general: groq → gemini → openai → ollama."),
    ("Gemini", "Google LLM, preferred for research/analysis tasks.",
     "llm/gemini_client.py", "Strong long-context research in routing table.",
     "task_type=research uses gemini first."),
    ("MCP", "Model Context Protocol — expose Founder OS tools to external agents.",
     "mcp_server.py", "Swarm path 8: Cursor/Claude can invoke swarm tools remotely.",
     "External peer calls run_swarm via MCP server."),
    ("Voyager-style", "Self-evolving skills from successful tool trajectories.",
     "agent/swarm/evolve.py, agent/skills_factory.py", "Agent authors new tools/skills from experience.",
     "run_evolve_swarm discovers reusable skill patterns."),
    ("Reflexion", "Self-criticism after action to improve next attempt.",
     "agent/critic.py verify_answer, agent/loop.py step reflection", "Catches hallucination before reply sent.",
     "critic returns ok=false → one refinement execute_loop pass."),
    ("plan-and-execute", "Explicit plan injected before tool loop for complex goals.",
     "agent/planner.py, agent/core.py", "Decomposes multi-step work into inspectable checklist.",
     "Research 5 competitors → planner creates 5-step plan persisted to plans table."),
    ("epsilon-greedy", "Explore/exploit balance for strategy A/B testing.",
     "agent/optimizer.py, agent/store.py strategies table", "Learn which email subject styles work.",
     "10% random variant, 90% best-performing strategy variant."),
    ("prompt injection", "Malicious instructions embedded in untrusted content.",
     "agent/safety.py", "Email/web content must not override system instructions.",
     "safety.wrap_tool_result marks external content untrusted."),
    ("kill switch", "Emergency stop — no LLM calls, no autonomy.",
     "config.py AGENT_PAUSED, agent/core.py", "Instant halt without redeploy.",
     "AGENT_PAUSED=true → core.run returns paused message."),
    ("spend cap", "Daily LLM call budget to prevent runaway loops.",
     "agent/budget.py, config DAILY_LLM_CALL_CAP", "Cost and safety guardrail.",
     "Cap exceeded → BudgetError, agent pauses LLM calls."),
    ("flight recorder", "Immutable per-turn JSONL trace of all events.",
     "agent/trace.py, data/traces/", "Debug, replay, LECE distillation input.",
     "Each turn logs plan, tool calls, decisions, healing events."),
    ("heartbeat", "Scheduled proactive self-check without user message.",
     "scheduler/jobs.py job_heartbeat, agent/core.py actor=heartbeat", "Autonomous nudges on goals, follow-ups, pipeline.",
     "Every 4h 9-21: agent reviews state, sends update or NOTHING."),
    ("watchdog", "Periodic self-test and auto-remediation.",
     "agent/healing/watchdog.py, scheduler/jobs.py job_watchdog", "Catches DB/vector/API degradation before user notices.",
     "Every 30m: watchdog_tick runs health checks."),
]

# Extend glossary to 80+ terms programmatically
_EXTRA_GLOSSARY = [
    ("AgentCore", "Top-level supervisor orchestrating plan→execute→verify.", "agent/core.py", "Single entry point for all turns.", "core.run(user_message) from Telegram handler."),
    ("execute_loop", "Shared ReAct tool-calling loop with healing wrapper.", "agent/loop.py", "Same semantics for main agent and sub-agents.", "Up to MAX_STEPS=8 rounds of complete_with_tools."),
    ("Tool schema", "OpenAI-style JSON function definition per registered tool.", "agent/registry.py Tool.schema()", "LLM sees structured callable API.", "name, description, parameters with types."),
    ("action_log", "Audit table of every tool invocation.", "agent/store.py action_log", "Replay, compliance, LECE episode scoring.", "actor, tool_name, args_json, result logged each call."),
    ("approval queue", "Pending side-effect actions awaiting founder decision.", "agent/store.py approvals", "Durable HITL state across restarts.", "status: pending|approved|rejected|executed."),
    ("inline keyboard", "Telegram tappable Approve/Reject buttons.", "bot/handlers.py, scheduler/jobs.py", "Mobile-first HITL UX.", "callback_data approve:42 / reject:42."),
    ("long polling", "Bot pulls updates from Telegram API (not webhook).", "main.py app.run_polling()", "Simpler local dev; no public HTTPS endpoint needed.", "drop_pending_updates=True on startup."),
    ("middleware", "Auth gate — only MY_TELEGRAM_USER_ID unless PUBLIC_ACCESS.", "bot/middleware.py", "Single-tenant security default.", "is_authorized blocks strangers."),
    ("hybrid_search", "Dense + BM25 fused with RRF.", "memory/retrieval.py", "Best of semantic and lexical recall.", "deep_recall tool uses hybrid_search."),
    ("fused_recall", "Multi-collection hybrid search with episodic scoring.", "memory/retrieval.py fused_recall", "Cross-collection recall for complex queries.", "Searches conversations + lessons + contacts."),
    ("tool_retrieval", "Embed tool descriptions; retrieve top-k per message.", "agent/tool_retrieval.py", "Token efficiency at 117 tools.", "TOOL_RAG_K=16 plus _CORE always-on set."),
    ("context spaces", "Scoped document collections for project-specific RAG.", "memory/context_store.py, context/", "Isolate deck drafts from general memory.", "Resolver builds context block per query."),
    ("cross-encoder rerank", "Optional second-stage relevance scoring.", "memory/retrieval.py _maybe_rerank", "Improves precision when sentence-transformers installed.", "ms-marco-MiniLM reranks top-20 RRF results."),
    ("APScheduler", "Cron scheduler for proactive jobs.", "scheduler/jobs.py", "Briefings, consolidation, heartbeat without user.", "AsyncIOScheduler with CronTrigger jobs."),
    ("daily briefing", "Morning summary from report specialist.", "scheduler/jobs.py 08:00, specialists/report_agent.py", "Proactive founder value at day start.", "☀️ Good morning + pipeline/tasks summary."),
    ("follow-up reminder", "CRM contacts due for follow-up nudge.", "scheduler/jobs.py 10:00", "Prevents pipeline decay.", "🔔 N contacts due today listed."),
    ("topic monitor", "Scheduled web search for new URLs on topic.", "scheduler/jobs.py job_check_monitors", "Competitive/market awareness.", "📡 New on 'AI agents' with fresh links."),
    ("reply loop", "Track email replies and notify founder.", "agent/reply_loop.py, job_check_inbox", "Close the outreach feedback loop.", "Hourly 9-21 checks inbox for new replies."),
    ("RecoveryBudget", "Per-turn cap on healing recovery attempts.", "agent/healing/orchestrator.py", "Prevents infinite heal loops.", "HEALING_MAX_RECOVERIES=4 per turn."),
    ("FailureClass", "Taxonomy: transient, wrong_tool, stuck_loop, etc.", "agent/healing/taxonomy.py", "Routes failure to cheapest fix.", "diagnose.py classifies timeout → RETRY."),
    ("stuck-loop detection", "Break when same tool+args repeats failing.", "agent/loop.py detect_stuck_loop", "Runaway token spend prevention.", "Same sig 3x → degrade with partial result."),
    ("metacog", "MASC-style step anomaly scoring.", "agent/healing/metacog.py", "Early warning on suspicious tool sequences.", "Anomaly logged before escalation."),
    ("checkpoint", "Per-step snapshot for rollback.", "agent/healing/checkpoint.py", "State recovery on multi-step failure.", "turn_id + step saved after each tool."),
    ("failure ledger", "Persistent failure→fix patterns for learning.", "agent/healing/ledger.py", "System learns which recoveries work.", "Stored in failures + healing_events tables."),
    ("AdaptOrch", "Task-adaptive topology routing from DAG metrics.", "agent/swarm/topology.py", "Picks parallel vs hierarchical vs debate.", "route_topology(goal, steps) → Topology enum."),
    ("blackboard", "Shared stigmergy board for swarm agents.", "agent/swarm/board.py", "Decentralized coordination without central planner.", "board_post / board_read during run_blackboard."),
    ("maker-checker", "One agent drafts, another verifies.", "agent/swarm/debate.py", "Quality gate for high-stakes outputs.", "run_maker_checker before send_email draft."),
    ("SwarmSys", "Bio-inspired explorer/worker/validator profiles.", "agent/swarm/profiles.py", "Diverse agent behaviors for exploration.", "Pheromone-weighted profile assignment."),
    ("DLQ", "Dead-letter queue for failed swarm jobs.", "agent/swarm/workers/queue.py", "Retry without losing work.", "job_swarm_dlq_retry every 15 minutes."),
    ("principles", "Distilled LECE rules from successful traces.", "agent/cognition/principles.py, agent/cognition/distill.py", "Durable learning beyond instance memory.", "Injected step-wise in execute_loop."),
    ("Global Workspace", "Attention blackboard with salience decay.", "agent/cognition/workspace.py", "Coalitions bid for founder attention.", "workspace_state tool shows active items."),
    ("trust-calibrated autonomy", "Learned per-tool competence for policy.", "agent/cognition/trust.py", "Elevate autonomy only after proven success.", "LECE_TRUST_MIN_TRIALS=5 before elevation."),
    ("LoRA gate", "Eval gate before promoting fine-tuned adapter.", "agent/cognition/train/gate.py", "Tier B training must beat baseline.", "LECE_DISTILL_TRAIN=false by default."),
    ("simulation sandbox", "Intercept side-effect tools during preplay.", "agent/cognition/sandbox.py", "Safe counterfactual execution.", "should_intercept → simulate_tool_result."),
    ("identity", "System prompt builder with constitution.", "agent/identity.py", "Consistent agent persona and rules.", "build_system_prompt with skills, goals, manual."),
    ("evolution", "Async reflection: lessons, skills, strategies.", "agent/evolution.py", "Self-improving without fine-tune.", "reflect() after substantive turns."),
    ("confidence", "Annotate low-confidence replies honestly.", "agent/confidence.py", "Abstention over hallucination.", "confidence=low → suggest clarifying question."),
    ("complete_with_tools", "LLM call returning tool_calls or final text.", "llm/tool_client.py", "Bridge between router and ReAct loop.", "OpenAI-compatible tool use API."),
    ("BudgetError", "Raised when daily cap or pause blocks LLM.", "agent/budget.py", "Hard stop on spend.", "check_before_call in router.complete."),
    ("RateLimitError", "Groq rate limit — triggers cascade to next provider.", "llm/groq_client.py", "Resilient multi-provider routing.", "Caught in router → try gemini."),
    ("PUBLIC_ACCESS", "Allow any Telegram user (demo mode).", "config.py, bot/middleware.py", "Shared brain warning — demo only.", "false default — single founder."),
    ("specialist", "Named sub-agent with category-filtered tools.", "agent/subagent.py SPECIALISTS", "Focused expertise without full catalog noise.", "researcher gets research+perception only."),
    ("fan-out/fan-in", "Parallel sub-agents then aggregate results.", "agent/tools/orchestration_tools.py delegate_parallel", "Latency reduction for independent subtasks.", "Research 3 companies in parallel."),
    ("dynamic handoff", "OpenAI Swarm-style agent-to-agent transfer.", "agent/swarm/handoff.py", "Context preserved across handoffs.", "handoff_start → handoff_to outreach specialist."),
    ("mesh convergence", "Iterative artifact refinement across agents.", "agent/swarm/mesh.py", "Draft improves over rounds.", "run_mesh refines pitch deck copy."),
    ("hierarchical swarm", "Nested supervisor delegating to sub-supervisors.", "agent/swarm/hierarchy.py", "Complex org-chart style tasks.", "run_hierarchical_swarm for multi-phase launches."),
    ("proactive swarm", "Budget-aware swarm on heartbeat goals.", "agent/swarm/proactive.py", "Autonomous progress on active goals.", "Triggered after heartbeat if SWARM_ENABLED."),
    ("skills_factory", "Runtime tool authoring with quarantine.", "agent/skills_factory.py", "Voyager-style capability expansion.", "create_tool requires approval; broken tools quarantined."),
    ("FastAPI dashboard", "Local web UI for traces, cognition, CRM.", "api/server.py, web/", "Visual ops without Telegram limits.", "DASHBOARD_PORT=8787, React on 3000."),
    ("eval harness", "Quality scenarios + judge for regression testing.", "evals/runner.py, evals/quality_runner.py", "Production bar beyond ad-hoc testing; replaces full RAGAS pipeline.", "Golden ~30 queries in evals/quality_scenarios.py."),
]
GLOSSARY.extend(_EXTRA_GLOSSARY)

# ═══════════════════════════════════════════════════════════════════════════════
# PART 0 — PREREQUISITES
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 0: Prerequisites & mental model", 2)

w("Before diving into agent/swarm/RAG internals, ensure the learner can run and observe the system.")
w()
w("### Required environment")
w()
w("| Requirement | Version / detail | Why |")
w("|---|---|---|")
w("| Python | 3.10+ (3.11 recommended) | asyncio, type hints, match statements in deps |")
w("| Telegram account | Bot from @BotFather | Primary UX — push notifications, HITL buttons |")
w("| LLM API keys | Groq + Gemini minimum; OpenAI optional | Router cascade; Groq for speed |")
w("| Ollama | Optional local fallback | Free offline last resort in chain |")
w("| SQLite | Bundled via Python | `data/founder_os.db` — no separate DB server |")
w("| Vector backend | Chroma (default) or Qdrant | Semantic memory; interchangeable via VECTOR_BACKEND |")
w()
w("### Setup checklist")
w()
for i, step in enumerate([
    "Clone repo; `pip install -r requirements.txt`",
    "Copy `.env.example` → `.env`; fill TELEGRAM_BOT_TOKEN, GROQ_API_KEY, GOOGLE_GEMINI_API_KEY, MY_TELEGRAM_USER_ID",
    "Run `python main.py` — confirm long-polling starts (not webhook)",
    "Send `/start` on Telegram — verify authorized response",
    "Send a simple message; watch `data/traces/*.jsonl` for flight recorder output",
    "Optional: `python scripts/google_auth.py` for Calendar; set Gmail app password for email",
], 1):
    w(f"{i}. {step}")
w()
w("### Mental model — one diagram to rule them all")
w()
diagram("""flowchart TB
    Founder[Founder on Telegram] -->|message| Handler[bot/handlers.py]
    Handler --> Core[agent/core.py AgentCore]
    Core --> Plan[planner.py optional plan]
    Core --> Exec[loop.py execute_loop MAX_STEPS=8]
    Exec --> LLM[llm/router.py cascade]
    Exec --> Tools[registry.call 117 tools]
    Tools --> Memory[(SQLite + Chroma/Qdrant)]
    Tools --> Ext[Gmail Calendar Web X APIs]
    Exec --> Policy[policy + approvals HITL]
    Exec --> Heal[healing orchestrator]
    Core --> Critic[critic.py verify]
    Critic --> Reply[Reply to Telegram]
    Scheduler[APScheduler cron] -->|heartbeat briefing| Core
    Traces[data/traces JSONL] --> LECE[agent/cognition LECE]
    LECE --> Core""")
w("**Key insight:** The founder is the customer. Every design choice — HITL, SQL source of truth, local traces — maps to *don't surprise the user with irreversible actions* and *ground answers in their data*.")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1 — WHAT IS FOUNDER OS
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 1: What is Founder OS? (Basics)", 2)

w("Founder OS is **not a chatbot**. A chatbot maps message → text reply. Founder OS maps message → **plan → tool chain → verified reply**, with memory, scheduling, and safety gates.")
w()
w("It is a **virtual cofounder** for a solo builder: chief-of-staff that researches, manages CRM, drafts outreach, schedules, monitors goals, and learns from every turn — all via Telegram.")
w()
w("### Design principles")
w()
w("| Principle | Meaning | Code manifestation |")
w("|---|---|---|")
w("| Agentic, not scripted | LLM chooses tools; no intent classifier | `registry.all_schemas()` + ReAct loop |")
w("| Founder is customer | No surprise side effects | HITL on send_email, x_post, etc. |")
w("| Hybrid memory | SQL for facts; vectors for fuzzy recall | list_tasks → SQL; search_memory → Chroma |")
w("| Shared executor | Main agent and sub-agents same loop | `execute_loop` everywhere |")
w("| Local-first | Traces, DB, embeddings on disk | data/ directory |")
w("| Observable | Every turn traced | `agent/trace.py` JSONL |")
w("| Bounded autonomy | Caps on steps, recoveries, LLM calls | MAX_STEPS=8, HEALING_MAX_RECOVERIES=4 |")
w("| Fail safe | Healing never bypasses policy | orchestrator wraps, never skips approvals |")
w()
w("### Founder OS vs ChatGPT")
w()
w("| Dimension | ChatGPT | Founder OS |")
w("|---|---|---|")
w("| Memory | Thread-only / optional memory | Persistent SQLite + vector + world model + LECE |")
w("| Actions | Plugins limited | 117 first-class tools: CRM, email, calendar, swarm |")
w("| Safety | User responsibility | Policy tiers, HITL, constitution, injection defense |")
w("| Proactivity | None | Scheduler: briefing, heartbeat, monitors, follow-ups |")
w("| Learning | Static weights | Evolution + LECE distillation from your traces |")
w("| Cost control | Subscription | Semantic cache, Tool-RAG, DAILY_LLM_CALL_CAP |")
w("| Interface | Web/app | Telegram push + inline approval keyboards |")
w("| Multi-agent | Single model | 10 specialists, 12 swarm paths |")
w("| Observability | Opaque | Flight recorder, dashboard, eval harness |")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 2 — GLOSSARY
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 2: Complete glossary — every term defined", 2)
w(f"This glossary defines **{len(GLOSSARY)} terms** with definition, codebase location, rationale, and example.")
w()
for entry in GLOSSARY:
    glossary_entry(*entry)

# ═══════════════════════════════════════════════════════════════════════════════
# PART 3 — ARCHITECTURE DIAGRAMS
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 3: System architecture (diagrams)", 2)

w("### 3.1 High-level architecture")
diagram("""flowchart LR
    subgraph Interface
        TG[Telegram long-poll]
        WEB[React Dashboard]
    end
    subgraph Agent
        CORE[core.py]
        LOOP[loop.py]
        SWARM[swarm/]
    end
    subgraph Memory
        SQL[(SQLite)]
        VEC[(Chroma/Qdrant)]
        KG[Knowledge Graph]
    end
    subgraph Safety
        POL[policy.py]
        APP[approvals.py]
        SAF[safety.py]
    end
    TG --> CORE
    WEB --> API[api/server.py]
    CORE --> LOOP
    CORE --> SWARM
    LOOP --> POL
    LOOP --> APP
    LOOP --> SAF
    LOOP --> SQL
    LOOP --> VEC
    LOOP --> KG""")

w("### 3.2 Layered view")
diagram("""flowchart TB
    L1[Layer 1: Interface — Telegram bot handlers middleware formatters]
    L2[Layer 2: Cognition — core planner critic loop subagent]
    L3[Layer 3: Tools — registry 117 callables grouped by category]
    L4[Layer 4: Memory — SQL vector graph context LECE]
    L5[Layer 5: Safety — policy approvals budget safety healing]
    L6[Layer 6: Infrastructure — LLM router scheduler trace backup]
    L1 --> L2 --> L3 --> L4
    L2 --> L5
    L3 --> L5
    L2 --> L6""")

w("### 3.3 Memory brain")
diagram("""flowchart TB
    Query[User query] --> Router{Retrieval router}
    Router -->|structured filters| SQL[sql_store tasks contacts]
    Router -->|conceptual| Hybrid[hybrid_search BM25+RRF]
    Router -->|relational| Graph[graph.py GraphRAG]
    Router -->|tools| ToolRAG[tool_retrieval.py]
    SQL --> Merge[Merged context block]
    Hybrid --> Merge
    Graph --> Merge
    ToolRAG --> Schemas[Tool schemas for LLM]
    Merge --> Prompt[System prompt injection]""")

w("### 3.4 Safety stack")
diagram("""flowchart TD
    ToolCall[Tool call proposed] --> Budget[budget.py cap check]
    Budget --> Policy[policy.decide allow approve deny]
    Policy -->|approve| Precheck[critic.precheck_action]
    Precheck --> Queue[approvals.enqueue]
    Queue --> TG[Telegram inline keyboard]
    TG -->|approved| Execute[registry.call]
    Policy -->|allow| Preplay[LECE preplay if high-stakes]
    Preplay --> Execute
    Execute --> Wrap[safety.wrap_tool_result]
    Wrap --> Log[action_log + trace]""")

w("### 3.5 Turn lifecycle sequence")
diagram("""sequenceDiagram
    participant U as Founder
    participant B as bot/handlers
    participant C as core.py
    participant P as planner
    participant L as loop.py
    participant R as registry
    participant CR as critic
    U->>B: Telegram message
    B->>C: core.run(message)
    C->>C: retrieve memory context
    C->>P: make_plan if deliberate
    C->>L: execute_loop MAX_STEPS=8
    loop up to 8 steps
        L->>L: LLM complete_with_tools
        L->>R: tool call via policy
        R-->>L: result
    end
    C->>CR: verify_answer
    CR-->>C: ok or refine once
    C-->>B: final reply
    B-->>U: Telegram response""")

w("### 3.6 Tool execution flow")
diagram("""flowchart LR
    LLM[LLM proposes tool] --> Get[registry.get]
    Get --> Heal[healing orchestrator]
    Heal --> CB{circuit open?}
    CB -->|yes| Sub[substitute or route_around]
    CB -->|no| Call[registry.call]
    Call --> Sim{sandbox simulate?}
    Sim -->|yes| Pred[predicted result]
    Sim -->|no| Real[real API or DB write]
    Real --> Trace[trace.add_tool_event]""")

w("### 3.7 Approval flow")
diagram("""sequenceDiagram
    participant L as loop.py
    participant Pol as policy
    participant A as approvals
    participant S as scheduler
    participant U as Founder
    L->>Pol: decide(tool)
    Pol-->>L: approve
    L->>A: enqueue(name args)
    A->>S: send_approval_to_user
    S->>U: Inline Approve Reject
    U->>A: callback approve:id
    A->>L: registry.call executed""")

w("### 3.8 Hybrid retrieval")
diagram("""flowchart LR
    Q[Query] --> Dense[Chroma embedding search]
    Q --> Sparse[BM25Okapi token match]
    Dense --> RRF[Reciprocal Rank Fusion k=60]
    Sparse --> RRF
    RRF --> Rerank{Cross-encoder available?}
    Rerank -->|yes| CE[ms-marco rerank]
    Rerank -->|no| TopK[Top k results]
    CE --> TopK""")

w("### 3.9 GraphRAG")
diagram("""flowchart TB
    CRM[CRM contacts companies] --> Build[graph.build_from_crm]
    Build --> Entities[kg_entities kg_relations]
    Entities --> Comm[graphrag.build_communities]
    Comm --> Map[Community summaries]
    Map --> Ask[ask_network tool]
    Nightly[job_consolidate_memory 03:00] --> Build""")

w("### 3.10 Swarm topologies")
diagram("""flowchart TD
    Goal[Swarm goal] --> TR[topology.route_topology]
    TR --> P1[Parallel fan-out]
    TR --> P2[Sequential handoff]
    TR --> P3[Blackboard stigmergy]
    TR --> P4[Debate maker-checker]
    TR --> P5[Mesh refine]
    TR --> P6[Hierarchical nested]
    P1 --> EL[execute_loop shared]
    P2 --> EL
    P3 --> EL
    P4 --> EL
    P5 --> EL
    P6 --> EL""")

w("### 3.11 Self-healing control loop")
diagram("""flowchart TD
    M[Monitor call] --> D[Detect failure]
    D --> Di[Diagnose FailureClass]
    Di --> R[Recovery policy budget]
    R --> V[Verify fix]
    V -->|fail| D
    V -->|success| OK[Return result]
    R -->|exhausted| E[escalate Telegram]""")

w("### 3.12 LECE three pillars")
diagram("""flowchart LR
    subgraph P1[Pillar 1 Distillation]
        T[traces] --> E[episodes] --> D[distill] --> PR[principles]
    end
    subgraph P2[Pillar 2 Twin Preplay]
        TW[twin] --> SB[sandbox] --> PP[preplay] --> ACT[real action]
    end
    subgraph P3[Pillar 3 Workspace Trust]
        WS[workspace] --> FM[founder_model] --> TR[trust_scores]
    end
    PR --> Core[core.py loop.py]
    TR --> Pol[policy adaptive_decide]""")

w("### 3.13 Scaling on AWS")
diagram("""flowchart TB
    ALB[Application Load Balancer] --> API[Stateless API tier]
    API --> SQS[SQS embed and email jobs]
    API --> RDS[(Postgres per-tenant RLS)]
    API --> QdrantCloud[Qdrant cluster metadata filter]
    API --> Redis[ElastiCache rate limits sessions]
    API --> SM[Secrets Manager keys]
    API --> LLM[LLM providers token budget per user]
    TG[Telegram] --> API""")

w("### 3.14 Data flow: remind me to email investor Friday")
diagram("""sequenceDiagram
    participant U as Founder
    participant C as core.py
    participant Pl as planner
    participant L as loop.py
    participant SQL as SQLite tasks
    participant Mem as vector memory
    participant App as approvals
    U->>C: Remind me to email investor Friday draft when I approve
    C->>Pl: needs_planning true
    Pl-->>C: steps set_reminder add_task draft_email
    C->>L: execute_loop
    L->>SQL: add_task due Friday
    L->>Mem: recall investor context hybrid_search
    L->>App: send_email queued HITL
    App-->>U: Draft with Approve button
    U->>App: Approve
    App->>L: execute send_email log outcome embed summary""")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 4 — TURN LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 4: The turn lifecycle — step by step", 2)
w("Every user message flows through **10 steps**. Constants: `MAX_STEPS=8` (`agent/loop.py`), `HISTORY_TURNS=8` (`agent/core.py`).")
w()

TURN_STEPS = [
    ("1. Authorization & intake", "bot/handlers.py handle_message", "middleware.is_authorized; voice/photo routed to vision/transcription", "Unauthorized users rejected unless PUBLIC_ACCESS=true"),
    ("2. Trace start & enrichment", "agent/core.py run()", "trace.start(actor, message); image_context appended; actor=user|heartbeat", "Flight recorder opens new JSONL entry"),
    ("3. Context assembly", "agent/core.py _memory_context, context/resolver, world_model", "Hybrid memory + context spaces + world snapshot + evolution blocks + LECE manual/workspace/founder", "System prompt grows with retrieved evidence"),
    ("4. Planning (if deliberate)", "agent/planner.py needs_planning, make_plan", "Heuristic: long message or 2+ deliberate hints; plan persisted to plans/subtasks", "Multi-step goals get WORKING PLAN injected"),
    ("5. Tool-RAG schema selection", "agent/tool_retrieval.py schemas_for_message", "User turns: top TOOL_RAG_K=16 + _CORE; heartbeat/subagents: full catalog", "117 tools → ~30 schemas typical"),
    ("6. Execute loop", "agent/loop.py execute_loop", "Up to MAX_STEPS=8: LLM → tool calls → policy → healing → results appended", "ReAct until model returns text without tools"),
    ("7. Verification", "agent/critic.py verify_answer", "Deliberate turns only; one refinement pass if ok=false", "Reflexion before user sees reply"),
    ("8. History & vector persist", "agent/core.py _history, memory/vector_store add", "Rolling HISTORY_TURNS*2 messages; conversation embedded", "Next turn has short-term context"),
    ("9. Async evolution", "agent/evolution.py reflect, cognition founder_model workspace", "Fire-and-forget on substantive turns", "Lessons/skills/principles updated offline"),
    ("10. Approval UI & reply", "bot/handlers.py _notify_new_approvals, split_long_message", "New pending approvals get inline keyboards; reply chunked for Telegram 4096 limit", "Founder sees answer + any approval cards"),
]
for title, path, detail, note in TURN_STEPS:
    w(f"### {title}")
    w()
    w(f"- **Primary file:** `{path}`")
    w(f"- **What happens:** {detail}")
    w(f"- **Interview note:** {note}")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# PART 5 — AGENT CORE
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 5: Agentic core deep dive", 2)

CORE_MODULES = {
    "agent/core.py": [
        ("run", "Main entry: plan → execute → verify → persist. Called from Telegram and heartbeat."),
        ("_memory_context", "Top-4 vector hits across collections for prompt injection."),
        ("_safe_reflect", "Async wrapper for evolution.reflect after turn."),
        ("HISTORY_TURNS", "Constant 8 — prior user/assistant pairs in prompt."),
    ],
    "agent/loop.py": [
        ("execute_loop", "ReAct loop up to MAX_STEPS=8 with healing, checkpoints, stuck-loop detection."),
        ("_execute_tool", "Policy gate, preplay, approvals enqueue, or healed registry.call."),
        ("_healed_llm_call", "LLM wrapped in healing orchestrator with circuit breaker."),
        ("_healed_tool_call", "Tool call with retry, substitute, degrade paths."),
        ("_policy_decide", "Static policy or LECE adaptive_decide from trust.py."),
        ("MAX_STEPS", "Constant 8 — prevents runaway token spend."),
    ],
    "agent/planner.py": [
        ("needs_planning", "Heuristic gate for plan-and-execute pattern."),
        ("make_plan", "LLM JSON plan with steps; optional persist to plans table."),
        ("render_plan", "Checklist string injected into executor messages."),
        ("replan_on_failure", "Adaptive replan preserving completed subtasks."),
    ],
    "agent/critic.py": [
        ("verify_answer", "Reflexion judge on final reply; returns confidence + clarify."),
        ("precheck_action", "Risk note for send_email, x_post, propose_code_change, create_tool."),
    ],
    "agent/registry.py": [
        ("register", "Decorator attaching Tool to _TOOLS dict."),
        ("all_tools / all_schemas", "Catalog for LLM and Tool-RAG indexing."),
        ("call", "Execute sync/async tool; sandbox intercept for preplay simulation."),
        ("schemas_for", "Category-filtered schemas for sub-agents."),
    ],
    "agent/subagent.py": [
        ("SPECIALISTS", "10 named roles with category sets and briefs."),
        ("run_subagent", "execute_loop with filtered schemas and role system message."),
        ("list_specialists", "Returns researcher, outreach, ops, analyst, etc."),
    ],
}
for mod, funcs in CORE_MODULES.items():
    w(f"### `{mod}`")
    w()
    for fname, desc in funcs:
        w(f"- **`{fname}`** — {desc}")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# PART 6 — TOOL CATALOG
# ═══════════════════════════════════════════════════════════════════════════════
section(f"Part 6: Complete tool catalog ({len(tools)} tools)", 2)
w(f"All **{len(tools)}** tools registered via `@register` decorator. Grouped by category.")
w()
w(f"**Approval-gated tools ({len(APPROVAL_TOOLS)}):** `{', '.join(APPROVAL_TOOLS)}`")
w()
w(f"**Side-effect tools (approval + cautious writes):** `{', '.join(SIDE_EFFECT_TOOLS)}`")
w()
for cat in sorted(cats.keys()):
    w(f"### Category: `{cat}` ({len(cats[cat])} tools)")
    w()
    for t in sorted(cats[cat], key=lambda x: x.name):
        tool_entry(t)

# ═══════════════════════════════════════════════════════════════════════════════
# PART 7 — RAG VARIANTS
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 7: Memory brain & all RAG variants", 2)

RAG_VARIANTS = [
    ("Vector store (Chroma/Qdrant)", "memory/vector_store.py", "Default semantic storage for conversations, lessons, contacts",
     "Fuzzy recall, embedding similarity", "Embedding model mismatch; empty collection returns nothing — always check SQL for status fields",
     "search_memory, save_memory, add to conversations collection"),
    ("hybrid_search", "memory/retrieval.py", "BM25 + dense + RRF — entity names need lexical match",
     "Investor names, codenames, exact phrases", "rank_bm25 not installed → dense-only gracefully",
     "deep_recall tool, _memory_context in core.py"),
    ("episodic_recall", "memory/retrieval.py", "Recency + importance weighting like Generative Agents",
     "What happened this week?", "Old but important events may rank below recent noise — tune importance metadata",
     "fused_recall with episodic scoring"),
    ("fused_recall", "memory/retrieval.py", "Multi-collection hybrid with unified ranking",
     "Cross-domain questions spanning CRM + conversations", "Higher latency — more collections searched",
     "Used when query spans multiple memory types"),
    ("tool_retrieval (Tool-RAG)", "agent/tool_retrieval.py", "Retrieve relevant tool schemas per turn",
     "Every user turn with TOOL_RAG=true", "Wrong tools retrieved → bad tool choice; _CORE set mitigates",
     "schemas_for_message before execute_loop"),
    ("self_rag", "agent/self_rag.py", "Decide if retrieval needed; grade relevance",
     "Ambiguous whether memory holds answer", "Over-refusal if threshold too high",
     "self_rag_grade before injecting chunks"),
    ("graphrag", "memory/graphrag.py", "Community summaries over knowledge graph",
     "Who knows X? Network-level questions", "Stale until nightly consolidation rebuild",
     "ask_network, build_communities in job_consolidate_memory"),
    ("context spaces", "memory/context_store.py, context/resolver.py", "Project-scoped document RAG",
     "Deck draft, spec doc isolation", "Wrong space alias → missing context",
     "build_context_block in core.run"),
]
w("| Variant | Module | WHY | WHEN | Failure modes | Tools |")
w("|---|---|---|---|---|---|")
for name, mod, why, when, fail, tools_used in RAG_VARIANTS:
    w(f"| {name} | `{mod}` | {why} | {when} | {fail} | {tools_used} |")
w()
for name, mod, why, when, fail, tools_used in RAG_VARIANTS:
    w(f"#### Deep dive: {name}")
    w()
    w(f"- **Module:** `{mod}`")
    w(f"- **Why it exists:** {why}")
    w(f"- **When to use:** {when}")
    w(f"- **Failure modes:** {fail}")
    w(f"- **Related tools:** {tools_used}")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# PART 8 — GATES
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 8: Gates, HITL, policy & safety", 2)

w("### 8.1 Policy tiers (`agent/policy.py`)")
w()
w("| Tier | Config | Behavior |")
w("|---|---|---|")
w("| cautious | AUTONOMY_LEVEL=cautious | requires_approval tools + _WRITE_TOOLS need approval |")
w("| balanced | default | only requires_approval tools gated |")
w("| autonomous | AUTONOMY_LEVEL=autonomous or AUTO_APPROVE=true | all tools execute immediately |")
w()
w("`_WRITE_TOOLS`: add_contact, update_contact_status, set_followup, add_task, calendar_create_event, set_reminder, add_goal, graph_link")
w()
w("LECE `trust.py` adaptive_decide never goes below static AUTONOMY_LEVEL floor.")
w()
w("### 8.2 Approvals flow (`agent/approvals.py`)")
w()
w("1. loop gets decision=`approve` → critic.precheck_action for high-stakes")
w("2. approvals.enqueue(tool_name, args, risk_note) → SQLite approvals row")
w("3. bot or scheduler sends Telegram message with InlineKeyboardButton")
w("4. CallbackQueryHandler parses approve:N / reject:N")
w("5. On approve: registry.call executes; status→executed; result stored")
w()
w("### 8.3 Injection defense (`agent/safety.py`)")
w()
w("- Tool outputs wrapped as untrusted — never promoted to system instructions")
w("- External email/web content cannot override constitution")
w("- HTML stripped where applicable; summarization path has no tool access")
w()
w("### 8.4 Budget (`agent/budget.py`)")
w()
w("- `DAILY_LLM_CALL_CAP` — 0=unlimited; non-zero hard stop")
w("- `AGENT_PAUSED` kill switch checked in core.run and router")
w("- Recovery LLM calls in healing count against cap")
w()
w("### 8.5 LoRA gate (`agent/cognition/train/gate.py`)")
w()
w("- Tier B LECE training: promote adapter only if eval score beats baseline")
w("- Default LECE_DISTILL_TRAIN=false — scaffold only")
w("- modelfile.py builds Ollama Modelfile for promoted adapter")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 9 — TELEGRAM
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 9: Telegram interface", 2)

w("### Handlers (`bot/handlers.py`)")
w()
w("| Handler | Trigger | Role |")
w("|---|---|---|")
w("| start | /start | Welcome + capability overview |")
w("| handle_message | TEXT | Main agent path → core.run |")
w("| handle_voice | VOICE/AUDIO | Transcribe → core.run; optional voice reply |")
w("| handle_media | PHOTO/DOCUMENT | Vision describe_image → core.run |")
w("| approvals_cmd | /approvals | List pending with inline buttons |")
w("| on_approval_button | callback approve/reject | Execute or reject queued action |")
w("| pause/resume/status | commands | Ops control |")
w()
w("### Middleware (`bot/middleware.py`)")
w()
w("`is_authorized(user_id)` — matches MY_TELEGRAM_USER_ID unless PUBLIC_ACCESS=true.")
w()
w("### Long polling vs webhook")
w()
w("`main.py` uses `app.run_polling(drop_pending_updates=True)` — **not webhook**.")
w("Rationale: local dev without public HTTPS; simpler single-process deployment.")
w("Tradeoff: slight latency vs webhook; acceptable for cofounder UX.")
w()
w("### Inline keyboards")
w()
w("Approvals use InlineKeyboardMarkup with callback_data `approve:{id}` and `reject:{id}`.")
w("Scheduler proactive approvals use same pattern via send_approval_to_user.")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 10 — SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 10: Scheduler & proactive autonomy", 2)

SCHEDULER_JOBS = [
    ("daily_briefing", "08:00 daily", "Morning pipeline/tasks summary via report specialist", "job_daily_briefing"),
    ("followup_reminder", "10:00 daily", "CRM contacts needing follow-up today", "job_followup_reminder"),
    ("backup", "02:00 daily", "Nightly data backup to data/backups/", "job_backup"),
    ("consolidate_memory", "03:00 daily", "Memory consolidation + GraphRAG rebuild", "job_consolidate_memory"),
    ("lece_distill", "03:30 daily (LECE_DISTILL_HOUR:30)", "Principle distillation from traces", "job_distill"),
    ("check_monitors", "09:30, 15:30, 20:30 daily", "Topic monitor web search for fresh URLs", "job_check_monitors"),
    ("check_inbox", "Every hour :15 from 09:00-21:00", "Email reply tracking loop", "job_check_inbox"),
    ("heartbeat", "Every HEARTBEAT_HOURS (default 4) from 09:00-21:00", "Proactive agent self-check + optional swarm", "job_heartbeat"),
    ("watchdog", "Every WATCHDOG_MINUTES (default 30)", "Self-test and auto-remediation", "job_watchdog"),
    ("swarm_dlq_retry", "Every 15 minutes", "Retry failed swarm jobs from DLQ", "job_swarm_dlq_retry"),
    ("reminder_*", "Dynamic DateTrigger per reminder", "One-off or recurring user reminders", "job_fire_reminder"),
]
w("| Job ID | Cron / trigger | Purpose | Function |")
w("|---|---|---|---|")
for jid, cron, purpose, func in SCHEDULER_JOBS:
    w(f"| `{jid}` | {cron} | {purpose} | `{func}` |")
w()
w("**Proactive nudges summary:** daily briefing 8am, follow-ups 10am, topic monitors 3x/day, inbox/replies hourly, heartbeat every 4h with swarm pass, plus user-scheduled reminders.")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 11 — INTEGRATIONS
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 11: External integrations", 2)

INTEGRATIONS = [
    ("Telegram", "TELEGRAM_BOT_TOKEN, MY_TELEGRAM_USER_ID, PUBLIC_ACCESS", "bot/handlers.py, main.py", "Primary interface"),
    ("Groq LLM", "GROQ_API_KEY", "llm/groq_client.py", "Fast general routing"),
    ("Gemini LLM", "GOOGLE_GEMINI_API_KEY", "llm/gemini_client.py", "Research/analysis routing"),
    ("OpenAI LLM", "OPENAI_API_KEY", "llm/openai_client.py", "Fallback provider"),
    ("Ollama", "OLLAMA_ENABLED, OLLAMA_BASE_URL, OLLAMA_MODEL", "llm/ollama_client.py", "Local offline fallback"),
    ("Gmail", "GMAIL_ADDRESS, GMAIL_APP_PASSWORD", "tools/email or outreach", "Send/receive email"),
    ("Google Calendar", "GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH", "agent/tools/calendar_tools.py", "Event CRUD"),
    ("Web search", "TAVILY_API_KEY, SERPER_API_KEY", "tools/web_search.py", "Tavily→Serper→DDG fallback chain"),
    ("X/Twitter", "X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN", "agent/tools/social_tools.py", "x_post approval-gated"),
    ("Qdrant", "VECTOR_BACKEND, QDRANT_URL, QDRANT_API_KEY", "memory/vector_store.py", "Remote vector backend"),
    ("Redis", "REDIS_URL, SWARM_WORKER_MODE=redis", "agent/swarm/workers/", "Distributed swarm queue"),
    ("MCP", "mcp_server.py runtime", "mcp_server.py", "External agent tool access"),
]
w("| Service | Env vars | Code | Role |")
w("|---|---|---|---|")
for svc, env, code, role in INTEGRATIONS:
    w(f"| {svc} | `{env}` | `{code}` | {role} |")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 12 — LECE
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 12: LECE — Lived-Experience Cognitive Engine", 2)

w("Full whitepaper: `docs/LECE.md`. Package: `agent/cognition/` (15 modules + train/).")
w()
w("### Pillar 1 — Experiential self-distillation")
w()
w("- Pipeline: traces JSONL → episodes.py → off-policy filter score≥0.6 → distill.py → principles")
w("- Semantic dedup via Chroma DefaultEmbeddingFunction")
w("- Effectiveness decay; quarantine below 0.2")
w("- manual.md rebuilt; injected turn-level (evolution) and step-level (loop.py)")
w("- Schedule: job_distill cron 03:30 daily")
w()
w("### Pillar 2 — Business digital twin + preplay")
w()
w("- Twin extends world_model with procedure graph twin_transitions")
w("- Sandbox: contextvars.SIMULATION intercepts registry.call")
w("- Preplay: N branches (LECE_PREPLAY_BRANCHES=3), modes learned/swarm/hybrid")
w("- High-stakes: send_email, x_post, writes — simulate then real via approval gate")
w("- Expectation feedback updates transition reliabilities")
w()
w("### Pillar 3 — Global Workspace + trust-calibrated autonomy")
w()
w("- workspace table: salience + decay; coalitions: perception, goals, healing, twin_risk")
w("- founder_model KV: risk tolerance, communication style learned from patterns")
w("- trust.py extends policy.decide; LECE_TRUST_MIN_TRIALS=5")
w("- Continuous loop optional: LECE_WORKSPACE_CONTINUOUS=false default; else replaces fixed heartbeat")
w()
w("**LECE tools:** distill_now, list_principles, preplay_action, simulate_strategy, twin_state, why_did_you, workspace_state, trust_report, founder_profile, lece_metrics")
w()
w("**LECE tables:** principles, twin_transitions, preplay_runs, workspace, founder_model, trust_scores, distill_runs")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 13 — SWARM
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 13: Multi-agent swarm orchestration", 2)

SWARM_PATHS = [
    (1, "Orchestrator-worker + fan-out/fan-in + AdaptOrch", "agent/swarm/runner.py, topology.py", "run_swarm, swarm_aggregate, route_topology"),
    (2, "Dynamic handoff (OpenAI Swarm style)", "agent/swarm/handoff.py", "handoff_start, handoff_to"),
    (3, "Blackboard / stigmergy", "agent/swarm/board.py", "run_blackboard, board_post, board_read"),
    (4, "Bio-inspired SwarmSys", "agent/swarm/profiles.py", "assign_swarm_agent, run_swarmsys, list_swarm_profiles"),
    (5, "Multi-agent debate + maker-checker", "agent/swarm/debate.py", "run_debate, run_maker_checker"),
    (6, "Mesh artifact convergence", "agent/swarm/mesh.py", "run_mesh"),
    (7, "Hierarchical hybrid", "agent/swarm/hierarchy.py", "run_hierarchical_swarm"),
    (8, "External swarm via MCP", "mcp_server.py", "All swarm tools exposed externally"),
    (9, "Proactive heartbeat swarms", "agent/swarm/proactive.py", "run_proactive_swarm"),
    (10, "Self-evolving swarm (Voyager + skills)", "agent/swarm/evolve.py", "run_evolve_swarm"),
    (11, "Optional LangGraph adapter", "agent/swarm/adapters/langgraph_adapter.py", "run_langgraph_swarm"),
    (12, "Distributed workers SQLite/Redis", "agent/swarm/workers/", "enqueue_swarm_job"),
]
w("### 13.1 The 12 swarm paths")
w()
w("| # | Technique | Module | Key tools |")
w("|---|---|---|---|")
for num, tech, mod, ktools in SWARM_PATHS:
    w(f"| {num} | {tech} | `{mod}` | {ktools} |")
w()
w("### 13.2 Ten specialists (`agent/subagent.py`)")
w()
w("| Specialist | Categories | Role |")
w("|---|---|---|")
for name, cats_s, role in [
    ("researcher", "research, perception", "Gather sourced facts; never invent"),
    ("outreach", "outreach, crm", "Draft messages; sending stays gated"),
    ("ops", "tasks, reminders, calendar, goals", "Scheduling and task precision"),
    ("analyst", "research, evolution", "Judgments and recommendations"),
    ("fundraising", "research, crm, outreach", "Investor pipeline and materials"),
    ("competitive_intel", "research, perception", "Competitor mapping"),
    ("content", "outreach, social, evolution", "Blog, social, newsletter copy"),
    ("legal_ops", "research, tasks", "Contracts/compliance tracking — not legal advice"),
    ("growth", "research, crm, outreach, goals", "Experiments and funnel optimization"),
    ("finance", "finance, research, chart", "Runway, burn, MRR analysis"),
]:
    w(f"| `{name}` | {cats_s} | {role} |")
w()
w("Guardrails: every swarm agent uses execute_loop; SWARM_MAX_AGENTS=5, SWARM_MAX_ROUNDS=10, SWARM_MAX_HANDOFFS=5.")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 14 — SELF-HEALING
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 14: Self-healing control plane", 2)

HEALING_TECHNIQUES = [
    (1, "Retry + exponential backoff + jitter", "Infrastructure", "healing/retry.py", "Transient blips retried before failover"),
    (2, "3-state circuit breaker", "Infrastructure", "healing/circuit.py", "CLOSED/OPEN/HALF_OPEN per provider and tool"),
    (3, "Tool fallback chains", "Infrastructure", "healing/fallback.py", "tavily→serper→duckduckgo style chains"),
    (4, "Provider health routing", "Infrastructure", "llm/router.py", "Adaptive routing by live telemetry"),
    (5, "Failure taxonomy + diagnosis", "Execution", "healing/diagnose.py", "Classify timeout/args/wrong-tool/empty/etc."),
    (6, "Local argument repair", "Execution", "healing/repair.py", "Fix malformed args from schema + error"),
    (7, "Self-healing tool router", "Execution", "healing/router.py", "Reweight failed tool, route around without LLM"),
    (8, "Tool substitution", "Execution", "healing/fallback.py", "scrape_url ↔ web_search equivalents"),
    (9, "Stuck-loop detection", "Execution", "agent/loop.py", "Break infinite repeat of same failing call"),
    (10, "Step-level reflection", "Cognitive", "agent/loop.py + critic.py", "Reflect after each step, not just at end"),
    (11, "Metacognitive anomaly detection", "Cognitive", "healing/metacog.py", "MASC-style step scoring via local embedder"),
    (12, "Adaptive replanning", "Cognitive", "agent/planner.py", "replan_on_failure() preserves completed work"),
    (13, "Output schema validation", "Cognitive", "healing/repair.py", "JSON auto-repair for malformed LLM output"),
    (14, "Swarm cross-verification", "Cognitive", "agent/swarm/debate.py", "Maker-checker as healing primitive"),
    (15, "Checkpoint + rollback", "State", "healing/checkpoint.py", "Snapshot per step; roll back on failure"),
    (16, "Compensating transactions", "State", "healing/checkpoint.py", "Undo side effects of failed multi-step actions"),
    (17, "Durable replay recovery", "State", "scripts/replay.py", "Replay from immutable action_log/traces"),
    (18, "DB + vector self-repair", "State", "healing/storage.py", "SQLite reconnect; Chroma/Qdrant liveness"),
    (19, "Watchdog + self-test", "System", "healing/watchdog.py", "Periodic health check + auto-remediation"),
    (20, "Generated-tool quarantine", "System", "agent/skills_factory.py", "Broken self-authored tools moved to quarantine"),
    (21, "Swarm DLQ + auto-retry", "System", "agent/swarm/workers/", "Failed jobs re-queued with backoff"),
    (22, "Bulkhead isolation", "System", "agent/swarm/runner.py", "Per-swarm agent caps prevent starvation"),
    (23, "Graceful degradation", "System", "healing/escalate.py", "Partial/cached answer instead of total failure"),
    (24, "Human escalation", "System", "healing/escalate.py", "Telegram alert after budget exhausted"),
    (25, "Failure ledger / memory", "Learning", "healing/ledger.py", "Persist failure→diagnosis→fix patterns"),
    (26, "Recovery-budget policy", "Learning", "healing/policy.py", "Cheap local repairs before global recovery"),
    (27, "Self-diagnostic tools", "Learning", "agent/tools/healing_tools.py", "run_self_test, health_report, heal_now"),
    (28, "Healing observability", "Learning", "agent/trace.py + store.py", "Healing events in traces + DB metrics"),
]
w("| # | Technique | Layer | Module | Description |")
w("|---|---|---|---|---|")
for row in HEALING_TECHNIQUES:
    w(f"| {row[0]} | {row[1]} | {row[2]} | `{row[3]}` | {row[4]} |")
w()
w("Recovery priority (cheapest first): retry → arg repair → substitute → reflexion/replan → rollback → degrade → escalate.")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 15 — LLM ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 15: LLM routing, caching & cost", 2)

w("### Provider cascade (`llm/router.py`)")
w()
w("| task_type | Chain order |")
w("|---|---|")
w("| general | groq → gemini → openai → ollama (if enabled) |")
w("| research | gemini → groq → openai → ollama |")
w("| outreach | groq → gemini → openai → ollama |")
w("| analysis | gemini → groq → openai → ollama |")
w()
w("Flow: semantic cache check → budget.check_before_call → try each provider → cache.put on success.")
w("RateLimitError on Groq triggers fallthrough to Gemini.")
w()
w("### Cost controls")
w()
w("- `SEMANTIC_CACHE=true` — near-duplicate prompt skip")
w("- `TOOL_RAG=true` — smaller tool schema payload")
w("- `DAILY_LLM_CALL_CAP` — hard daily limit")
w("- Cheaper models for planning/routing; analysis task_type for critic/planner")
w("- Ollama free last resort when OLLAMA_ENABLED=true")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 16 — DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 16: Data model — every table", 2)

DB_TABLES = [
    ("contacts", "memory/sql_store.py", "CRM contacts — name, company, status, follow-up dates"),
    ("companies", "memory/sql_store.py", "Company records linked to contacts"),
    ("tasks", "memory/sql_store.py", "Structured tasks with due dates and status"),
    ("notes", "memory/sql_store.py", "Free-form notes"),
    ("outreach_log", "memory/sql_store.py", "Sent outreach history"),
    ("reminders", "agent/store.py", "Scheduled reminders with repeat rules"),
    ("goals", "agent/store.py", "Active/done/paused founder goals"),
    ("lessons", "agent/store.py", "Evolution-learned lessons"),
    ("skills", "agent/store.py", "Reusable skill playbooks"),
    ("approvals", "agent/store.py", "HITL queue pending/approved/rejected"),
    ("action_log", "agent/store.py", "Immutable audit of every tool call"),
    ("plans", "agent/store.py", "Planner DAG headers"),
    ("subtasks", "agent/store.py", "Plan steps with depends_on"),
    ("strategies", "agent/store.py", "Epsilon-greedy A/B strategy variants"),
    ("monitors", "agent/store.py", "Topic watchlist for proactive search"),
    ("usage_daily", "agent/store.py", "LLM/tool token and cost tracking"),
    ("finance_log", "agent/store.py", "Cash, burn, MRR snapshots"),
    ("seen_emails", "agent/store.py", "Reply-loop dedup keys"),
    ("swarm_runs", "agent/store.py", "Swarm execution records"),
    ("swarm_board", "agent/store.py", "Blackboard posts per run"),
    ("swarm_agents", "agent/store.py", "Agent assignments per swarm run"),
    ("swarm_jobs", "agent/store.py", "Distributed worker job queue"),
    ("swarm_messages", "agent/store.py", "Inter-agent messages"),
    ("failures", "agent/store.py", "Healing failure records"),
    ("circuit_state", "agent/store.py", "Circuit breaker persistence"),
    ("checkpoints", "agent/store.py", "Turn step snapshots for rollback"),
    ("healing_events", "agent/store.py", "Recovery action audit"),
    ("principles", "agent/store.py", "LECE distilled principles"),
    ("twin_transitions", "agent/store.py", "Digital twin procedure graph edges"),
    ("preplay_runs", "agent/store.py", "Preplay simulation audit"),
    ("workspace", "agent/store.py", "Global Workspace items"),
    ("founder_model", "agent/store.py", "Theory-of-mind KV profile"),
    ("trust_scores", "agent/store.py", "Per-tool competence for adaptive autonomy"),
    ("distill_runs", "agent/store.py", "LECE distillation job history"),
    ("kg_entities", "memory/graph.py", "Knowledge graph nodes"),
    ("kg_relations", "memory/graph.py", "Knowledge graph edges"),
    ("kg_communities", "memory/graphrag.py", "GraphRAG community summaries"),
    ("context_spaces", "memory/context_store.py", "Scoped RAG space definitions"),
    ("context_assets", "memory/context_store.py", "Documents within a space"),
    ("context_aliases", "memory/context_store.py", "Query aliases to spaces"),
]
w("| Table | Module | Purpose |")
w("|---|---|---|")
for tbl, mod, purpose in DB_TABLES:
    w(f"| `{tbl}` | `{mod}` | {purpose} |")
w()
w("Single database file: `data/founder_os.db` (SQLite). Vector data: `data/chroma/` or Qdrant remote.")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 17 — FILE PATHS
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 17: File-by-file reference", 2)

FILE_PATHS = [
    ("main.py", "Entry point: Telegram polling, scheduler, dashboard, cognitive loop"),
    ("config.py", "All env-var-backed settings"),
    ("bot/handlers.py", "Telegram message/command/callback handlers"),
    ("bot/middleware.py", "Authorization gate"),
    ("bot/formatters.py", "Long message splitting for Telegram limits"),
    ("agent/core.py", "AgentCore plan→execute→verify"),
    ("agent/loop.py", "execute_loop ReAct MAX_STEPS=8"),
    ("agent/planner.py", "Plan-and-execute"),
    ("agent/critic.py", "Reflexion verify + precheck"),
    ("agent/registry.py", "Tool registration and call"),
    ("agent/subagent.py", "10 specialist sub-agents"),
    ("agent/policy.py", "Autonomy tiers"),
    ("agent/approvals.py", "HITL queue"),
    ("agent/safety.py", "Injection defense"),
    ("agent/budget.py", "Spend cap and pause"),
    ("agent/trace.py", "Flight recorder JSONL"),
    ("agent/store.py", "SQLite agent tables"),
    ("agent/evolution.py", "Reflection and lessons"),
    ("agent/identity.py", "System prompt + constitution"),
    ("agent/tool_retrieval.py", "Tool-RAG"),
    ("agent/self_rag.py", "Self-RAG grading"),
    ("agent/healing/", "28-technique self-healing package"),
    ("agent/swarm/", "12-path multi-agent orchestration"),
    ("agent/cognition/", "LECE cognitive engine"),
    ("memory/vector_store.py", "Chroma/Qdrant abstraction"),
    ("memory/retrieval.py", "hybrid_search, episodic_recall, fused_recall"),
    ("memory/sql_store.py", "CRM tasks contacts SQL"),
    ("memory/world_model.py", "Business snapshot block"),
    ("memory/graph.py", "Knowledge graph"),
    ("memory/graphrag.py", "Community summaries"),
    ("memory/consolidation.py", "Nightly memory merge"),
    ("memory/context_store.py", "Context spaces RAG"),
    ("llm/router.py", "Provider cascade"),
    ("llm/tool_client.py", "complete_with_tools for ReAct"),
    ("llm/cache.py", "Semantic cache"),
    ("scheduler/jobs.py", "All cron jobs"),
    ("specialists/", "10 specialist agent modules"),
    ("evals/", "Quality harness and LECE ablations"),
    ("mcp_server.py", "MCP external tool server"),
    ("api/server.py", "FastAPI dashboard backend"),
    ("data/traces/", "Per-turn JSONL flight recorder"),
    ("data/founder_os.db", "SQLite database"),
    ("docs/LECE.md", "LECE whitepaper"),
]
w("| Path | Purpose |")
w("|---|---|")
for path, purpose in FILE_PATHS:
    w(f"| `{path}` | {purpose} |")

# ═══════════════════════════════════════════════════════════════════════════════
# PART 18 — AMAZON INTERVIEW PREP
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 18: Amazon interview prep (Q-B01–Q-B05)", 2)

w("Rehearse these aloud in **STAR format** (Situation, Task, Action, Result). Map every answer to **Customer Obsession**: the founder is the customer; irreversible surprises are defects.")
w()

# Q-B01
w("### Q-B01 · \"Explain Founder OS like I'm an Amazon SDE-2 who will maintain it in prod.\"")
w()
w("**Main answer:**")
w()
w('Founder OS is a Telegram bot that acts as a constrained cofounder for a solo builder. Architecture: Telegram **long-polling** (not webhook) → Python async handler (`bot/handlers.py`) → **custom ReAct loop** (`agent/core.py` + `agent/loop.py`, not LangGraph for the main agent) → LLM proposes tool calls via `complete_with_tools` → executor runs tools (tasks/CRM/reminders/Gmail/Calendar/web search/swarm — full catalog of **117 tools**, with side-effect tools **`send_email`, `x_post`, `calendar_delete_event`, `create_tool`, `propose_code_change`** approval-gated) → results fed back until stop condition (`MAX_STEPS=8`). Memory: ChromaDB or Qdrant for semantic chunks; **SQLite as source of truth** for tasks, CRM, approvals. Safety: JSON schema per tool; HITL approval queue in Telegram with inline keyboards for side-effect tools. Scheduler proactive nudges: **daily briefing 08:00, follow-ups 10:00, backup 02:00, consolidation+GraphRAG 03:00, LECE distill 03:30, topic monitors 09:30/15:30/20:30, inbox reply loop hourly :15 (9–21), heartbeat every 4h (9–21) with optional proactive swarm, watchdog every 30m, swarm DLQ retry every 15m**, plus dynamic user reminders. I designed it so the founder is the customer — Customer Obsession maps to \"don\'t surprise the user with irreversible email.\"')
w()
w("**Follow-ups:**")
w()
QB01_FU = [
    ("Draw data flow for 'Remind me to email investor Friday and draft when I approve.'",
     "Parse intent → planner decides tools: `set_reminder` + `add_task(due=Friday)` + draft via outreach tools → SQLite insert task/reminder → `hybrid_search` retrieves past investor context from vector memory → present draft in Telegram → HITL gate on `send_email` → on Approve callback, `registry.call` executes send → log to action_log + embed summary to conversations collection after durable SQL write."),
    ("Why LangGraph instead of while loop?",
     "Honest answer: **main agent uses a while loop** (`execute_loop`), not LangGraph — simpler, fewer deps, fine for single-tenant. LangGraph is optional **only for swarm path 11** (`LANGGRAPH_ADAPTER=true`). Graph benefits: checkpointable state, conditional edges, clearer test seams — worth it for multi-step workflows where crashes mid-run matter. For hackathon I'd use a loop; we did, and added LangGraph as optional adapter for swarm experiments."),
    ("Why Telegram?",
     "Push notifications, mobile-first founder UX, zero frontend build. Tradeoff: rich approval UI is worse than web; we compensate with concise inline keyboards and `/approvals` command."),
    ("Single tenant or multi-tenant?",
     "Designed **single-tenant by default** (`MY_TELEGRAM_USER_ID`). PUBLIC_ACCESS=true allows demo multi-user but shares one brain — documented as unsafe for prod. For true multi-tenant: filter every SQL query and vector metadata by user_id; namespace Chroma collections per user. Cross-tenant leakage is the catastrophic bug class."),
]
w("| Follow-up | Answer |")
w("|---|---|")
for q, a in QB01_FU:
    w(f"| {q} | {a} |")
w()

# Q-B02
w("### Q-B02 · \"Your resume says hybrid memory. Vector DB alone failed — prove it.\"")
w()
w("**Main answer (STAR):**")
w()
w("**Situation:** Early version used embedding-only recall. **Task:** Answer 'What tasks are due before Friday?' **Action:** Vector search returned semantically similar notes about deadlines but **missed actual tasks** because embedding distance doesn't encode SQL date predicates. **Result:** Implemented hybrid architecture — SQLite source of truth for structured fields; Chroma/Qdrant for fuzzy recall ('what did we decide about pricing?'). Retrieval router: structured filters → SQL via `list_tasks`; conceptual → `hybrid_search` with BM25+RRF; both → merge with **priority on SQL for dates/status**.")
w()
QB02_FU = [
    ("Dual-write inconsistency scenario?",
     "Task marked done in SQL but embedding still says pending → agent resurrects stale plan. Mitigation: write SQL first, async embed; reads for status always hit SQL; vector lags acceptable for narrative memory, not pending/done."),
    ("How evaluate retrieval quality?",
     "Golden set ~30 queries in `evals/quality_scenarios.py`: exact pending tasks, fuzzy decisions, refusal cases. Metrics: context precision, faithfulness via `evals/judge.py`. We did **not** ship full RAGAS pipeline — use **`evals/` harness** (`quality_runner.py`, `runner.py`) as the production bar before scaling."),
    ("BM25 + dense hybrid?",
     "Yes — `memory/retrieval.py` implements BM25Okapi + dense + RRF (k=60). Optional cross-encoder rerank on top-20 when sentence-transformers installed. Rerank only when needed — cost/latency tradeoff."),
]
w("| Follow-up | Answer |")
w("|---|---|")
for q, a in QB02_FU:
    w(f"| {q} | {a} |")
w()

# Q-B03
w("### Q-B03 · \"Tool calling — wrong tool or hallucinated args. What breaks and what did you build?\"")
w()
w("**Main answer:**")
w()
w("Failure modes: (1) wrong tool chosen, (2) right tool wrong args, (3) tool succeeds but user didn't want side effect. Defenses: JSON schema per tool with types/enums; Tool-RAG allowlist per turn + _CORE set; HITL on `requires_approval` tools; **max iterations = 8** (`MAX_STEPS` in `agent/loop.py`); audit `action_log` row per tool call; healing layer with arg repair, substitution, stuck-loop detection.")
w()
QB03_FU = [
    ("Prompt injection via fetched email body?",
     "Treat tool outputs as untrusted — `safety.wrap_tool_result` never promotes email content to system channel. Constitution forbids following instructions in external content. Optional summarization path has no tool access."),
    ("Concrete wrong-tool anecdote?",
     "User asked **'What tasks do I have due this week?'** Agent called **`web_search`** instead of **`list_tasks`** → returned irrelevant SEO articles about task-management apps. Fix: Tool-RAG now strongly retrieves task tools for task utterances; `list_tasks` reads SQLite with date filters; added stuck-loop + metacog anomaly logging when research tools appear on internal-state queries. Template filled with real failure mode from development."),
    ("Max iterations number?",
     "**8** (`MAX_STEPS=8` in `agent/loop.py`). Reason: prevent runaway token spend; after cap, return partial work + ask user to continue."),
]
w("| Follow-up | Answer |")
w("|---|---|")
for q, a in QB03_FU:
    w(f"| {q} | {a} |")
w()

# Q-B04
w("### Q-B04 · GenAI design choice")
w()
w("**Interviewer:** \"What's one non-trivial GenAI design choice in Founder OS?\"")
w()
w("**Main answer:**")
w()
w("When to retrieve vs answer from parametric knowledge. If user asks 'what's our runway assumption?', that must hit stored founder memory (`finance_log`, `world_state`), not model weights. Self-RAG + hybrid router classifies needs_evidence; below relevance threshold → refuse or clarify rather than hallucinate. Second choice: **HITL on side effects** — autonomy for read, approval for write — mirrors how I'd want an internal Amazon agent on production systems.")
w()
QB04_FU = [
    ("RAG vs fine-tune for Founder OS?",
     "RAG wins: data changes daily, user-specific, small corpus — fine-tune expensive and stale. LECE Tier B LoRA scaffold exists (`agent/cognition/train/`) but default off; RAG + principle distillation sufficient."),
    ("Observability?",
     "Flight recorder `data/traces/*.jsonl`: turn_id, tool name, token counts, retrieval ids, HITL outcome — never OAuth tokens. Replay with redaction via `scripts/replay.py`."),
    ("Cost control?",
     "Semantic cache; Tool-RAG; cheaper models for planner/critic (task_type=analysis); Groq-first cascade; DAILY_LLM_CALL_CAP; MAX_STEPS=8."),
]
w("| Follow-up | Answer |")
w("|---|---|")
for q, a in QB04_FU:
    w(f"| {q} | {a} |")
w()

# Q-B05
w("### Q-B05 · \"Scale Founder OS to 10,000 founders on AWS — 90 seconds.\"")
w()
w("**Main answer:**")
w()
w("API tier stateless behind ALB; per-tenant Postgres shard or **strict user_id RLS**; Qdrant per tenant or single cluster with **hard metadata filters**; SQS for embed jobs and outbound email; Redis for rate limits and sessions; Secrets Manager for keys; LLM calls with **token budget per user/day**; HITL stays Telegram or migrate approval to web for enterprise. Keep execute_loop semantics; horizontal scale workers; scheduler as separate service with per-tenant cron shards.")
w()
QB05_FU = [
    ("Biggest bottleneck?",
     "LLM cost + latency, not Telegram. Mitigate: async notifications, batch non-urgent nudges, semantic cache, Tool-RAG, cap MAX_STEPS."),
    ("Why not one shared vector space?",
     "Leakage risk — embedding search without hard filter caused cross-user retrieval bugs in public RAG incidents. Namespace collections per user_id."),
]
w("| Follow-up | Answer |")
w("|---|---|")
for q, a in QB05_FU:
    w(f"| {q} | {a} |")
w()

w("### Customer Obsession mapping")
w()
w("| Amazon LP | Founder OS manifestation |")
w("|---|---|")
w("| Customer Obsession | Founder is customer; HITL on irreversible actions |")
w("| Ownership | End-to-end turn lifecycle traced; you own failures in action_log |")
w("| Invent and Simplify | Custom ReAct loop over heavy framework for main path |")
w("| Are Right, A Lot | Critic verify + Self-RAG refuse over hallucinate |")
w("| Learn and Be Curious | LECE distillation from own traces |")
w("| Insist on Highest Standards | evals/ harness, 28 healing techniques |")
w("| Bias for Action | Heartbeat proactive swarms on active goals |")
w("| Frugality | Semantic cache, Ollama fallback, Tool-RAG |")
w()
w("### STAR template examples")
w()
STAR_EXAMPLES = [
    ("Hybrid memory fix (Q-B02)", "Embedding-only recall missed due tasks", "Ground task queries in SQL", "Built hybrid_search + SQL router; eval harness regression tests", "Accurate deadline answers; fewer hallucinated task lists"),
    ("Wrong tool incident (Q-B03)", "web_search on internal task query", "Prevent irrelevant external results", "Tool-RAG + list_tasks SQL path + metacog logging", "Task queries now hit SQL first; anecdote ready for interview"),
    ("HITL email gate", "Founder almost sent wrong investor email", "Never auto-send side effects", "approvals.enqueue + inline Telegram buttons + critic precheck", "Zero surprise sends in production usage"),
]
for title, situation, task, action, result in STAR_EXAMPLES:
    w(f"**{title}**")
    w(f"- Situation: {situation}")
    w(f"- Task: {task}")
    w(f"- Action: {action}")
    w(f"- Result: {result}")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# PART 19 — PRACTICE QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 19: Additional practice interview questions", 2)

PRACTICE_QA = [
    ("What is MAX_STEPS and why 8?", "Constant in agent/loop.py limiting ReAct iterations. Prevents runaway token spend and infinite tool loops. After 8 steps agent asks user to continue.", "loop.py execute_loop"),
    ("Difference between HISTORY_TURNS and MAX_STEPS?", "HISTORY_TURNS=8 is conversation messages in prompt; MAX_STEPS=8 is tool rounds per turn. Orthogonal limits.", "core.py vs loop.py"),
    ("How does Tool-RAG work?", "Embed tool name+description; retrieve top TOOL_RAG_K=16 per message; union with _CORE always-on tools.", "tool_retrieval.py"),
    ("What tools require approval?", f"{', '.join(APPROVAL_TOOLS)} — requires_approval=True in registry.", "registry.py"),
    ("Explain the policy tiers.", "cautious/balanced/autonomous in policy.py; LECE trust never below static floor.", "policy.py trust.py"),
    ("How does preplay differ from approval?", "Preplay simulates on twin before real execution; approval is founder consent gate. Both can apply.", "cognition/preplay.py"),
    ("What is the flight recorder?", "JSONL per turn in data/traces/ via trace.py — plan, tools, healing, decisions.", "trace.py"),
    ("How do you kill the agent instantly?", "AGENT_PAUSED=true — core.run returns paused message; scheduler jobs no-op.", "config.py core.py"),
    ("Explain RRF in one sentence.", "Reciprocal Rank Fusion merges BM25 and dense ranked lists without score normalization tuning.", "retrieval.py"),
    ("When would you use GraphRAG over vector search?", "Network-level questions: who knows X, community themes — ask_network tool.", "graphrag.py"),
    ("What is Self-RAG?", "Grades whether retrieval needed and if chunks relevant before injecting context.", "self_rag.py"),
    ("How does the LLM router pick a provider?", "Task-type chain in ROUTING dict; try in order; RateLimitError fallthrough; Ollama last if enabled.", "llm/router.py"),
    ("What happens when circuit breaker opens?", "healing/circuit.py blocks calls; route_around or substitute tool; reset after cooldown.", "healing/circuit.py"),
    ("Describe stuck-loop detection.", "Same tool+args signature repeated → degrade with partial result, escalate if needed.", "loop.py orchestrator"),
    ("What is LECE Pillar 1?", "Experiential self-distillation: traces → principles → manual injection.", "cognition/distill.py"),
    ("What is the digital twin?", "Procedure graph over business state predicting action outcomes for preplay.", "cognition/twin.py"),
    ("Name 3 swarm paths.", "Any from: orchestrator-worker, handoff, blackboard, SwarmSys, debate, mesh, hierarchical, MCP, proactive, evolve, LangGraph, distributed workers.", "agent/swarm/"),
    ("How many specialists?", "10: researcher, outreach, ops, analyst, fundraising, competitive_intel, content, legal_ops, growth, finance.", "subagent.py"),
    ("Why long polling not webhook?", "No public HTTPS needed for local dev; simpler ops; acceptable latency for cofounder use case.", "main.py"),
    ("How are traces used for learning?", "LECE episodes segment traces; distill extracts principles; off-policy filter score≥0.6.", "cognition/episodes.py"),
    ("What is epsilon-greedy in Founder OS?", "strategy A/B in optimizer.py — explore new variants vs exploit best in strategies table.", "optimizer.py"),
    ("How do you test retrieval quality?", "evals/quality_scenarios.py golden queries; evals/judge.py faithfulness scoring.", "evals/"),
    ("What is context spaces?", "Project-scoped RAG isolation — deck in one space, CRM notes in another.", "context_store.py"),
    ("Explain maker-checker.", "One swarm agent drafts, another verifies — run_maker_checker in debate.py.", "swarm/debate.py"),
    ("What is graceful degradation?", "healing/escalate.degrade returns partial/cached answer with honest explanation when recovery exhausted.", "healing/escalate.py"),
    ("How does consolidation work nightly?", "job_consolidate_memory 03:00 — merge notes, rebuild graph, GraphRAG communities.", "consolidation.py"),
    ("What is the constitution?", "Hard safety rules in identity.py system prompt — non-negotiable even at autonomous level.", "identity.py"),
    ("Difference between delegate and run_swarm?", "delegate: one specialist handoff; run_swarm: multi-agent topology with fan-out/debate/mesh.", "orchestration_tools swarm_tools"),
    ("How is cost tracked?", "usage_daily table; budget.note_call per LLM invocation; DAILY_LLM_CALL_CAP enforcement.", "budget.py store.py"),
    ("What would you monitor in prod?", "Trace error rate, circuit states, approval queue depth, LLM cap usage, healing escalations, vector/SQL health via watchdog.", "healing/watchdog.py trace.py"),
]
for i, (q, a, ref) in enumerate(PRACTICE_QA, 1):
    w(f"### Q{i}. {q}")
    w()
    w(f"**Answer:** {a}")
    w()
    w(f"**Code reference:** `{ref}`")
    w()

for i, (q, a, ref) in enumerate(PRACTICE_QA, 1):
    w(f"#### Q{i} — interviewer probe")
    w()
    w(f"If challenged on Q{i}, add: \"In production I'd point you to `{ref}` and the trace JSONL for a concrete example.\"")
    w(f"Whiteboard: draw box for `{ref}` connected to execute_loop.")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# PART 20 — TEACHING SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 20: Teaching walkthrough scripts", 2)
w("Five **2-hour sessions**. Each includes timing, activity, and verification.")
w()

SESSIONS = [
    ("Session 1: Foundations & first message", [
        ("0:00–0:20", "Read Part 0–1; draw mental model diagram from memory", "Learner can explain agent vs chatbot"),
        ("0:20–0:40", "Setup .env; run main.py; send /start", "Bot responds authorized"),
        ("0:40–1:00", "Send 'what can you do?' — open trace JSONL", "Identify core.run in stack"),
        ("1:00–1:20", "Walk glossary terms: ReAct, HITL, SQLite, Chroma", "Define 10 terms with file paths"),
        ("1:20–1:40", "Send simple task: 'add a reminder tomorrow'", "See set_reminder in trace"),
        ("1:40–2:00", "Review Part 3 architecture diagrams; Q&A", "Redraw high-level arch without notes"),
    ]),
    ("Session 2: Turn lifecycle & memory", [
        ("0:00–0:25", "Part 4 turn lifecycle — trace one message step by step", "Name all 10 steps"),
        ("0:25–0:50", "Part 7 RAG — run search_memory vs list_tasks", "Explain hybrid vs SQL"),
        ("0:50–1:10", "Inspect data/founder_os.db tasks table", "SQL is source of truth"),
        ("1:10–1:30", "Part 8 gates — set AUTONOMY_LEVEL=cautious; trigger approval", "See inline keyboard"),
        ("1:30–1:50", "Part 2 glossary drill — 20 random terms", "80% correct definitions"),
        ("1:50–2:00", "Practice Q-B02 aloud", "STAR hybrid memory story"),
    ]),
    ("Session 3: Tools, swarm & healing", [
        ("0:00–0:30", "Part 6 — pick 10 tools; explain category + approval", "Tool catalog navigation"),
        ("0:30–0:55", "Part 13 — 12 swarm paths whiteboard", "Match path to module"),
        ("0:55–1:20", "Run delegate or run_swarm on safe read-only goal", "Trace sub-agent actor"),
        ("1:20–1:45", "Part 14 — 28 healing techniques; run health_report", "Name 5 techniques"),
        ("1:45–2:00", "Practice Q-B03 wrong-tool anecdote", "web_search vs list_tasks story"),
    ]),
    ("Session 4: LECE, scheduler & integrations", [
        ("0:00–0:30", "Part 12 LECE three pillars; read docs/LECE.md", "Explain distillation vs preplay"),
        ("0:30–0:50", "Part 10 scheduler cron table", "Recite 5 job times"),
        ("0:50–1:10", "Part 11 integrations env vars", "Map Gmail, Calendar, Groq keys"),
        ("1:10–1:35", "Part 15 LLM router; trigger fallback discussion", "Draw cascade diagram"),
        ("1:35–2:00", "Practice Q-B04 GenAI design choice", "RAG vs parametric answer"),
    ]),
    ("Session 5: Interview dry-run & scaling", [
        ("0:00–0:40", "Part 18 Q-B01–Q-B05 full aloud with follow-ups", "90-second Q-B05 answer"),
        ("0:40–1:00", "Part 19 — random 10 practice questions", "Answer without notes"),
        ("1:00–1:25", "Part 22 AWS scaling whiteboard", "ALB, RLS, SQS, per-tenant vectors"),
        ("1:25–1:45", "Part 21 failure modes — pick 5 to debug", "Trace + fix path"),
        ("1:45–2:00", "Mock Amazon loop: explain + whiteboard + deep dive", "Confident Customer Obsession tie-in"),
    ]),
]
for sess_title, blocks in SESSIONS:
    w(f"### {sess_title}")
    w()
    w("| Time | Activity | Success criteria |")
    w("|---|---|---|")
    for time, activity, criteria in blocks:
        w(f"| {time} | {activity} | {criteria} |")
    w()
    for time, activity, criteria in blocks:
        w(f"**{time}** — {activity}")
        w(f"- Instructor note: pause for questions after each block.")
        w(f"- Learner delivers: {criteria}")
        w()

# ═══════════════════════════════════════════════════════════════════════════════
# PART 21 — FAILURE MODES
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 21: Failure modes & debugging", 2)

FAILURE_MODES = [
    ("Vector says task pending but SQL says done", "Dual-write lag", "Always read status from SQL; re-embed after mark_done", "list_tasks not search_memory for status"),
    ("Agent calls web_search for internal query", "Wrong tool / Tool-RAG miss", "Improve utterance overlap; ensure task tools in retrieval", "Metacog log + Tool-RAG tuning"),
    ("Infinite tool loop", "Stuck loop", "MAX_STEPS=8 + detect_stuck_loop", "Check trace for repeated signatures"),
    ("Empty retrieval", "Cold vector collection", "Fall back to SQL + ask user to save_memory", "hybrid_search returns []"),
    ("Approval stuck pending", "User didn't tap button", "/approvals or text approve N", "approvals table status"),
    ("Groq rate limit cascade fail", "All providers down", "Enable Ollama fallback; check keys", "router.py logs"),
    ("Cross-tenant data leak", "PUBLIC_ACCESS demo mode", "Disable PUBLIC_ACCESS; filter by user_id", "middleware.py"),
    ("Prompt injection in email", "Untrusted content", "safety.wrap_tool_result; constitution", "Never execute email instructions"),
    ("Runaway LLM cost", "No cap / long loop", "DAILY_LLM_CALL_CAP; MAX_STEPS", "usage_daily table"),
    ("GraphRAG stale", "Missed consolidation", "Check job_consolidate_memory 03:00 logs", "Manual graph.build_from_crm"),
    ("Healing makes things worse", "Healer bug", "HEALING_ENABLED=false temporary; fix forward", "Orchestrator falls back on internal error"),
    ("Swarm handoff infinite", "Loop in handoffs", "SWARM_MAX_HANDOFFS=5", "handoff.py logs"),
    ("Broken generated tool", "skills_factory quarantine", "Remove from registry; reset quarantine", "Generated-tool quarantine technique #20"),
    ("Chroma corrupt", "Disk issue", "healing/storage self-repair; restore backup", "job_backup 02:00"),
    ("Calendar token expired", "OAuth drift", "Re-run scripts/google_auth.py", "calendar_tools errors"),
    ("Heartbeat spam", "Over-eager proactive", "Tune HEARTBEAT_HOURS; verify NOTHING response", "job_heartbeat logs"),
    ("Preplay wrong branch", "Twin inaccuracy", "Expectation feedback; more traces", "preplay_runs table"),
    ("Principle quarantine", "Low effectiveness", "Review distill output; adjust LECE_PRINCIPLES_K", "principles table effectiveness"),
    ("Redis queue unavailable", "SWARM_WORKER_MODE misconfig", "Fall back to sqlite worker mode", "workers/queue.py"),
    ("Telegram parse error", "Markdown break", "formatters split_long_message; plain fallback", "handlers.py try/except"),
]
for i, (symptom, cause, fix, debug) in enumerate(FAILURE_MODES, 1):
    w(f"### {i}. {symptom}")
    w()
    w(f"- **Likely cause:** {cause}")
    w(f"- **Fix:** {fix}")
    w(f"- **Debug path:** {debug}")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# PART 22 — AWS SCALING
# ═══════════════════════════════════════════════════════════════════════════════
section("Part 22: Scaling to 10,000 founders on AWS", 2)

w("### Target architecture")
w()
diagram("""flowchart TB
    Users[10000 Telegram users] --> TGAPI[Telegram API]
    TGAPI --> ALB[AWS ALB]
    ALB --> ECS[ECS/Fargate stateless workers]
    ECS --> RDS[(RDS Postgres user_id RLS)]
    ECS --> Qdrant[Qdrant Cloud filtered]
    ECS --> Redis[ElastiCache rate limit]
    ECS --> SQS[SQS embed email jobs]
    SQS --> Workers[Async workers]
    ECS --> SM[Secrets Manager]
    ECS --> LLM[LLM APIs per-tenant budget]
    Workers --> RDS
    Workers --> Qdrant""")
w()
w("### Sharding strategy")
w()
w("- **Compute:** Horizontal pod autoscaling on message queue depth")
w("- **SQL:** Postgres with strict RLS on user_id OR schema-per-tenant for largest customers")
w("- **Vectors:** Collection per user_id or metadata filter mandatory on every query")
w("- **Scheduler:** EventBridge per-shard cron; heartbeat batched off-peak")
w("- **Traces:** S3 JSONL partitioned by user_id/date; Athena for analytics")
w("- **HITL:** Telegram remains; enterprise tier gets web approval portal")
w()
w("### Migration checklist from single-box")
w()
for step in [
    "Extract config to Secrets Manager; remove .env from images",
    "Replace SQLite with Postgres; add user_id column to all tables",
    "Move Chroma to Qdrant Cloud with tenant metadata",
    "Externalize scheduler to dedicated service",
    "Add SQS between turn completion and embedding jobs",
    "Implement per-tenant DAILY_LLM_CALL_CAP in Redis",
    "Load test execute_loop at p99 latency target",
    "Run evals/ harness in CI on every deploy",
]:
    w(f"- {step}")
w()

# ═══════════════════════════════════════════════════════════════════════════════
# APPENDICES
# ═══════════════════════════════════════════════════════════════════════════════
section("Appendix A: Environment variables", 2)
w("See `.env.example` for full list. Critical vars:")
w()
for var in [
    "TELEGRAM_BOT_TOKEN", "MY_TELEGRAM_USER_ID", "GROQ_API_KEY", "GOOGLE_GEMINI_API_KEY",
    "AUTONOMY_LEVEL", "AUTO_APPROVE", "DAILY_LLM_CALL_CAP", "AGENT_PAUSED",
    "VECTOR_BACKEND", "QDRANT_URL", "TOOL_RAG", "TOOL_RAG_K",
    "SWARM_ENABLED", "HEALING_ENABLED", "LECE_ENABLED", "HEARTBEAT_HOURS",
]:
    w(f"- `{var}`")
w()

section("Appendix B: Concept → code map", 2)
CONCEPT_MAP = [
    ("ReAct loop", "agent/loop.py"),
    ("Plan-and-execute", "agent/planner.py"),
    ("Reflexion", "agent/critic.py"),
    ("HITL", "agent/approvals.py"),
    ("Hybrid RAG", "memory/retrieval.py"),
    ("Tool-RAG", "agent/tool_retrieval.py"),
    ("Self-RAG", "agent/self_rag.py"),
    ("GraphRAG", "memory/graphrag.py"),
    ("Swarm", "agent/swarm/"),
    ("Self-healing", "agent/healing/"),
    ("LECE", "agent/cognition/"),
    ("Scheduler", "scheduler/jobs.py"),
    ("Traces", "agent/trace.py"),
    ("Eval harness", "evals/"),
]
w("| Concept | Primary code |")
w("|---|---|")
for concept, code in CONCEPT_MAP:
    w(f"| {concept} | `{code}` |")
w()

section("Appendix C: Eval suite & quality bar", 2)
w("- **`evals/runner.py`** — scenario-based agent eval entry")
w("- **`evals/quality_runner.py`** — quality regression suite")
w("- **`evals/quality_scenarios.py`** — golden ~30 queries (tasks, fuzzy recall, refusal)")
w("- **`evals/judge.py`** — LLM-as-judge for faithfulness/precision")
w("- **`evals/lece/`** — LECE ablation harness (principle vs instance, preplay on/off)")
w("- **`research/`** — extended research eval pipeline (separate from prod harness)")
w()
w("Production bar before scale: run quality_runner in CI; track context precision and faithfulness; no full RAGAS pipeline shipped — evals/ harness is the intentional substitute.")
w()

section("Expanded reference: tool category study notes", 2)
for cat in sorted(cats.keys()):
    w(f"### Study notes: `{cat}` ({len(cats[cat])} tools)")
    w()
    for t in sorted(cats[cat], key=lambda x: x.name):
        desc = (t.description or "")[:120]
        if len(t.description or "") > 120:
            desc += "..."
        w(f"- **`{t.name}`** — {desc}")
        w(f"  - Approval: {'yes' if t.requires_approval else 'no'}")
        w(f"  - Practice: explain when LLM picks this over siblings in `{cat}`.")
    w()

section("Expanded reference: glossary flashcard drills", 2)
for idx, entry in enumerate(GLOSSARY, 1):
    term = entry[0]
    w(f"{idx}. **{term}** — cover the card, recite: definition, file, why, example.")
    w()

section("Expanded reference: Amazon behavioral probes", 2)
BEHAVIORAL = [
    ("Tell me about a time you disagreed with a shortcut", "Chose HITL over full autonomy despite faster demo", "Founder trust > demo speed", "Approval gate shipped default"),
    ("How do you prioritize when everything is P0?", "Heartbeat budgets + DAILY_LLM_CALL_CAP + recovery budget", "Bounded autonomy", "No runaway loops in prod"),
    ("Describe debugging a production incident", "Trace JSONL → action_log → healing_events", "Flight recorder first", "Root cause in wrong-tool class"),
]
for prompt, situation, action, result in BEHAVIORAL:
    w(f"**Prompt:** {prompt}")
    w(f"- Situation: {situation}")
    w(f"- Action: {action}")
    w(f"- Result: {result}")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# EXPANDED APPENDIX D — FULL ENV REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════
section("Appendix D: Complete environment variable reference", 2)
ENV_VARS = [
    ("TELEGRAM_BOT_TOKEN", "—", "Telegram BotFather token", "main.py ApplicationBuilder"),
    ("MY_TELEGRAM_USER_ID", "—", "Authorized founder chat ID", "bot/middleware.py"),
    ("PUBLIC_ACCESS", "false", "Allow any Telegram user (demo only)", "bot/middleware.py"),
    ("GROQ_API_KEY", "—", "Groq LLM API key", "llm/groq_client.py"),
    ("GOOGLE_GEMINI_API_KEY", "—", "Gemini API key", "llm/gemini_client.py"),
    ("OPENAI_API_KEY", "—", "OpenAI fallback key", "llm/openai_client.py"),
    ("GMAIL_ADDRESS", "—", "Gmail account for send/receive", "outreach tools"),
    ("GMAIL_APP_PASSWORD", "—", "Gmail app password", "outreach tools"),
    ("SERPER_API_KEY", "—", "Serper web search API", "tools/web_search.py"),
    ("TAVILY_API_KEY", "—", "Tavily search (primary)", "tools/web_search.py"),
    ("AUTO_APPROVE", "false", "Skip approval gate globally", "agent/policy.py"),
    ("AUTONOMY_LEVEL", "balanced", "cautious|balanced|autonomous", "agent/policy.py"),
    ("HEARTBEAT_HOURS", "4", "Proactive heartbeat interval", "scheduler/jobs.py"),
    ("DAILY_LLM_CALL_CAP", "0", "Daily LLM cap (0=unlimited)", "agent/budget.py"),
    ("AGENT_PAUSED", "false", "Kill switch", "agent/core.py"),
    ("VOICE_REPLIES", "true", "Reply with voice to voice messages", "bot/handlers.py"),
    ("DASHBOARD_ENABLED", "true", "Start FastAPI dashboard", "main.py api/server.py"),
    ("OLLAMA_ENABLED", "false", "Enable local Ollama fallback", "llm/ollama_client.py"),
    ("OLLAMA_MODEL", "llama3.1", "Ollama model name", "llm/ollama_client.py"),
    ("VECTOR_BACKEND", "qdrant", "chroma|qdrant", "memory/vector_store.py"),
    ("QDRANT_URL", "—", "Qdrant cluster URL", "memory/vector_store.py"),
    ("SEMANTIC_CACHE", "true", "Cache duplicate LLM prompts", "llm/cache.py"),
    ("CACHE_DISTANCE_THRESHOLD", "0.08", "Semantic cache similarity threshold", "llm/cache.py"),
    ("TOOL_RAG", "true", "Retrieve relevant tools per turn", "agent/tool_retrieval.py"),
    ("TOOL_RAG_K", "16", "Tools retrieved per turn", "agent/tool_retrieval.py"),
    ("SWARM_ENABLED", "true", "Multi-agent swarm master switch", "agent/swarm/"),
    ("SWARM_MAX_AGENTS", "5", "Max concurrent swarm agents", "agent/swarm/runner.py"),
    ("SWARM_WORKER_MODE", "sqlite", "inproc|sqlite|redis", "agent/swarm/workers/"),
    ("HEALING_ENABLED", "true", "Self-healing control plane", "agent/healing/"),
    ("HEALING_MAX_RECOVERIES", "4", "Per-turn recovery budget", "agent/healing/orchestrator.py"),
    ("WATCHDOG_MINUTES", "30", "Watchdog cron interval", "scheduler/jobs.py"),
    ("LECE_ENABLED", "true", "LECE cognitive layer", "agent/cognition/"),
    ("LECE_PREPLAY_ENABLED", "true", "Simulate before high-stakes actions", "agent/cognition/preplay.py"),
    ("LECE_DISTILL_TRAIN", "false", "Tier B LoRA training", "agent/cognition/train/"),
]
w("| Variable | Default | Purpose | Used in |")
w("|---|---|---|---|")
for var, default, purpose, used in ENV_VARS:
    w(f"| `{var}` | {default} | {purpose} | `{used}` |")
w()

# ═══════════════════════════════════════════════════════════════════════════════
# EXPANDED APPENDIX E — PER-TOOL INTERVIEW CHEAT SHEET
# ═══════════════════════════════════════════════════════════════════════════════
section("Appendix E: Per-tool interview one-liners", 2)
w("Quick reference: name → one sentence for whiteboard interviews.")
w()
for t in tools:
    gate = " [APPROVAL]" if t.requires_approval else ""
    w(f"- **`{t.name}`**{gate} ({t.category}): {(t.description or '')[:100]}{'...' if len(t.description or '') > 100 else ''}")
w()

# ═══════════════════════════════════════════════════════════════════════════════
# EXPANDED APPENDIX F — TURN TRACE ANNOTATION GUIDE
# ═══════════════════════════════════════════════════════════════════════════════
section("Appendix F: How to read a trace JSONL entry", 2)
TRACE_EVENTS = [
    ("start", "Turn opened with actor and user message", "agent/trace.py trace.start"),
    ("plan", "Planner created steps with plan_id", "agent/planner.py make_plan"),
    ("tool_call", "Tool name, args, policy decision, result preview", "agent/loop.py trace.add_tool_event"),
    ("healing", "Recovery action attempted on failure", "agent/healing/orchestrator.py"),
    ("finish", "Final reply text", "agent/trace.py trace.finish"),
]
for evt, meaning, src in TRACE_EVENTS:
    w(f"### Event: `{evt}`")
    w(f"- **Meaning:** {meaning}")
    w(f"- **Source:** `{src}`")
    w(f"- **Teaching drill:** Find this event in today's trace and explain what happened before/after it.")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# EXPANDED APPENDIX G — SCHEDULER DEEP DIVE
# ═══════════════════════════════════════════════════════════════════════════════
section("Appendix G: Scheduler job deep dive", 2)
for jid, cron, purpose, func in SCHEDULER_JOBS:
    w(f"### `{jid}`")
    w(f"- **Schedule:** {cron}")
    w(f"- **Purpose:** {purpose}")
    w(f"- **Function:** `{func}`")
    w(f"- **Paused when:** AGENT_PAUSED=true (most jobs check _paused())")
    w(f"- **Interview line:** \"{jid} runs on {cron} — {purpose}\"")
    w()

# ═══════════════════════════════════════════════════════════════════════════════
# EXPANDED APPENDIX H — GLOSSARY QUICK RECALL (ALPHABETICAL)
# ═══════════════════════════════════════════════════════════════════════════════
section("Appendix H: Glossary alphabetical quick recall", 2)
for entry in sorted(GLOSSARY, key=lambda e: e[0].lower()):
    term, definition, where, why, example = entry
    w(f"**{term}** — {definition}")
    w(f"  - Code: `{where}` | Why: {why[:80]}{'...' if len(why) > 80 else ''}")
    w()

section("Appendix I: Module walkthrough bullets", 2)
for path, purpose in FILE_PATHS:
    w(f"#### `{path}`")
    w(f"1. Purpose: {purpose}")
    w(f"2. Entry: search for `def` or `class` in {path}")
    w(f"3. Upstream: who imports this module")
    w(f"4. Downstream: what this module calls")
    w(f"5. Interview: one failure mode if this module breaks")
    w(f"6. Test: locate this path in repo and open it while explaining Q-B01")
    w()

section("Appendix J: Tool-by-tool interview rapid fire", 2)
for t in sorted(tools, key=lambda x: x.name):
    w(f"**{t.name}** ({t.category}): {(t.description or 'no description')[:90]} | Approval: {t.requires_approval} | Say: 'I'd use {t.name} when the founder needs {t.category}-class work.'")
    w(f"Follow-up probe: What breaks if {t.name} is removed from registry? → Agent loses capability; Tool-RAG may omit it unless in _CORE.")
    w(f"Whiteboard: draw arrow from execute_loop → registry.call('{t.name}') → {t.category} backend.")
    w(f"Trace check: grep '{t.name}' in latest data/traces/*.jsonl after a live demo.")
    w()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"Wrote {len(lines)} lines to {OUT}")
