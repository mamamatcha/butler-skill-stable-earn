"""Keep the owner's USDC lent on Aave (Base) on the wallet's Platforms tab.

Each check reads the position on-chain through `bevo-rpc`: the wallet's aBasUSDC,
which is the USDC lent plus the interest it has earned, one for one, and the
market's supply rate. While anything is lent there is one "Aave" row, keyed by
the wallet, at that figure; once nothing is, the row is removed.

The contracts are pinned, as in the skill's `scripts/aave.py`, and every check
confirms them on-chain (the address provider's Pool, the Pool's aToken for USDC)
before writing anything. A failed or mismatched read writes nothing, so the row
keeps its last good value.

It checks once when it starts, so the skill restarting it after a supply or a
withdrawal refreshes the row at once, then on every tick.
"""

import bevo
import json
import os
import random
import re
import subprocess
import time

PARAMS = json.loads(os.environ["PARAMS"])
WALLET = str(PARAMS.get("WALLET") or "").lower()

BASE = 8453
PROVIDER = "0xe20fcbdbffc4dd138ce8b2e6fbb6cb49777ad64d"
POOL = "0xa238dd80c259a72e81d7e4664a9801593f98d1c5"
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
AUSDC = "0x4e65fe4dba92790696d040ac24aa414708f5c0ab"
SECONDS_PER_YEAR = 31536000


def say(text):
    """`bevo.log()` on one line: an echoed error must not forge a log line."""
    bevo.log(" ".join(str(text).split()))


def word(address):
    return address[2:].rjust(64, "0")


def call(to, data):
    """One eth_call on Base, as 32-byte words.

    Shelled rather than `bevo.rpc()`: `bevo-rpc` prints an eth_call's result as a
    bare JSON string, and the SDK only accepts a JSON object, so `bevo.rpc()`
    raises on every eth_call.
    """
    params = json.dumps([{"to": to, "data": data}, "latest"])
    try:
        done = subprocess.run(["bevo-rpc", str(BASE), "eth_call", params],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise bevo.BevoError("bevo-rpc: %s" % exc)
    if done.returncode != 0:
        raise bevo.BevoError("bevo-rpc: %s" % done.stderr.strip()[-200:])
    try:
        result = json.loads(done.stdout)
    except ValueError:
        raise bevo.BevoError("bevo-rpc answered %r" % done.stdout[:120])
    if not isinstance(result, str) or len(result) <= 2:
        raise bevo.BevoError("empty result from %s" % to)
    body = result[2:]
    return [int(body[i:i + 64], 16) for i in range(0, len(body), 64)]


def apy_pct(ray):
    return round(((1 + ray / 1e27 / SECONDS_PER_YEAR) ** SECONDS_PER_YEAR - 1) * 100, 2)


def read():
    """(USDC lent, APY %), or None when the contracts do not check out."""
    if "0x%040x" % call(PROVIDER, "0x026b1d5f")[0] != POOL:
        return None
    reserve = call(POOL, "0x35ea6a75" + word(USDC))
    if "0x%040x" % reserve[8] != AUSDC:
        return None
    lent = call(AUSDC, "0x70a08231" + word(WALLET))[0] / 1e6
    return lent, apy_pct(reserve[2])


def remove_row():
    """Remove this wallet's Aave row, if there is one."""
    for row in bevo.platform_balances():
        if row.get("siteHost") != "app.aave.com" or str(row.get("account")).lower() != WALLET:
            continue
        done = subprocess.run(["bevo-platforms", "remove", str(row.get("id"))],
                              capture_output=True, text=True, timeout=30)
        if done.returncode != 0:
            say("could not remove the Aave row: %s" % done.stderr[:200])


def check():
    try:
        position = read()
    except bevo.BevoError as exc:
        say("could not read Aave: %s" % exc)
        bevo.status("unreadable")
        return
    if position is None:
        say("Aave's contracts did not match the pinned addresses; nothing written")
        bevo.status("unreadable")
        return
    lent, apy = position
    if lent < 0.01:
        remove_row()
        bevo.status("empty")
        return
    value = round(lent, 2)
    week = round(lent * apy / 100 / 52, 2)
    bevo.platform_balance("https://app.aave.com", "Aave", value, account=WALLET, positions=[{
        "title": "USDC lent",
        "subtitle": "Aave V3 · Base",
        "valueUsd": value,
        "details": [{"label": "APY (variable)", "value": "%s%%" % apy},
                    {"label": "About a week", "value": "$%s" % format(week, ",.2f")}],
    }])
    bevo.status("ok", value=value, apy=apy)


def run_check():
    try:
        check()
    except Exception as exc:
        # Never bevo.fail(): Base out of reach is not this duty failing.
        say("check skipped: %s" % exc)


if not re.fullmatch(r"0x[0-9a-f]{40}", WALLET):
    say("WALLET is not an address: %r" % WALLET)
    bevo.status("blocked")
else:
    run_check()

for tick in bevo.ticks():
    if not re.fullmatch(r"0x[0-9a-f]{40}", WALLET):
        continue
    # Spreads every owner's read across the minute instead of the timer's edge.
    time.sleep(random.uniform(0, 60))
    run_check()
