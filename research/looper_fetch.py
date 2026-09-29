#!/usr/bin/env python3
"""
looper_fetch.py — pull a Looper NFT's on-chain tokenURI → metadata → personality codex.

The Loopers collection (Base mainnet, 0x1649CD37f4748807b4882FC48765bA0B2aFfa94a) stores a
per-token metadata JSON on Arweave, which links a richer `codex_uri` (the personality matrix:
class scores, trait atoms, composed personality, lore, activation prompt). This resolves all
three and writes them to metadata/<id>.json, metadata/<id>.codex.json, and prints a distilled
personality summary — the raw material for composing a dack soul.

  ALCHEMY_KEY=<key> ./looper_fetch.py 370
  ALCHEMY_KEY=<key> ./looper_fetch.py 370 --summary-only

The key is read from the env (never hardcoded — this dir becomes a pond template).
"""
import json
import os
import sys
import urllib.request

CONTRACT = "0x1649CD37f4748807b4882FC48765bA0B2aFfa94a"  # Loopers, Base mainnet
RPC = "https://base-mainnet.g.alchemy.com/v2/{key}"
# Any Base-mainnet JSON-RPC works; `RPC_URL` overrides the Alchemy default so you can read a codex
# with no account at all (e.g. RPC_URL=https://mainnet.base.org).
RPC_URL = os.environ.get("RPC_URL")
# Public RPC gateways and the Arweave gateway sit behind bot protection that 403s urllib's default
# `Python-urllib/3.x` agent. Send a normal browser UA.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")
TOKEN_URI_SELECTOR = "0xc87b56dd"  # tokenURI(uint256)
OUT_DIR = os.path.join(os.path.dirname(__file__), "metadata")


def _post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"content-type": "application/json", "user-agent": UA}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _get_json(url: str) -> dict:
    # arweave.net 302-redirects to a content-addressed subdomain; urllib follows redirects.
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def ar_to_https(uri: str) -> str:
    """ar://<txid>[/path] → an arweave.net gateway URL."""
    if uri.startswith("ar://"):
        return "https://arweave.net/" + uri[len("ar://"):]
    return uri


def token_uri(rpc: str, token_id: int) -> str:
    data = TOKEN_URI_SELECTOR + f"{token_id:064x}"
    res = _post(rpc, {"id": 1, "jsonrpc": "2.0", "method": "eth_call",
                      "params": [{"to": CONTRACT, "data": data}, "latest"]})
    if "error" in res:
        raise RuntimeError(f"eth_call failed: {res['error']}")
    return _decode_abi_string(res["result"])


def _decode_abi_string(hexstr: str) -> str:
    """Decode an ABI-encoded single `string` return (offset, length, bytes)."""
    b = bytes.fromhex(hexstr[2:] if hexstr.startswith("0x") else hexstr)
    # [0:32] offset (0x20), [32:64] length, then the utf-8 bytes.
    length = int.from_bytes(b[32:64], "big")
    return b[64:64 + length].decode("utf-8")


def summarize(meta: dict, codex: dict) -> str:
    p = codex.get("personality", {})
    lines = [
        f"# {meta.get('name')}  —  {meta.get('agent_class')}",
        f"voice: {p.get('voice') or meta.get('voice')}",
        f"risk: {p.get('risk_profile')} ({p.get('risk_tolerance')}/10)   "
        f"autonomy: {p.get('autonomy_profile')} ({p.get('autonomy_level')}/10)   "
        f"specialization: {meta.get('specialization')}",
        f"first missions: {', '.join(codex.get('activation', {}).get('first_missions', []))}",
        "",
        "class scores: " + ", ".join(f"{k}={v}" for k, v in sorted(
            codex.get("class_scores", {}).items(), key=lambda kv: -kv[1]) if v),
        "",
        "values: " + " | ".join(p.get("values", [])),
        "quirks: " + " | ".join(p.get("quirks", [])),
        "",
        "short lore: " + codex.get("lore", {}).get("short_lore", ""),
        "",
        "activation_prompt:",
        "  " + codex.get("activation", {}).get("activation_prompt", ""),
    ]
    return "\n".join(lines)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: ALCHEMY_KEY=<key> ./looper_fetch.py <token_id> [--summary-only]")
    token_id = int(args[0])
    if RPC_URL:
        rpc = RPC_URL
    else:
        key = os.environ.get("ALCHEMY_KEY")
        if not key:
            sys.exit("set ALCHEMY_KEY, or RPC_URL for any Base-mainnet JSON-RPC endpoint")
        rpc = RPC.format(key=key)

    uri = token_uri(rpc, token_id)
    meta = _get_json(uri)
    codex = _get_json(ar_to_https(meta["codex_uri"])) if meta.get("codex_uri") else {}

    os.makedirs(OUT_DIR, exist_ok=True)
    if "--summary-only" not in sys.argv:
        with open(os.path.join(OUT_DIR, f"{token_id}.json"), "w") as f:
            json.dump(meta, f, indent=2)
        if codex:
            with open(os.path.join(OUT_DIR, f"{token_id}.codex.json"), "w") as f:
                json.dump(codex, f, indent=2)
        print(f"tokenURI: {uri}")
        print(f"wrote metadata/{token_id}.json" + (f" + metadata/{token_id}.codex.json" if codex else ""))
        print(f"image: {ar_to_https(meta.get('image', ''))}\n")
    print(summarize(meta, codex))


if __name__ == "__main__":
    main()
