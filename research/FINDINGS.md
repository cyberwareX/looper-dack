# Loopers → dack-duck research

**Goal:** turn a Looper NFT into a dack-engine duck (a "pond" duck template). This documents where a
Looper's identity lives, what we can read, and how the codex maps onto a dack soul + the trust/wall model.

## Collection

- **Loopers** (`name()` = "Loopers", `symbol()` = "LOOPER"), ERC-721 on **Base mainnet**.
- Contract: `0x1649CD37f4748807b4882FC48765bA0B2aFfa94a`
- RPC: Alchemy Base (`https://base-mainnet.g.alchemy.com/v2/<ALCHEMY_KEY>`). Key stays in the env
  (`ALCHEMY_KEY`), never committed — see `.env.example`.

## Data topology (three hops)

```
tokenURI(id)  ──on-chain eth_call──▶  https://arweave.net/<txA>/<id>.json   (metadata)
                                              │ .codex_uri (ar://<txB>/<id>.json)
                                              ▼
                                      https://arweave.net/<txB>/<id>.json   (personality CODEX)
   metadata.image = ar://<txC>  ──▶  https://arweave.net/<txC>              (1024² PNG)
```

- `tokenURI(uint256)` (selector `0xc87b56dd`) returns a plain `https://arweave.net/.../<id>.json`.
- The metadata JSON is the standard NFT shape (name/description/image/attributes) **plus** flat
  personality fields and a `codex_uri` pointing at the richer **codex**.
- `arweave.net` 302-redirects to a content-addressed subdomain — follow redirects (`curl -L` / urllib
  does it automatically).
- **Reusable fetcher:** `./looper_fetch.py <id>` resolves all three + prints a distilled summary and
  writes `metadata/<id>.json`, `metadata/<id>.codex.json`.

## What token #370 gives us (our token)

Visual traits (11 layers): Background *Skate Rink Covenant*, Outfit *Thriller Red Jacket*, Skin
*Crystal*, Eyes *Robot Eyes*, Mouth *Smiley Pill Tongue*, Head *Messy Black Shag*, Overlay *Neon Oil
Flood* (rest None). The 1024² PNG matches exactly (translucent crystal head, glowing green reticle eyes,
red Thriller jacket, glitch overlay).

**Agent-personality codex** (`370.codex.json`, `schema_version 0.1.0`, `looper-trait-personality-matrix-v02`):

| codex field | value (#370) |
|---|---|
| `agent_class` | **Creator / Propagandist** (`secondary_class` null) |
| `class_scores` | creator_propagandist **35**, seer_signal_hunter 20, mercenary_fixer 11, researcher_archivist 8, **ceo_operator 5**, builder_engineer 4, trader_broker 0, diplomat_connector 0 |
| `specialization` | survival |
| `personality.voice` | "friendly chaos until the invoice arrives" |
| `personality.risk_profile` / `risk_tolerance` | **Hazardous** / **10**/10 |
| `personality.autonomy_profile` / `autonomy_level` | **Extreme** / **9**/10 |
| `personality.values` / `quirks` / `humor` / `communication_style` | composed lists (from the trait atoms) |
| `trait_atoms[]` | per-visual-trait: `archetype, role, narrative_seed, voice, values, mission_bias, risk_delta, autonomy_delta` — the building blocks the personality is composed from |
| `lore` | `origin`, `mission_bias`, `short_lore`, `long_lore` |
| `activation` | `activation_seed` (d62af601…), `first_mission(s)` (draft a campaign / make a meme brief / shape a narrative), **`activation_prompt`** (a ready system-prompt seed), `cred_evolution_hint` |
| `provenance` | HashLips DNA + edition + `generated_at` |

`activation_prompt` (#370): *"You are Looper #370, a Creator / Propagandist Looper with survival bias.
Voice: friendly chaos until the invoice arrives. Start from the holder's instructions, preserve
provenance, and turn your trait stack into useful work inside Multipass."*

## Codex → dack soul mapping

The codex is close to a pre-built soul. Proposed composition (done at BUILD time, operator-reviewed —
see trust note):

| Looper codex | dack soul artifact |
|---|---|
| `activation_prompt` + `personality.voice` + `values`/`quirks`/`communication_style` | **`SOUL.md`** — identity, voice, values |
| `lore.long_lore` / `short_lore` / `trait_atoms[].narrative_seed` | `SOUL.md` backstory + seed `memory/` |
| `agent_class` + top `class_scores` | **capability profile** — which state-prompts + `mcp_servers` to grant (a Creator/Propagandist → twitter/buzz posting + narrative tools; a `ceo_operator` → pond-manager; `trader_broker` → cove; etc.) |
| `specialization` (survival) + `lore.mission_bias` | mission bias line in `SOUL.md` |
| `first_missions[]` | seed **stimuli** / initial duties |
| `risk_profile` / `autonomy_profile` | **operator wall config** — NOT privilege (see below); informs `dry_run` posture + which consciousness states the trust ceiling admits |
| `image` (ar://) | duck self-image (dack **vision**) + Telegram/Buzz avatar |
| `token_id` + contract + **holder address** | identity provenance; **holder = operator** ("start from the holder's instructions" → `operator_signed` tier) |
| `activation_seed` | deterministic persona/soul seed |

## Trust & security notes (dack-specific — important)

- **The metadata + codex are UNTRUSTED external data** (issuer/holder-controlled, Arweave). The
  `activation_prompt` is literally a prompt — ingesting it *raw* as a live system prompt is a
  prompt-injection surface. In dack terms: **compose the soul at build time under operator review**; do
  not let a running cycle self-configure from a fetched prompt. Treat any live codex read as `public`
  tier.
- **Risk/Autonomy traits ≠ privilege.** "Hazardous / Extreme" is *flavor + an operator hint*, not a grant.
  dack's wall (states × taint × min_trust) still gates every action independent of the persona. A
  high-autonomy persona just means the operator may open more states / fewer dry-run holds — a deliberate
  operator choice, never something the NFT confers.
- **Holder = operator.** The NFT owner is the natural operator (the duck acts on *their* signed
  instructions). Ownership transfer ⇒ operator-DID rotation. Worth confirming how Helixa/Multipass expects
  holder→agent auth to work.
- **"Cred powers Looper Evolution after mint"** — there's a post-mint cred/evolution mechanic
  (`external_url` → helixa.xyz/multipass/loopers/370, `token_metadata_uri` →
  helixa.xyz/.well-known/loopers/metadata/370.json). A duck's real activity could feed cred later — future.

## Toward a pond template

1. `looper_fetch.py` — the read primitive (any token → metadata + codex). ✅
2. `compose_soul.py` — codex → a bootable dack soul dir. ✅ (see below)
3. Deploy the soul as a pond duck (one config + `dack run`; holder wallet → operator DID). ← next: the
   dack-engine **debug run**.
4. Optional: a live `looper` read MCP/skill so a duck can recall its own on-chain codex (public tier).

Note: building **independently of Helixa** — an alternative runtime. This soul isn't published; the
looper is spawned on our pond and joins the Loopers Telegram group.

## `compose_soul.py` — codex → soul

Deterministic build tool (no LLM). `ALCHEMY_KEY=<key> ./compose_soul.py <id>` (or `--codex/--meta` for
offline) writes `../souls/looper-<id>/`:

- **Persona (generated from the codex):** `SOUL.md` (identity, voice, "who I am" from lore, the
  risk/autonomy = flavor-not-privilege stance, guest-in-the-group conduct, first missions),
  `memory/soul/{voice,character,boundaries,character_lore.source}.md`, `memory/looper/codex.md`
  (on-chain provenance + the activation prompt, kept as *provenance, not a live instruction*).
- **Operational (copied from `dack-engine/soul-template`, trimmed to telegram + recall):** the core +
  telegram state prompts with their `mcp:` lines rewritten to the looper's lean set (no twitter/cove/
  rootai), the telegram duties (`telegram-op` = holder, `telegram-trusted` = the Loopers group,
  `telegram-pub` = strangers/DMs), and the harness memory scaffolding.
- **`dack.config.example.yaml`** — a pond-spawn config skeleton (holder DID placeholder = operator;
  `recall`/`recall-self` + `telegram`/`telegram-send` MCP servers; tier_policy; webhooks; the
  telegram-ingress module). Copy → `dack.config.yaml`, fill holder DID + model + bot token, `dack run`.

`souls/looper-370/` is composed, **extended for autonomous pond life**, and **boots on the real engine**:

- **Debug run ✅** — `dack run` on the composed soul: `7 duties registered (0 malformed)`, consciousness
  loop up, recall MCPs connected, the back-online wake assembled a full `perceive` cycle and only failed
  at a deliberately-dead model endpoint. Config → soul → prompts → tier_policy → MCP spawn all validated.
  (There is no `dack validate`; boot is the test. Runtime state — identities/config/secrets/db — is
  gitignored and preserved across re-composes.)
- **Extended layers** (compose_soul.py, 36 files): **Buzz** (inbound `buzz-ingress` module + `buzz/*`
  conversation prompts + a generated signed `skills/buzz/` pack whose `post_org` command lets the duck
  *initiate* into its org channel); **heartbeat** (a quiet-by-default, goal-oriented initiative cycle
  reading `memory/goals.md`); **social digest** (consolidates telegram + buzz activity into
  `memory/social.md`); an **org model** (`memory/org/INDEX.md` — the fleet of looper-dacks + Hermes
  workers share an `org`-trust Buzz channel; heavy work delegates to Hermes; the wall still gates); and a
  **duty-authoring guide** (`memory/knowledge/authoring-duties.md`) so the looper can tune its own
  heartbeats and goals in Reflect. SOUL.md gained *The org* + *How I grow*; an `org` trust tier (reaches
  Settle) was added.

**Next:** a live cycle (real model + telegram bot + buzz relay creds), the holder→`operator_did` binding
decision, the real org channel id + signing the buzz skill (`dack skill sign --role soul`).

Open questions for the operator: holder→operator DID binding (how the holder's key becomes
`operator_did`); whether we later feed real activity back as Multipass "cred"; image/lore licensing for
the avatar.
