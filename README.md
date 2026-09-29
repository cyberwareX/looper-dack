# looper-duck

Tools for turning a **Looper** NFT (Base mainnet, `0x1649CD37f4748807b4882FC48765bA0B2aFfa94a`)
into a running **[dack](https://github.com/obraztsov/dack-engine) duck** — an autonomous agent whose
on-chain personality *codex* becomes a dack **soul** (prompts, memory, boundaries, capabilities).

Each Looper's identity, personality, and traits live on-chain; this repo reads that codex and composes a
soul that a dack engine can boot and run on Telegram + Buzz.

```
  token id ──► looper_fetch.py ──► personality codex ──► compose_soul.py ──► souls/looper-<id>/
   (chain)      (tokenURI →           (agent_class,        (+ base soul        (a dack soul: SOUL.md,
                 Arweave metadata)      voice, traits…)      template)           prompts, stimuli, config)
```

## What's here

- **`research/looper_fetch.py`** — resolve a token's on-chain `tokenURI` → Arweave metadata → personality
  **codex**. `ALCHEMY_KEY=<key> research/looper_fetch.py <token_id>`.
- **`research/compose_soul.py`** — the composer: codex + a base soul template → a complete dack soul under
  `souls/looper-<id>/` (persona prompts, org/heartbeat/digest duties, Telegram + Buzz rails, an example
  config). Deterministic, no LLM. See [`LOADING.md`](LOADING.md) for the full run.
- **`research/FINDINGS.md`** — how a Looper's identity is laid out on-chain, the codex → soul mapping, and
  the trust/wall model the soul relies on.
- **`research/agentic-skills-design.md`** — design notes for giving a looper plain-text skills + a
  sandboxed `bash` capability (e.g. the Bankr wallet skill), gated behind the engine's Settle state.
- **`research/metadata/*.json`** — example fetched codexes (#370 Creator/Propagandist, #383 CEO/Operator)
  so you can run `compose_soul.py --codex … --meta …` offline without an RPC key.

## Prerequisites

1. **The dack engine** — the runtime that boots and runs the soul (the `dack` CLI + its Docker image, MCP
   servers, and the trust "wall"): <https://github.com/obraztsov/dack-engine>.
2. **A base soul template** — the composer *extends* a base soul (shared prompts/stimuli/memory). Clone the
   public template and point `SOUL_TEMPLATE` at it: <https://github.com/obraztsov/dack-soul>. (If you have a
   sibling `dack-engine` checkout, its `soul-template/` is used by default.)
3. **`ALCHEMY_KEY`** — a Base-mainnet RPC key, to read a Looper's on-chain codex (`.env`, see below). Not
   needed if you compose from a saved `--codex/--meta` JSON.
4. **Optional capability skills** — the [Bankr](https://github.com/BankrBot/skills) wallet skill (for a
   trading/treasury looper) and the Helixa identity skill are **third-party**; clone them from source and
   point `compose_soul.py --skill <dir>` at your local copy. This repo does not redistribute them.

## Quick start

```bash
cp .env.example .env          # then fill in ALCHEMY_KEY, SOUL_TEMPLATE, (optional) BUZZ_RELAY
set -a; . ./.env; set +a

# 1. Read a Looper's on-chain personality codex
research/looper_fetch.py 370 --summary-only

# 2. Compose its dack soul  →  souls/looper-370/
research/compose_soul.py 370

# 3. Run it — fill secrets + config, then boot on the dack engine. See LOADING.md.
```

## Security

The composer's output under **`souls/`** is per-operator **runtime state** — a duck's identity keys, its
filled config (real chat ids / model endpoint / operator DID), and runlog databases (private
conversations). It is **gitignored and must never be committed**. This repo ships only the *tools* and
*example on-chain data*; every real credential stays in your local `.env`, `secrets/`, and `identities/`.
