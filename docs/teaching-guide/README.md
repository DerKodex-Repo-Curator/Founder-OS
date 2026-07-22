# Founder OS Teaching Guide

This folder contains the complete teaching documentation for explaining Founder OS from basics through advanced agentic architecture — designed for Amazon SDE interview preparation.

## Files

| File | Purpose |
|------|---------|
| [`FOUNDER_OS_COMPLETE_TEACHING_GUIDE.md`](FOUNDER_OS_COMPLETE_TEACHING_GUIDE.md) | **Main document** (~4,100+ lines). Teach from this. |
| [`generate_guide.py`](generate_guide.py) | Regenerator script — re-run after codebase changes to refresh tool counts and descriptions |

## How to teach

1. Start with **Part 0–3** (2 hours): prerequisites, glossary, architecture diagrams
2. Run the bot live during **Part 4** (1 hour): trace `data/traces/*.jsonl` while sending Telegram messages
3. One session per **Part 5–14** (agent, tools, memory, gates, swarm, LECE, healing)
4. Rehearse **Part 18** aloud — Amazon interview crib sheet (Q-B01 through Q-B05)

## Regenerate after code changes

```bash
cd FOUDNER_OS
py docs/teaching-guide/generate_guide.py
```

## Related project docs

- [`../../README.md`](../../README.md) — project source of truth
- [`../LECE.md`](../LECE.md) — LECE whitepaper
- [`../DEPLOY_AWS.md`](../DEPLOY_AWS.md) — AWS deployment notes
