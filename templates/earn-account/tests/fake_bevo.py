"""A scripted stand-in for the `bevo` SDK, for running duty.py offline.

`run(...)` installs a fresh fake as `bevo`, answers each shelled `bevo-rpc`
eth_call from the chain it is given, printed as the real launcher prints it,
makes the jitter sleep free, executes duty.py through its ticks, and returns
the fake for assertions.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent

WALLET = "0x00000000000000000000000000000000000000a1"
PROVIDER = "0xe20fcbdbffc4dd138ce8b2e6fbb6cb49777ad64d"
POOL = "0xa238dd80c259a72e81d7e4664a9801593f98d1c5"
AUSDC = "0x4e65fe4dba92790696d040ac24aa414708f5c0ab"
# Aave's liquidity rate (ray) for about 4.58% APY: Base, 2026-11-03.
RATE = 44_770_000_000_000_000_000_000_000


class BevoError(Exception):
    pass


def words(*values):
    return "0x" + "".join(format(v, "064x") for v in values)


def chain(lent_usdc=2004.12, pool=POOL, atoken=AUSDC, down=False):
    """An eth_call answerer: (to, data) -> hex result."""
    def answer(to, data):
        if down:
            raise BevoError("rpc eth_call on chain 8453 failed: timeout")
        if to == PROVIDER and data == "0x026b1d5f":
            return words(int(pool, 16))
        if to == POOL and data.startswith("0x35ea6a75"):
            reserve = [0] * 15
            reserve[2], reserve[8] = RATE, int(atoken, 16)
            return words(*reserve)
        if to == AUSDC and data.startswith("0x70a08231"):
            return words(round(lent_usdc * 1e6))
        raise AssertionError("unexpected eth_call to %s: %s" % (to, data))
    return answer


class FakeBevo:
    BevoError = BevoError

    def __init__(self, answers, ticks, platforms):
        self.answers = list(answers)
        self.ticks_left = ticks
        self.platforms = platforms
        self.logs, self.statuses, self.rows, self.removed, self.rpcs = [], [], [], [], []

    def log(self, message):
        self.logs.append(str(message))

    def status(self, next, last=None, next_at=None, **values):
        self.statuses.append((next, values))

    def rpc(self, chain_id, method, params=None):
        raise AssertionError("bevo.rpc() cannot parse an eth_call result; shell bevo-rpc")

    def platform_balance(self, site, name, usd, account="", icon=None, positions=None):
        self.rows.append({"site": site, "name": name, "usd": usd, "account": account,
                          "positions": positions})
        return {"id": "row-1"}

    def platform_balances(self):
        return list(self.platforms)

    def spawned(self, argv, **_kwargs):
        """`subprocess.run`: answers `bevo-rpc` and records `bevo-platforms remove <id>`.

        `bevo-rpc` prints the eth_call result as a bare JSON string on stdout and
        logs its endpoint on stderr, as the launcher does.
        """
        if argv[0] == "bevo-rpc":
            self.rpcs.append((int(argv[1]), argv[2]))
            call = json.loads(argv[3])[0]
            try:
                result = self.answers[0](call["to"], call["data"])
            except BevoError as exc:
                return subprocess.CompletedProcess(argv, 1, "", "[bevo-rpc] %s\n" % exc)
            log = "[rpc] chain=%s endpoint=https://mainnet.base.org rotated=false\n" % argv[1]
            return subprocess.CompletedProcess(argv, 0, json.dumps(result) + "\n", log)
        if list(argv[:2]) == ["bevo-platforms", "remove"]:
            self.removed.append(argv[2])
        return subprocess.CompletedProcess(argv, 0, "", "")

    def ticks(self):
        while self.ticks_left > 0:
            self.ticks_left -= 1
            # Each check after the first reads the next scripted chain.
            if len(self.answers) > 1:
                self.answers.pop(0)
            yield {"kind": "timer"}


def run(answers, ticks=0, wallet=WALLET, platforms=()):
    """Run duty.py: one check at start, then `ticks` more, each on the next of `answers`."""
    fake = FakeBevo(answers, ticks, list(platforms))
    spec = importlib.util.spec_from_file_location("duty_under_test", ROOT / "duty.py")
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"bevo": fake}), \
            mock.patch.dict(os.environ, {"PARAMS": json.dumps({"WALLET": wallet})}), \
            mock.patch("time.sleep"), \
            mock.patch("subprocess.run", fake.spawned):
        spec.loader.exec_module(module)
    return fake
