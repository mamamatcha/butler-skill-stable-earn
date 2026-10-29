"""Aave V3 USDC on Base: read the market and the owner's position, and build calldata.

    python3 aave.py status <ADDRESS>
    python3 aave.py supply <ADDRESS> <AMOUNT>
    python3 aave.py withdraw <ADDRESS> <AMOUNT|all>

Prints one JSON object and never sends anything; SKILL.md step 4 sends `txs`.
Fields: references/aave.md.
"""
import json, re, sys, urllib.request
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
if cmd not in ("status", "supply", "withdraw"):
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
if cmd == "status":
    out(s)
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
