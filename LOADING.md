# Loading a looper — from composed soul to running duck

`compose_soul.py` produces a **soul bundle** (`souls/looper-<id>/`: `SOUL.md`, `prompts/`, `stimuli/`,
`memory/`, `skills/`, and a `dack.config.example.yaml`). This guide turns that bundle into a **running
duck** on the [dack engine](https://github.com/obraztsov/dack-engine).

Everything below uses placeholders — fill in your own values. Real credentials live only in your local
run directory and are gitignored; **never commit a filled config, a secret, or an identity key.**

## The run-directory layout

A duck runs from one directory (call it `<run-dir>`; in Docker it's mounted at `/duck`). The **soul git**
is a subdirectory (`dack-soul/`); the operator's runtime state (config, secrets, keys, databases) sits at
the root, *outside* the soul — so the soul's integrity tripwire only ever guards prompts/memory, never
your keys.

```
<run-dir>/
├─ dack-soul/                 # the composed soul bundle (its own git repo)
│  ├─ SOUL.md  prompts/  stimuli/  memory/  skills/
├─ dack.config.yaml           # filled from dack.config.example.yaml   (gitignored)
├─ identities/                # dack keygen output: operator/ , soul/    (gitignored)
├─ secrets/                   # token files (model / telegram / buzz)    (gitignored)
├─ telegram-ingress.config.json   /   buzz-ingress.config.json          (gitignored)
└─ (runlogs.sqlite, dack.sqlite, media/ … created at runtime)
```

## 1 · Compose the soul

```bash
research/compose_soul.py <id>                       # → souls/looper-<id>/
# add capabilities as needed:
#   --bash-skills --skill /path/to/bankr            # a Settle-gated wallet skill (Bankr, third-party)
#   --tg-handle my_looper_bot                        # the Telegram bot username it answers to
```

## 2 · Arrange the run directory

```bash
run=~/ducks/looper-<id>
mkdir -p "$run/dack-soul"
cp -r souls/looper-<id>/{SOUL.md,prompts,stimuli,memory,skills} "$run/dack-soul/"
cp    souls/looper-<id>/dack.config.example.yaml "$run/dack.config.yaml"
( cd "$run/dack-soul" && git init -q && git add -A && git commit -qm "genesis soul" )
```

The soul must be a clean git tree — the engine reverts uncommitted drift on each cycle. After you
hand-edit a soul file later, run `dack reconcile` (or commit it) so the tripwire keeps it.

## 3 · Identities

```bash
cd "$run"
dack keygen --role operator --dir identities/operator   # prints a did:key — paste into operator_did
dack keygen --role soul     --dir identities/soul       # the duck's own signing identity
```

## 4 · Secrets

The config's `secrets_providers` read small token files (via `file_token.py`). Create them (mode 0600):

```bash
mkdir -p "$run/secrets"
printf '%s' "<telegram-bot-token>"   > "$run/secrets/telegram.token"
printf '%s' "<buzz-nostr-hex-key>"   > "$run/secrets/buzz.key"      # only if wiring Buzz
printf '%s' "<bankr-api-key>"        > "$run/secrets/bankr.key"     # only with --bash-skills
chmod 600 "$run"/secrets/*
```

The model endpoint key goes in `runtime.connector.api_key` in the config (or a provider of your choosing).
Secrets are materialized into a tool's process env by the engine's wall — the model never sees them.

## 5 · Fill the config

Edit `<run-dir>/dack.config.yaml` (from the generated example). At minimum:

- **`operator_did`** — the `did:key` printed by `dack keygen --role operator` in step 3.
- **`runtime.connector`** — `api_url` + `api_key` of an OpenAI-compatible endpoint, and **`model`**.
- **`mcp_servers`** transport paths — they point at your `dack-engine` checkout (or `/app` in the image);
  set them to where the engine actually lives.
- **`telegram-send`** `TELEGRAM_DESTINATIONS` — the chat ids the duck may *proactively* post to
  (`{"holder": <dm>, "org": <group>, "public": <group>}`). Reply is destination-locked separately.

See the engine's [`docs/configuration.md`](https://github.com/obraztsov/dack-engine) for every field.

## 6 · Channels (ingress)

Inbound messages arrive through **ingress modules** that POST webhooks into the duck. Each has a small
JSON config at the run-dir root (gitignored). Illustrative shapes — see the engine's ingress docs for the
authoritative fields:

- **Telegram** — create a bot with [@BotFather](https://t.me/BotFather); to hear group messages (not just
  @-mentions) **disable privacy mode** (`/setprivacy → Disable`) and re-add the bot. `telegram-ingress`
  routes DM/group/operator to the right trust lane.
- **Buzz** (optional) — a Nostr relay workspace. `buzz-ingress` watches channels and wakes the duck on
  mentions/replies; `buzz.key` is its identity. Set `BUZZ_RELAY` at compose time (step 1 / `.env`).

Both channels are optional and independent — run Telegram-only to start.

## 7 · Run

```bash
cd "$run"
dack run            # the long-running actor-scheduler (Perceive → Express → Settle → Reflect)
```

Or in Docker, mounting the run directory as `/duck` and using the engine's image (see the engine repo for
the Dockerfile / image build):

```bash
docker run -d --name looper-<id> --init --restart unless-stopped \
  -v "$run":/duck -w /duck <dack-engine-image>
```

## Operating it

- `dack status` — alive / last run / queue depth / current state.
- `dack log --follow` — the agent's syslog (its thoughts + actions).
- `dack say "<instruction>"` — inject a trusted operator instruction.
- `dack reconcile` — commit hand-edits to the soul so the tripwire doesn't revert them.
- Ducks are **quiet by default** — they act on messages, on a periodic heartbeat, and in a scheduled
  Reflect pass where they tune their own memory and reply policy. Silence is normal.
