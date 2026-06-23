import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    telegram_bot_token: str
    groq_api_key: str
    gemini_api_key: str
    openai_api_key: str
    gmail_address: str
    gmail_app_password: str
    my_telegram_user_id: int
    public_access: bool          # if true, ANY Telegram user can use the bot
    serper_api_key: str
    tavily_api_key: str
    my_name: str
    company_name: str
    my_role: str
    my_one_liner: str
    # Autonomy / agent
    auto_approve: bool
    heartbeat_hours: int
    autonomy_level: str          # cautious | balanced | autonomous
    voice_replies: bool          # speak responses back to voice messages
    dashboard_enabled: bool      # serve the local web dashboard
    dashboard_port: int
    dashboard_api_port: int
    web_origin: str              # CORS origins for React dashboard (comma-separated)
    daily_llm_call_cap: int      # 0 = unlimited
    agent_paused: bool           # kill switch

    # Local model (Ollama) + caching
    ollama_enabled: bool
    ollama_base_url: str
    ollama_model: str
    semantic_cache: bool
    cache_distance_threshold: float
    # Tool-RAG: retrieve only the most relevant tools per turn instead of all of them
    tool_rag: bool
    tool_rag_k: int
    # Vector store backend: "chroma" (local, default) or "qdrant" (managed/remote)
    vector_backend: str
    qdrant_url: str
    qdrant_api_key: str
    # Google Calendar (optional)
    google_credentials_path: str
    google_token_path: str
    # X / Twitter (optional)
    x_api_key: str
    x_api_secret: str
    x_access_token: str
    x_access_token_secret: str
    x_bearer_token: str
    # Agent swarm
    swarm_enabled: bool
    swarm_max_agents: int
    swarm_max_rounds: int
    swarm_max_handoffs: int
    debate_rounds: int
    swarm_worker_mode: str       # inproc | sqlite | redis
    redis_url: str
    langgraph_adapter: bool
    # Self-healing
    healing_enabled: bool
    healing_max_recoveries: int
    healing_retry_max: int
    healing_backoff_base_ms: int
    circuit_fail_threshold: int
    circuit_cooldown_s: int
    healing_metacog: bool
    healing_auto_replan: bool
    healing_escalate: bool
    watchdog_enabled: bool
    watchdog_minutes: int
    # Lived-Experience Cognitive Engine (LECE)
    lece_enabled: bool
    lece_distill_enabled: bool
    lece_distill_hour: int
    lece_distill_train: bool
    lece_train_backend: str
    lece_principles_k: int
    lece_preplay_enabled: bool
    lece_preplay_mode: str          # learned | swarm | hybrid
    lece_preplay_branches: int
    lece_workspace_continuous: bool
    lece_workspace_tick_s: int
    lece_adaptive_autonomy: bool
    lece_trust_min_trials: int

def load_config() -> Config:
    missing = []
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        missing.append("TELEGRAM_BOT_TOKEN")
    if not os.getenv("MY_TELEGRAM_USER_ID"):
        missing.append("MY_TELEGRAM_USER_ID")

    # At least one LLM provider key is required. Any one is enough — the router
    # falls back across whatever is configured (Groq -> Gemini -> OpenAI).
    llm_keys = [
        os.getenv("GROQ_API_KEY"),
        os.getenv("GOOGLE_GEMINI_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
    ]
    if not any(llm_keys):
        missing.append("at least one of GROQ_API_KEY / GOOGLE_GEMINI_API_KEY / OPENAI_API_KEY")

    if missing:
        print(f"[FATAL] Missing required env vars: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in the required values.")
        exit(1)

    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        gmail_address=os.getenv("GMAIL_ADDRESS", ""),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
        my_telegram_user_id=int(os.getenv("MY_TELEGRAM_USER_ID", "0")),
        public_access=os.getenv("PUBLIC_ACCESS", "false").strip().lower() in ("1", "true", "yes", "on"),
        serper_api_key=os.getenv("SERPER_API_KEY", ""),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        my_name=os.getenv("MY_NAME", "Founder"),
        company_name=os.getenv("MY_COMPANY_NAME", "My Company"),
        my_role=os.getenv("MY_ROLE", "Founder"),
        my_one_liner=os.getenv("MY_ONE_LINER", ""),
        auto_approve=os.getenv("AUTO_APPROVE", "false").strip().lower() in ("1", "true", "yes", "on"),
        heartbeat_hours=int(os.getenv("HEARTBEAT_HOURS", "4") or "4"),
        autonomy_level=os.getenv("AUTONOMY_LEVEL", "balanced").strip().lower(),
        voice_replies=os.getenv("VOICE_REPLIES", "true").strip().lower() in ("1", "true", "yes", "on"),
        dashboard_enabled=os.getenv("DASHBOARD_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"),
        dashboard_port=int(os.getenv("DASHBOARD_PORT", "8787") or "8787"),
        dashboard_api_port=int(os.getenv("DASHBOARD_API_PORT", "8788") or "8788"),
        web_origin=os.getenv("WEB_ORIGIN", "http://localhost:3000").strip(),
        daily_llm_call_cap=int(os.getenv("DAILY_LLM_CALL_CAP", "0") or "0"),
        agent_paused=os.getenv("AGENT_PAUSED", "false").strip().lower() in ("1", "true", "yes", "on"),
        ollama_enabled=os.getenv("OLLAMA_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1").strip(),
        semantic_cache=os.getenv("SEMANTIC_CACHE", "true").strip().lower() in ("1", "true", "yes", "on"),
        cache_distance_threshold=float(os.getenv("CACHE_DISTANCE_THRESHOLD", "0.08") or "0.08"),
        tool_rag=os.getenv("TOOL_RAG", "true").strip().lower() in ("1", "true", "yes", "on"),
        tool_rag_k=int(os.getenv("TOOL_RAG_K", "16") or "16"),
        vector_backend=os.getenv("VECTOR_BACKEND", "chroma").strip().lower(),
        qdrant_url=os.getenv("QDRANT_URL", "").strip(),
        qdrant_api_key=os.getenv("QDRANT_API_KEY", "").strip(),
        google_credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "./data/google_credentials.json"),
        google_token_path=os.getenv("GOOGLE_TOKEN_PATH", "./data/google_token.json"),
        x_api_key=os.getenv("X_API_KEY", ""),
        x_api_secret=os.getenv("X_API_SECRET", ""),
        x_access_token=os.getenv("X_ACCESS_TOKEN", ""),
        x_access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", ""),
        x_bearer_token=os.getenv("X_BEARER_TOKEN", ""),
        swarm_enabled=os.getenv("SWARM_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"),
        swarm_max_agents=int(os.getenv("SWARM_MAX_AGENTS", "5") or "5"),
        swarm_max_rounds=int(os.getenv("SWARM_MAX_ROUNDS", "10") or "10"),
        swarm_max_handoffs=int(os.getenv("SWARM_MAX_HANDOFFS", "5") or "5"),
        debate_rounds=int(os.getenv("DEBATE_ROUNDS", "2") or "2"),
        swarm_worker_mode=os.getenv("SWARM_WORKER_MODE", "sqlite").strip().lower(),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0").strip(),
        langgraph_adapter=os.getenv("LANGGRAPH_ADAPTER", "false").strip().lower() in ("1", "true", "yes", "on"),
        healing_enabled=os.getenv("HEALING_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"),
        healing_max_recoveries=int(os.getenv("HEALING_MAX_RECOVERIES", "4") or "4"),
        healing_retry_max=int(os.getenv("HEALING_RETRY_MAX", "3") or "3"),
        healing_backoff_base_ms=int(os.getenv("HEALING_BACKOFF_BASE_MS", "200") or "200"),
        circuit_fail_threshold=int(os.getenv("CIRCUIT_FAIL_THRESHOLD", "5") or "5"),
        circuit_cooldown_s=int(os.getenv("CIRCUIT_COOLDOWN_S", "30") or "30"),
        healing_metacog=os.getenv("HEALING_METACOG", "true").strip().lower() in ("1", "true", "yes", "on"),
        healing_auto_replan=os.getenv("HEALING_AUTO_REPLAN", "true").strip().lower() in ("1", "true", "yes", "on"),
        healing_escalate=os.getenv("HEALING_ESCALATE", "true").strip().lower() in ("1", "true", "yes", "on"),
        watchdog_enabled=os.getenv("WATCHDOG_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"),
        watchdog_minutes=int(os.getenv("WATCHDOG_MINUTES", "30") or "30"),
        lece_enabled=os.getenv("LECE_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"),
        lece_distill_enabled=os.getenv("LECE_DISTILL_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"),
        lece_distill_hour=int(os.getenv("LECE_DISTILL_HOUR", "3") or "3"),
        lece_distill_train=os.getenv("LECE_DISTILL_TRAIN", "false").strip().lower() in ("1", "true", "yes", "on"),
        lece_train_backend=os.getenv("LECE_TRAIN_BACKEND", "peft").strip().lower(),
        lece_principles_k=int(os.getenv("LECE_PRINCIPLES_K", "4") or "4"),
        lece_preplay_enabled=os.getenv("LECE_PREPLAY_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"),
        lece_preplay_mode=os.getenv("LECE_PREPLAY_MODE", "hybrid").strip().lower(),
        lece_preplay_branches=int(os.getenv("LECE_PREPLAY_BRANCHES", "3") or "3"),
        lece_workspace_continuous=os.getenv("LECE_WORKSPACE_CONTINUOUS", "false").strip().lower() in ("1", "true", "yes", "on"),
        lece_workspace_tick_s=int(os.getenv("LECE_WORKSPACE_TICK_S", "120") or "120"),
        lece_adaptive_autonomy=os.getenv("LECE_ADAPTIVE_AUTONOMY", "true").strip().lower() in ("1", "true", "yes", "on"),
        lece_trust_min_trials=int(os.getenv("LECE_TRUST_MIN_TRIALS", "5") or "5"),
    )

config = load_config()
