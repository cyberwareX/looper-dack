# Agentic skills — plain-text skills + bash-in-Settle + skill-nav + webfetch

**Epoch scope (operator request):** give loopers more agentic capability — load **plain-text skills**
(Claude/Hermes `SKILL.md` format) and run operator-installed **system-wide CLI tools**. Concretely: our
agent must be able to use (some of) the **Bankr skills directory** — the *core `bankr` skill is a must*
(https://github.com/BankrBot/skills/tree/main/bankr) — the credential that makes people take our agents
seriously.

Status: **research + design.** Two source investigations in flight (OpenClaude port candidates; dack wall
change-surface). This doc grounds the target + the security model + the proposed architecture; the
port-vs-build specifics and the exact change list land when that research returns.

---

## 1. What a Bankr/Hermes skill actually is (grounded)

The Bankr repo is the **Claude/Anthropic "Agent Skills"** format (a root `.claude/`; content attributed to
`NousResearch/hermes-agent`). Each skill is a directory:

```
bankr/
  SKILL.md          # YAML frontmatter + markdown prose (the bankr core SKILL.md is 105 KB)
  catalog.json      # install/setup/demo metadata
  references/*.md   # deep-dive docs, loaded on demand (progressive disclosure): safety.md (28 KB),
                    # token-deployment.md (40 KB), llm-gateway.md (37 KB), api-workflow.md, …
```

`SKILL.md` frontmatter (the contract that matters):

```yaml
name: bankr
description: AI-powered crypto trading agent, wallet API, and LLM gateway via natural language. Use when…
metadata:
  clawdbot:
    requires: { bins: ["bankr"] }     # ← the CLI binary the skill needs (operator installs it)
```

**Execution model:** the operator installs the CLI (`npm i -g @bankr/cli` / `bun install -g @bankr/cli`)
and runs a one-time `bankr login` (which provisions a wallet + a `bk_…` API key and **accepts Bankr's ToS
on the user's behalf** — so onboarding is the *operator's* act, never the duck's). Thereafter the agent
**reads the prose + references and executes via bash**: `bankr agent prompt "Buy $50 of ETH"`,
`bankr fees claim …`, or `curl https://api.bankr.bot/...` (x402-paid). Many other skills in the directory
are the same shape (curl to x402 HTTP endpoints, or a native MCP).

⇒ Running these needs three things dack doesn't expose today: **bash**, **web fetch**, and a way to
**read/navigate the SKILL.md + references**.

## 2. Security model — why bash-in-Settle fits (and defense in depth)

The operator's insight, which the code supports: **bash is irreversible → it belongs in Settle**, the
state dack already reserves for irreversible authority. That gives us three independent gates:

1. **dack wall — WHEN bash may run.** Classify `Bash` as `SettleTx`; admit it only when
   `allow_bash_in_settle` is on (config, **default OFF**) AND the cycle is in **Settle** AND its trust
   ceiling reaches settle. A `public`-tainted cycle (read a stranger's tweet / an untrusted doc) has
   already dropped below settle and **physically cannot reach bash** — the taint lattice does this for
   free, no rule to write. This is the whole point of the consciousness ladder.
2. **Scoped credentials — WHAT bash sees.** The `bk_…` key (and any skill secret) is injected into the
   bash process env only for the skill being run, via the existing `scope_env`/secret-broker path — never
   the model context.
3. **Bankr server-side guardrails — WHAT the key can do.** From `references/safety.md`: an unconfigured
   wallet still enforces **$500/tx + $500/day**, plus permitted-recipient allowlists and an
   arbitrary-contract-call gate — and **an API key cannot raise its own limits** (that needs web/passkey
   auth). So even a misbehaving Settle cycle is capped by Bankr itself.

Plus the existing dack protections still hold: the per-cycle **tripwire** reverts any edit to protected
soul files; **dry_run** can block `Bash` for testing; and on the pond the duck runs **in a Docker
container**, so "bash" is already OS-isolated to that container (the natural FS-confinement answer).

**Capability layering by state (the operator's framing):**

| State | Capability | Why |
|---|---|---|
| Perceive / Express | **Protected CLI = signed executable skills** (existing `RunSkillCommand`, fixed argv, tier-gated) | reversible, safe for DAC ops / buzz / telegram; no free shell |
| any state | **skill navigation** (read/list SKILL.md + references) + **webfetch** | reading prose / fetching a URL doesn't *act* → read-tier (webfetch taints `public`) |
| **Settle only** | **plain bash** (default-off) → runs plain-text skills needing arbitrary CLI/curl | irreversible → Settle; only a clean, high-trust cycle reaches it |

## 3. Proposed components

1. **Bash tool, Settle-gated, default-off.** `config.allow_bash_in_settle: bool`. Wall classifies `Bash`
   → `SettleTx`; admit iff flag ∧ state=Settle ∧ ceiling≥settle. Execute via the bridge (sandboxed —
   reuse OpenClaude's command sandbox if present; else bubblewrap on Linux / container on the pond).
   Optional `bash_allowed_bins` allowlist so only vetted CLIs (`bankr`, `curl`, …) are callable.
2. **Plain-text (`SKILL.md`) skills** — a skill *type* distinct from the signed executable pack: frontmatter
   (`name`/`description`/`requires.bins`) + body + `references/`. Operator-curated, lives in the soul
   (tripwire-protected). Surfaced in orientation as a catalogue (name+description); body/references read
   on demand. `requires.bins` declares CLIs; the operator installs them; config gates which bins are
   allowed.
3. **Skill-navigation capability** (read-tier, all states) — list skills, read a skill's SKILL.md, read a
   reference file. *Port from OpenClaude if it has one (pending research), else a small MCP.*
4. **WebFetch capability** (read-tier, `trust: public`) — URL → markdown, size/time caps, SSRF/host guard.
   *Port from OpenClaude if present (pending research), else a small MCP.*

## 4. Open questions (for the operator)

- **FS confinement for bash.** Container-only (pond ducks already run in Docker) is the cheap answer; do we
  also want a per-run workspace dir + a bind-mount discipline, or reuse the worker Docker-isolation path?
- **Prose-skill trust.** Operator-curated-in-soul (tripwire-protected) is probably enough — the real gate
  is "can this cycle run bash", not per-skill signing. Do we still want to *sign* SKILL.md skills (extend
  the execute-gate) or trust them as soul content?
- **Bin allowlist.** Start with an explicit `bash_allowed_bins` (bankr, curl, jq, …), or allow-all-in-
  Settle and rely on the state gate? (Allowlist is safer + still lets the operator add bins.)
- **Onboarding.** `bankr login` (ToS acceptance, wallet provisioning) is an operator action; the duck only
  ever uses a pre-provisioned scoped key. Confirm that division.

## 5. dack change surface (from source research)

The wall plumbing **already anticipates this**. `ToolClass` (`src/state/mod.rs:47-77`) already has `Shell`
and `Net`. `classify.rs:90` maps `Bash|BashOutput|KillShell|PowerShell|REPL → Shell`; `WebFetch|WebSearch
→ Net`. The single state gate is `action_required.rs:333` (`spec.tool_scope.allows(class)`). The **trust
ceiling is already enforced upstream** — the harness only routes an *uncontaminated* cycle into Settle
(`harness/mod.rs:447,569`), so "reaches settle" is free; inside Settle the wall admits `SettleTx`
unconditionally.

**Bash is blocked today by two layers:** (a) `Shell` is in no consciousness-state scope (only
`worker_spec`); (b) an SDK-boundary strip — `ALWAYS_DISALLOWED=["Bash","PowerShell","REPL","KillShell"]`
(`openclaude.rs:40`) removes it from `disallowedTools` for every non-worker spec, so the model never even
sees it. Executable skills are `execve` of a fixed argv — **not** a shell.

**Minimal wall change for `allow_bash_in_settle` (default-false):**
1. `config/mod.rs` — add `#[serde(default)] pub allow_bash_in_settle: bool` (by `dry_run`/`protected_memory_paths`).
2. `harness/mod.rs` `wall_for()` (~1316) — when the flag is on and `spec.state==Settle`, override the
   Settle `tool_scope` to admit the shell class (colocated with the existing `long_term_writable`/
   `dry_run_block` wiring). Do **not** add `Shell` to `default_spec` globally.
3. `openclaude.rs` `disallowed_for()` (52-77) — stop stripping `Bash` for Settle-with-flag. **Caveat:**
   `is_worker` is derived from `tool_scope.allows(Shell)`; a dedicated flag check avoids Settle being
   mistaken for a worker (which would drop its `TodoWrite`/`snip` strips).
4. Update the invariant tests that hardcode "bash denied everywhere" (`state/mod.rs:256`,
   `openclaude.rs:517`, `action_required.rs:600,625`).

**Prose SKILL.md navigation already works** — `self_orientation()`/`skills_catalogue()`
(`harness/mod.rs:1887-1927`) surface a one-line **name — description** catalogue (frontmatter only) at
fresh wake and tell the model to `Read skills/<name>/SKILL.md`; the body + `references/` are loaded by the
model's **builtin `Read`** (a `Read`-class tool allowed in every state). So the "view/navigate plain-text
skills" ask is *mostly already there*; a small **skill-nav MCP** (list skills, list a skill's references,
maybe search) would be a nicety, not a requirement.

**WebFetch** classifies as `Net`, and `Net` is already in **Perceive**'s scope — so it's architecturally
permitted today. The only questions are whether the SDK exposes a WebFetch tool and whether we want it as
a builtin (via un-stripping) or as our own MCP (SSRF guard, host allowlist). → pending the OpenClaude research.

## 6. ⚠️ The real constraint: FS confinement for bash

The wall toggle is easy; **safe bash is not.** `Bash` classifies as `Shell` with no target path, so it
**bypasses** the `FileWrite` path-gate (`writable_dirs`, `is_protected_write`, `long_term_writable` — all
wall-FileWrite-only). And **the duck process is never containerized** (only workers are). Consequences of a
naive bash-in-Settle:

- It can **read `identities/` (the soul signing key!), `secrets/`, `dack.config.yaml`** — the crown jewels
  — and exfiltrate them over the network it also has.
- It can **write anywhere**: in-soul writes (`SOUL.md`, `memory/INDEX.md`, `prompts/`) survive for the rest
  of the cycle and are only reverted *post-hoc* by the git tripwire (`harness/mod.rs:1228-1281`); writes
  **outside** the soul repo are never reverted at all.

So bash-in-Settle **requires an OS sandbox**, not just a wall flag. The design must run the Settle shell in
a confined environment that exposes **only** a scratch workspace + the *one* skill's scoped secret, and
**hides** `identities/`, `secrets/`, the config, and the rest of the FS. Reuse candidates:
- the **worker Docker-isolation** path (`runtime.worker_sandbox`, `Dockerfile.worker`) — already built for
  exactly "run untrusted stuff in a locked box"; point a Settle-bash at it with a minimal bind-mount; **or**
- OpenClaude's own **command sandbox** (bubblewrap/`bwrap` + `socat`, already in the Docker image per
  `docs/deployment.md`) if it can be configured to a workspace + drop the secret dirs — pending the
  OpenClaude research (Agent 1).

**This reframes the epoch:** the flagged wall change is P1; the **sandbox** is the load-bearing P0 that
makes it safe. Ship bash-in-Settle *only* behind the sandbox.

### 6a. VPS reality check (2026-09-24) — bwrap needs `--privileged`; pivot to user-drop

Built `mcp/sandbox.ts` (bubblewrap; **10/10 confinement proven** in a Linux container: soul-key/secrets/
config unreadable, workspace-only writable, env cleared+scoped) + `preflightSandbox()` (fail-closed). But
testing the real deployment on the VPS (`dack/duck:latest`, matching the **live duck's default posture** —
`Privileged=false SecurityOpt=[]`) showed **bwrap does NOT work in the duck container** without full
`--privileged`:

| posture | result |
|---|---|
| default (== live duck) | `unshare(CLONE_NEWUSER)` blocked by Docker seccomp |
| `seccomp=unconfined` | userns OK → `Failed to make / slave: Permission denied` |
| `+ SYS_ADMIN`, `+ apparmor=unconfined` | → `Can't mount proc on /newroot/proc: Operation not permitted` |
| **`--privileged`** | ✅ fully confines |

`--privileged` is **rejected** (a privileged container is a host-escape surface — worse than the bash it
sandboxes). The **sibling-container** path is also unavailable: the duck has **no docker socket and no
docker CLI** (and a socket = root-on-host anyway). Host userns *is* enabled
(`unprivileged_userns_clone=1`); Docker's seccomp/apparmor + masked-`/proc` are what block it.

**Viable in the default container: user-drop.** The duck runs as **root**; `setpriv --reuid 65534
--regid 65534 --clear-groups` (drop to `nobody`) is available, and a **root:600** file is unreadable by
`nobody` (verified on the VPS). So bash-as-nobody, with the crown jewels kept **root:600/700**, covers the
core threats **with zero privilege change**:

- soul signing key / secrets / config / other skills' keys — **root:600 → unreadable** ✓
- soul writes — the soul repo is **root-owned → nobody can't write it** (stronger than the post-hoc
  tripwire) ✓
- `/proc/<duck>/environ` leak — proc `environ` is `0400` owned by root → **nobody can't read it** ✓
- clean env — we spawn bash with `--clearenv`-equivalent + only the scoped secret ✓

Weaker than bwrap (no mount namespace → world-readable files are visible; `/tmp` writable; **no egress
control**). But it protects exactly what matters (the key material) and ships in the unprivileged prod
container. Egress control becomes a hardening follow-up (an allow-list proxy).

**Recommendation — a fail-closed hybrid.** `preflightSandbox()` picks the strongest available:
**bwrap** if it actually runs (a privileged/opt-in high-value duck, or a future dedicated sandbox
container) → else **user-drop** *iff* the crown-jewel paths verify as non-readable by the sandbox uid
→ else **REFUSE** (never unconfined). Baseline prod = user-drop; the bwrap module stays for the strong tier.

### 6b. RESOLVED — bwrap under Kata (the pond already runs it) ✅

The pond runs each agent under a per-template **`runtime_class: runc | kata`**. Kata = a lightweight **VM
with its own guest kernel**, so a "privileged" workload is contained by the *hypervisor*, not the host —
the pond already translates `privileged: true` under Kata into **cap ALL + apparmor/seccomp=unconfined**
(real `--privileged` breaks Kata's device passthrough), and the **`buzz` template already runs a
privileged DinD stack** this way on the VPS. The box has `/dev/kvm` + the `kata`/`kata-clh` runtimes live.

**Verified on the VPS (`dack/duck:latest` under `--runtime kata`):** bwrap's proc-mount — the one thing
that failed everywhere on runc short of full `--privileged` — **succeeds under Kata** once we add
**`--security-opt systempaths=unconfined`** (clears Docker's masked `/proc` paths so bwrap can mount a
fresh procfs). Result: `BWRAP_OK_PROC_MOUNTED` · workspace writable · system read-only. `systempaths=
unconfined` is unsafe on runc (exposes the host kernel's `/proc`) but **safe under Kata** — there is no
host kernel in the guest; it's a disposable VM.

So the design is the **strong** one after all, no user-drop compromise:

> **Bash-enabled ducks ship as a custom pond template with `runtime_class: kata` + `privileged: true`.**
> Inside the Kata VM, `mcp/sandbox.ts` (bwrap) gives full FS confinement (soul key / secrets / config
> hidden, workspace-only, env cleared+scoped); the **VM is the outer boundary** so even the cap-ALL
> container can't reach the host. Layers: Kata VM → bwrap → wall (Settle-only, default-off, clean-cycle-
> only) → scoped key → Bankr server caps.

**One small pond change required:** add `systempaths=unconfined` to the Kata branch of
`privileged_for_runtime` (`dack-pond/src/agents.rs:~1865`) — either always (safe under Kata) or behind a
template flag (e.g. `needs_userns_sandbox: true`). Without it, bwrap's proc-mount fails inside the VM.

The user-drop hybrid (§6a) stays as the **fallback** for a non-Kata / runc deployment, but the Kata path
is the recommended prod posture for bash-ducks.

## 7. OpenClaude port findings

All three capabilities are already compiled into the vendored `sdk.mjs`; "porting" = enable + gate, not
reimplement.

- **WebFetch / WebSearch — PORT: yes (enable + gate).** `WebFetchTool` with a real **SSRF guard**
  (`ssrfGuard.ts` blocks 10/8, 169.254, metadata ranges, IPv6 ULA, creds-in-URL), per-host permission
  model, `turndown` HTML→markdown, 10 MB / 60 s / 100k-char caps, same-origin-only auto-redirect. Live by
  default; suppressed via `disallowedTools`; every call already passes the wall (`canUseTool`). WebSearch
  is provider-pluggable (needs a provider key). Caveat: WebFetch runs a post-fetch summarization via the
  SDK's small model → over our bridge it degrades to raw markdown on error (safe).
- **Skills nav — DO NOT port OpenClaude's `Skill` tool.** Its non-MCP loader runs inline `` !`…` `` shell
  at load and honors `allowed-tools` self-grant — the two things dack's [[executable-skills-design]]
  explicitly rejects. dack **already** has safe progressive disclosure: `skills_catalogue()` lists
  name+description; the model reads the body + `references/` with the builtin `Read`. Keep that.
- **Bash — PORT: partial; the sandbox is the work.** SDK `BashTool` + Anthropic Sandbox Runtime
  (`@anthropic-ai/sandbox-runtime`: bubblewrap+seccomp+egress-proxy on Linux). **But the bridge already
  forces `dangerouslyDisableSandbox:true` for every Bash call** (no docker-in-docker in our container), so
  the ASRT sandbox is bypassed today — native bash over the bridge would be **unsandboxed**. The rich
  read-only/permission classifiers are valuable but deeply coupled to SDK types (costly to lift).

## 8. Recommended architecture + phased plan

**P0 — the FS sandbox (load-bearing; nothing ships without it).** A dack-owned confinement for the Settle
shell. bubblewrap is already in the image (`docs/deployment.md`) and works *inside* a container (it's user-
namespaces, not docker-in-docker — unlike the ASRT path the bridge disabled). The sandbox: a per-run
**scratch workspace** as the only writable mount; **hide `identities/`, `secrets/`, `dack.config.yaml`,
and the soul `.git`**; **egress allowlist** (bankr/api hosts, npm) via the proxy; inject **only** the one
skill's scoped secret. This closes §6.

**P1 — bash capability, Settle-only, default-off.** Two surfaces (DECISION):
  - **(a) dack `bash` MCP server** (`tier: settle`) that runs the command in the P0 sandbox and injects the
    scoped secret. *Pro:* pure dack-native — "configurable, default-off" falls out of the existing
    capability handshake (operator registers it + adds to `tier_policy.settle.import`; absent ⇒ off), the
    wall classifies it `SettleTx` (Settle-only) with zero `ToolClass::Shell`/SDK-strip surgery, and dack
    fully controls sandbox + secret + audit. *Con:* the model calls `mcp__bash__run{command}`, not the
    native `Bash` the SKILL.md ` ```bash ` blocks assume (a teaching detail).
  - **(b) native SDK `Bash`, un-stripped in Settle + bridge-sandboxed.** Uses §5's 4-item wall change +
    the `config.allow_bash_in_settle` flag + re-enabling the sandbox in the bridge for Settle. *Pro:*
    SKILL.md ` ```bash ` compatibility. *Con:* wall/SDK-strip surgery, and we still build the sandbox.
  → **Recommend (a)** — the sandbox is identical work either way, and (a) is safer + more dack-native, at
    the cost of teaching skills to call the bash tool by its MCP name.

**P2 — WebFetch enable + gate.** Un-suppress `WebFetch` (Net class, already in Perceive's scope; the SSRF
guard rides the SDK). Optionally admit it in Settle too. Cheap; ship early — it's independently useful.

**P3 — plain-text `SKILL.md` skills.** Reuse dack's catalogue + Read progressive disclosure. Extend
`skill_catalogue_entry()` to read `metadata.requires.bins` so orientation shows a skill's required CLIs +
whether they're installed. Add a `bash_allowed_bins` allowlist (operator lists the CLIs the sandbox may
run: `bankr`, `curl`, `jq`, …). Operator installs the CLIs system-wide (P4). **Skills are memory-like
(operator decision): Reflect-only writable (add `skills/` to the Reflect-write floor, like
`protected_memory_paths`), and we do NOT honor inline `` !`…` `` execution or `allowed-tools` self-grant.**

*Nav (Hermes research):* the whole ecosystem uses only two ideas — a **Tier-1 list** (Hermes `skills_list`;
dack's wake catalogue already IS this) and **read-the-file** for the body + `references/` (Bankr ships NO
nav tools — it rides the host `Read` + in-body relative links + per-skill `catalog.json`). So the minimum
is: **make the catalogue carry each skill's absolute dir + `requires.bins`**, adopt the convention that a
SKILL.md links its own `references/*.md`, and let the builtin `Read` do Tiers 2–3. The *one* optional
convenience worth a thin tool is **`view_skill(name) → {skill_dir, body, linked_files:{references,scripts,
assets,templates}}`** (resolves a bare name → dir + an explicit reference menu, saving the model a `Glob`).
Skip Hermes' slash-command expansion, install/audit CLI, readiness/env plumbing. (Bankr's own
`.claude/settings.json` also denies `Read` of `*.pem`/`*.key`/`*.env`/`config.json` — our sandbox hides
those at the FS layer, which is strictly stronger.)

**P4 — bankr skill + live RC test.** Operator: `npm i -g @bankr/cli`, `bankr login` (ToS + wallet + `bk_`
key — the *operator's* act), store the key as a scoped secret. Drop the bankr `SKILL.md` + `references/`
into the soul. Drive a Settle cycle that runs `bankr …` in the P0 sandbox → real trade/portfolio read,
capped by Bankr's own $500/tx server guardrails.

**Trust recap (defense in depth):** wall (bash only in Settle, only a clean cycle reaches Settle,
default-off) · P0 sandbox (no keys/soul/FS beyond a workspace + egress allowlist) · scoped secret (key
never in model context) · Bankr server ($500/tx + recipient allowlist, key can't raise its own limits) ·
tripwire (soul reverts) · dry_run (block the bash tool for tests).

## 9. Decisions to lock before building

1. **Sandbox mechanism (P0):** bubblewrap-in-container (recommended — image already has it) vs. reuse the
   worker Docker-isolation path vs. adopt the `@anthropic-ai/sandbox-runtime` npm package.
2. **Bash surface (P1):** dack `bash` MCP (recommended) vs. native SDK `Bash` in Settle.
3. **Bin allowlist (P3):** explicit `bash_allowed_bins` (recommended) vs. allow-all-inside-the-sandbox.
4. **Prose-skill trust:** operator-curated-in-soul + tripwire (recommended) vs. also signing `SKILL.md`.
5. **Onboarding division:** confirm the operator does `bankr login`/ToS/key-mint; the duck only ever uses
   a pre-provisioned scoped key (never self-onboards / accepts ToS).

Local target reference saved under `research/bankr-ref/` (SKILL.md, catalog.json, safety/api-workflow/
error-handling references).
