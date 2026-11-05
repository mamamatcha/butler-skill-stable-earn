"""Aave V3 USDC on Base: read the market and the owner's position, and build calldata.

    python3 aave.py status <ADDRESS>
    python3 aave.py supply <ADDRESS> <AMOUNT>
    python3 aave.py withdraw <ADDRESS> <AMOUNT|all>
    python3 aave.py quote <ADDRESS> <AMOUNT> [FEE]

Prints one JSON object and never sends anything; SKILL.md step 7 sends `txs`.
Fields: references/aave.md.

`status` also restarts the owner's earn-account duty, so the Platforms row re-reads
the position now rather than at its next tick, and says how that went in `row`.
"""
import json, re, subprocess, sys, urllib.request
from decimal import Decimal
RPCS = ["https://mainnet.base.org", "https://base-rpc.publicnode.com"]
# Pinned: a moved branch must never move the contracts the owner approves.
BOOK = ("https://raw.githubusercontent.com/bgd-labs/aave-address-book/"
        "07eacb66ed46eb24019867b3d80fa62e799dbe80/src/ts/AaveV3Base.ts")
HEX40 = r"0x[0-9a-fA-F]{40}"
def out(d):
    print(json.dumps(d)); sys.exit(0)
def http(url, body=None):
    h = {"User-Agent": "butler-stable-earn", "Content-Type": "application/json"}
    with urllib.request.urlopen(urllib.request.Request(url, body, h), timeout=15) as f:
        return f.read().decode()
def book():
    try:
        t = http(BOOK)
        top = lambda k: re.search(r"export const %s = '(%s)'" % (k, HEX40), t).group(1)
        blk = re.search(r"\n  USDC: \{(.*?)\n  \}", t, re.S).group(1)
        pick = lambda k: re.search(k + r": '(%s)'" % HEX40, blk).group(1)
        return top("POOL"), top("POOL_ADDRESSES_PROVIDER"), pick("UNDERLYING"), pick("A_TOKEN")
    except Exception as e:
        out({"error": "book_unavailable", "detail": str(e)})
def call(to, data):
    err = None
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": to, "data": data}, "latest"]}).encode()
    for url in RPCS:
        try:
            r = json.loads(http(url, body))
            # "0x" is what a call to an address with no code returns.
            if len(r.get("result") or "") > 2:
                return r["result"][2:]
            err = r.get("error") or "empty result from %s" % to
        except Exception as e:
            err = str(e)
    out({"error": "rpc_unavailable", "detail": str(err)})
A = lambda x: x.lower()[2:].rjust(64, "0")
U = lambda n: format(n, "064x")
W = lambda h: [int(h[i:i + 64], 16) for i in range(0, len(h), 64)]
APY = lambda ray: round(((1 + ray / 1e27 / 31536000) ** 31536000 - 1) * 100, 2)
def units(x):
    try:
        v = int(Decimal(x) * 10**6)
    except Exception:
        v = 0
    if v <= 0:
        out({"error": "bad_amount"})
    return v
args = sys.argv[1:] + ["", "", ""]
cmd, owner, arg = args[0], args[1], args[2]
if cmd not in ("status", "supply", "withdraw", "quote"):
    out({"error": "bad_command"})
if not re.fullmatch(HEX40, owner):
    out({"error": "bad_address"})
pool, provider, usdc, ausdc = book()
if "0x%040x" % W(call(provider, "0x026b1d5f"))[0] != pool.lower():
    out({"error": "address_mismatch"})
rd = W(call(pool, "0x35ea6a75" + A(usdc)))
if "0x%040x" % rd[8] != ausdc.lower():
    out({"error": "address_mismatch"})
cfg = rd[0]
bal = lambda tok, who: W(call(tok, "0x70a08231" + A(who)))[0]
wallet, earning, cash = bal(usdc, owner), bal(ausdc, owner), bal(usdc, ausdc)
supply = W(call(ausdc, "0x18160ddd"))[0]
allow = W(call(usdc, "0xdd62ed3e" + A(owner) + A(pool)))[0]
cap = (cfg >> 116) & (2**36 - 1)
s = {"venue": "aave", "chain_id": 8453,
     "owner": owner, "pool": pool, "usdc": usdc, "ausdc": ausdc,
     "apy_pct": APY(rd[2]), "borrow_apy_pct": APY(rd[4]),
     "utilization_pct": round(100 * (1 - cash / supply), 1) if supply else 0.0,
     "wallet_usdc": wallet / 1e6, "earning_usdc": earning / 1e6,
     "withdrawable_now_usdc": min(earning, cash) / 1e6, "allowance_usdc": allow / 1e6,
     "est_week_usd": round(earning / 1e6 * APY(rd[2]) / 100 / 52, 2),
     "active": bool(cfg >> 56 & 1), "frozen": bool(cfg >> 57 & 1), "paused": bool(cfg >> 60 & 1),
     "cap_room_usdc": None if cap == 0 else max(0, cap * 10**6 - supply) / 1e6}
def automation(*a):
    r = subprocess.run(["bevo-automation", *a], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-200:])
    return r.stdout
def row():
    """Restart the earn-account@2 duty, or turn it on if it was off; it re-reads the
    position as it starts.

    Done here rather than left to SKILL.md step 9 because the model, resuming a
    supply in a later turn, re-ran status and stopped, leaving the row stale.
    """
    try:
        duties = [d for d in json.loads(automation("list")).get("duties", [])
                  if str(d.get("recipe", "")).startswith("earn-account@")]
    except Exception as e:
        return {"row": "unknown", "row_detail": str(e)[:200]}
    if not duties:
        return {"row": "no_duty"}
    current = [d for d in duties if d.get("recipe") == "earn-account@2"]
    if not current:
        return {"row": "old_recipe", "duty_id": duties[0]["id"]}
    d = next((d for d in current if d.get("state") == "live"), current[0])
    if d.get("state") == "pending":
        return {"row": "pending", "duty_id": d["id"]}
    was_live = d.get("state") == "live"
    if was_live:
        try:
            automation("disable", d["id"])
        except Exception as e:
            return {"row": "restart_failed", "duty_id": d["id"], "row_detail": str(e)[:200]}
    for _ in range(2):
        try:
            automation("enable", d["id"])
            return {"row": "restarted" if was_live else "turned_on", "duty_id": d["id"]}
        except Exception as e:
            err = str(e)[:200]
    return {"row": "left_off", "duty_id": d["id"], "row_detail": err}
if cmd == "quote":
    amt = units(arg) / 1e6
    try:
        fee = float(Decimal(args[3] or "0"))
    except Exception:
        out({"error": "bad_amount"})
    if fee < 0:
        out({"error": "bad_amount"})
    week = lambda x: x * s["apy_pct"] / 100 / 52
    now = earning / 1e6
    total = now + amt
    q = {"lend_usdc": amt, "apy_pct": s["apy_pct"], "earning_now_usdc": round(now, 2),
         "est_week_usd": round(week(amt), 4), "est_month_usd": round(week(amt) * 52 / 12, 4),
         "earning_after_usdc": round(total, 2), "est_week_after_usd": round(week(total), 4),
         "est_month_after_usd": round(week(total) * 52 / 12, 4),
         "fee_usd": fee, "fee_weeks": round(fee / week(amt), 1) if fee and amt else 0}
    c = lambda x: "$%.2f" % x if x >= 0.1 else "%.1f cents" % (x * 100)
    lines = ["Lending $%.2f at %.2f%% (variable) earns about %s a week, %s a month." % (
                 amt, s["apy_pct"], c(q["est_week_usd"]), c(q["est_month_usd"])),
             "With the $%.2f already lent, $%.2f would be earning: about %s a week, %s a month." % (
                 q["earning_now_usdc"], q["earning_after_usdc"], c(q["est_week_after_usd"]), c(q["est_month_after_usd"]))]
    if q["fee_weeks"]:
        w = q["fee_weeks"]
        span = "" if w < 4 else " (about %s months)" % round(w / 4.33, 1) if w < 52 else " (about %s years)" % round(w / 52, 1)
        lines.append("The $%.2f of fees is about %s weeks%s of the new $%.2f's interest: that long before the move pays for itself." % (fee, w, span, amt))
    out({**q, "summary": "\n".join("- " + l for l in lines)})
if cmd == "status":
    out({**s, **row()})
if cmd == "supply":
    amt = units(arg)
    if not s["active"] or s["frozen"] or s["paused"]:
        out({**s, "error": "market_closed"})
    if amt > wallet:
        out({**s, "error": "not_enough_usdc"})
    if s["cap_room_usdc"] is not None and amt / 1e6 > s["cap_room_usdc"]:
        out({**s, "error": "supply_cap_reached"})
    txs = [] if allow >= amt else [{"op": "approve", "to": usdc, "data": "0x095ea7b3" + A(pool) + U(amt)}]
    txs.append({"op": "supply", "to": pool, "data": "0x617ba037" + A(usdc) + U(amt) + A(owner) + U(0)})
    out({**s, "amount_usdc": amt / 1e6, "txs": txs})
if cmd == "withdraw":
    every = arg == "all"
    amt = 2**256 - 1 if every else units(arg)
    need = earning if every else amt
    if s["paused"]:
        out({**s, "error": "market_paused"})
    if need == 0 or need > earning:
        out({**s, "error": "more_than_earning"})
    if need > cash:
        out({**s, "error": "not_enough_liquidity"})
    out({**s, "amount_usdc": need / 1e6, "txs": [{"op": "withdraw", "to": pool,
        "data": "0x69328dec" + A(usdc) + U(amt) + A(owner)}]})
out({"error": "bad_command"})
