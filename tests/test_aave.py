"""Offline checks of scripts/aave.py: the address book and every eth_call are stubbed."""
import contextlib
import io
import json
import pathlib
import runpy
import sys
import unittest
from unittest import mock

SCRIPT = str(pathlib.Path(__file__).resolve().parent.parent / "scripts" / "aave.py")

POOL = "0x" + "a1" * 20
PROVIDER = "0x" + "b2" * 20
USDC = "0x" + "c3" * 20
AUSDC = "0x" + "d4" * 20
OWNER = "0x" + "e5" * 20
MAX_UINT = 2**256 - 1

BOOK = f"""export const POOL_ADDRESSES_PROVIDER = '{PROVIDER}';
export const POOL = '{POOL}';
export const ASSETS = {{
  USDC: {{
    UNDERLYING: '{USDC}',
    A_TOKEN: '{AUSDC}',
  }},
}};
"""

word = lambda n: format(n, "064x")
addr = lambda a: a.lower()[2:].rjust(64, "0")


def config(active=True, frozen=False, paused=False, cap=0):
    return (active << 56) | (frozen << 57) | (paused << 60) | (cap << 116)


class Chain:
    """What the stubbed RPC answers. Amounts are in USDC base units (6 decimals)."""

    def __init__(self, **kw):
        self.wallet = kw.get("wallet", 50_000_000)
        self.earning = kw.get("earning", 20_000_000)
        self.cash = kw.get("cash", 1_000_000_000)
        self.supply = kw.get("supply", 10_000_000_000)
        self.allowance = kw.get("allowance", 0)
        self.config = kw.get("config", config())
        self.provider_pool = kw.get("provider_pool", POOL)
        self.atoken = kw.get("atoken", AUSDC)

    def call(self, to, data):
        to, sel, arg = to.lower(), data[:10], data[10:]
        if (to, sel) == (PROVIDER, "0x026b1d5f"):
            return addr(self.provider_pool)
        if (to, sel) == (POOL, "0x35ea6a75"):
            rate = 5 * 10**25  # 5% a year, in ray
            return "".join(word(w) for w in [self.config, 0, rate, 0, rate, 0, 0, 0]) + addr(self.atoken) + word(0) * 6
        if sel == "0x70a08231":
            who = "0x" + arg[24:64]
            if to == USDC:
                return word(self.cash if who == AUSDC else self.wallet)
            return word(self.earning)
        if (to, sel) == (AUSDC, "0x18160ddd"):
            return word(self.supply)
        if (to, sel) == (USDC, "0xdd62ed3e"):
            return word(self.allowance)
        raise AssertionError(f"unexpected call {to} {data}")


def run(chain, *args):
    def urlopen(req, timeout=None):
        if req.data is None:
            body = BOOK
        else:
            params = json.loads(req.data)["params"][0]
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x" + chain.call(params["to"], params["data"])})
        res = mock.MagicMock()
        res.__enter__.return_value.read.return_value = body.encode()
        return res

    stdout = io.StringIO()
    with mock.patch("urllib.request.urlopen", urlopen), mock.patch.object(sys, "argv", [SCRIPT, *args]):
        with contextlib.redirect_stdout(stdout), contextlib.suppress(SystemExit):
            runpy.run_path(SCRIPT, run_name="__main__")
    return json.loads(stdout.getvalue())


class Arguments(unittest.TestCase):
    def test_refuses_before_any_read(self):
        chain = mock.MagicMock()
        chain.call.side_effect = AssertionError("read the network")
        self.assertEqual(run(chain, "borrow", OWNER), {"error": "bad_command"})
        self.assertEqual(run(chain, "status", "0x1234"), {"error": "bad_address"})
        self.assertEqual(run(chain), {"error": "bad_command"})

    def test_refuses_a_bad_amount(self):
        for amount in ["", "-5", "0", "NaN", "lots"]:
            self.assertEqual(run(Chain(), "supply", OWNER, amount)["error"], "bad_amount", amount)


class Status(unittest.TestCase):
    def test_reads_the_market_and_the_owner(self):
        s = run(Chain(), "status", OWNER)
        self.assertNotIn("error", s)
        self.assertEqual((s["venue"], s["chain_id"]), ("aave", 8453))
        self.assertEqual((s["pool"], s["usdc"], s["ausdc"]), (POOL, USDC, AUSDC))
        self.assertEqual((s["wallet_usdc"], s["earning_usdc"]), (50.0, 20.0))
        self.assertEqual(s["utilization_pct"], 90.0)
        self.assertAlmostEqual(s["apy_pct"], 5.13, places=2)
        self.assertIsNone(s["cap_room_usdc"])

    def test_refuses_a_pool_the_provider_does_not_point_at(self):
        self.assertEqual(run(Chain(provider_pool=OWNER), "status", OWNER), {"error": "address_mismatch"})

    def test_refuses_an_atoken_the_pool_does_not_name(self):
        self.assertEqual(run(Chain(atoken=OWNER), "status", OWNER), {"error": "address_mismatch"})


class Supply(unittest.TestCase):
    def test_approves_the_exact_amount_then_supplies_for_the_owner(self):
        s = run(Chain(), "supply", OWNER, "10")
        self.assertEqual([t["op"] for t in s["txs"]], ["approve", "supply"])
        approve, supply = s["txs"]
        self.assertEqual(approve["to"], USDC)
        self.assertEqual(approve["data"], "0x095ea7b3" + addr(POOL) + word(10_000_000))
        self.assertEqual(supply["to"], POOL)
        self.assertEqual(supply["data"], "0x617ba037" + addr(USDC) + word(10_000_000) + addr(OWNER) + word(0))

    def test_skips_the_approve_when_the_allowance_covers_it(self):
        s = run(Chain(allowance=10_000_000), "supply", OWNER, "10")
        self.assertEqual([t["op"] for t in s["txs"]], ["supply"])

    def test_refuses_more_than_the_wallet(self):
        self.assertEqual(run(Chain(), "supply", OWNER, "50.01")["error"], "not_enough_usdc")

    def test_refuses_a_closed_market(self):
        for cfg in [config(active=False), config(frozen=True), config(paused=True)]:
            self.assertEqual(run(Chain(config=cfg), "supply", OWNER, "1")["error"], "market_closed")

    def test_refuses_past_the_supply_cap(self):
        s = run(Chain(config=config(cap=10_005)), "supply", OWNER, "6")
        self.assertEqual((s["error"], s["cap_room_usdc"]), ("supply_cap_reached", 5.0))


class Withdraw(unittest.TestCase):
    def test_withdraws_everything_to_the_owner(self):
        s = run(Chain(), "withdraw", OWNER, "all")
        (tx,) = s["txs"]
        self.assertEqual((tx["op"], tx["to"], s["amount_usdc"]), ("withdraw", POOL, 20.0))
        self.assertEqual(tx["data"], "0x69328dec" + addr(USDC) + word(MAX_UINT) + addr(OWNER))

    def test_refuses_more_than_is_lent(self):
        self.assertEqual(run(Chain(), "withdraw", OWNER, "21")["error"], "more_than_earning")

    def test_refuses_more_than_the_pool_has(self):
        self.assertEqual(run(Chain(cash=5_000_000), "withdraw", OWNER, "6")["error"], "not_enough_liquidity")

    def test_still_withdraws_from_a_frozen_market_but_not_a_paused_one(self):
        self.assertIn("txs", run(Chain(config=config(frozen=True)), "withdraw", OWNER, "1"))
        self.assertEqual(run(Chain(config=config(paused=True)), "withdraw", OWNER, "1")["error"], "market_paused")


if __name__ == "__main__":
    unittest.main()
