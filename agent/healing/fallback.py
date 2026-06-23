"""Tool/provider fallback chains and substitution."""
import logging

from agent import registry

logger = logging.getLogger(__name__)

# Tool equivalence groups — first available tool in group wins on substitution.
_TOOL_GROUPS = {
    "web_search": ["web_search", "research_company"],
    "scrape": ["scrape_url", "browse_page"],
    "memory_recall": ["search_memory", "deep_recall", "smart_recall"],
    "crm_lookup": ["search_contacts", "pipeline_status", "get_followups"],
}

# Directed substitutions: failed_tool -> [alternatives in priority order]
_SUBSTITUTIONS = {
    "web_search": ["scrape_url"],
    "scrape_url": ["web_search", "browse_page"],
    "browse_page": ["scrape_url", "web_search"],
    "research_company": ["web_search"],
    "tavily_search": ["web_search"],
    "find_leads": ["web_search", "research_company"],
    "deep_recall": ["search_memory", "smart_recall"],
    "search_memory": ["deep_recall"],
    "smart_recall": ["deep_recall", "search_memory"],
    "graph_lookup": ["smart_recall", "deep_recall"],
    "ask_documents": ["search_memory", "web_search"],
    "ask_network": ["smart_recall", "graph_lookup"],
}


def substitute_tool(failed_name: str) -> str:
    """Return an alternative tool name, or empty string if none."""
    alts = _SUBSTITUTIONS.get(failed_name, [])
    registered = {t.name for t in registry.all_tools()}
    for alt in alts:
        if alt in registered and alt != failed_name:
            return alt
    # Try group fallback
    for group_name, members in _TOOL_GROUPS.items():
        if failed_name in members:
            for m in members:
                if m in registered and m != failed_name:
                    return m
    return ""


def provider_chain_excluding(failed_provider: str) -> list:
    """Return remaining LLM providers after excluding a failed one."""
    from config import config
    chain = []
    if config.groq_api_key and failed_provider != "groq":
        chain.append("groq")
    if config.gemini_api_key and failed_provider != "gemini":
        chain.append("gemini")
    if config.openai_api_key and failed_provider != "openai":
        chain.append("openai")
    if config.ollama_enabled and failed_provider != "ollama":
        chain.append("ollama")
    return chain
