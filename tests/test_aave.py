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


class Automation:
    """A stub `bevo-automation`: answers `list` with these duties, records every call."""

    def __init__(self, duties=(), fail=()):
        self.duties = list(duties)
        self.fail = set(fail)
        self.calls = []

    def __call__(self, argv, **kw):
        assert argv[0] == "bevo-automation", argv
        self.calls.append(argv[1:])
        res = mock.MagicMock(returncode=0, stdout="", stderr="")
        if argv[1] in self.fail:
            res.returncode, res.stderr = 1, "%s refused" % argv[1]
        elif argv[1] == "list":
            res.stdout = json.dumps({"duties": self.duties}, indent=2)
        return res


DUTY = "bdf2fcf7-fd35-41a9-9986-b11865da68b9"


def run(chain, *args, automation=None):
    automation = automation or Automation()
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
    with mock.patch("urllib.request.urlopen", urlopen), mock.patch.object(sys, "argv", [SCRIPT, *args]), \
            mock.patch("subprocess.run", automation):
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


class Quote(unittest.TestCase):
    def test_says_what_the_amount_earns_and_what_the_fee_costs(self):
        bot = Automation()
        q = run(Chain(), "quote", OWNER, "10", "0.06", automation=bot)
        self.assertNotIn("error", q)
        self.assertEqual((q["lend_usdc"], q["earning_now_usdc"], q["earning_after_usdc"]), (10.0, 20.0, 30.0))
        self.assertAlmostEqual(q["est_week_usd"], 10 * 5.13 / 100 / 52, places=3)
        self.assertAlmostEqual(q["fee_weeks"], 6.1, places=1)
        self.assertEqual(q["summary"].split("\n"), [
            "- Lending $10.00 at 5.13% (variable) earns about 1.0 cents a week, 4.3 cents a month.",
            "- With the $20.00 already lent, $30.00 would be earning: about 3.0 cents a week, $0.13 a month.",
            "- The $0.06 of fees is about 6.1 weeks (about 1.4 months) of the new $10.00's interest:"
            " that long before the move pays for itself.",
        ])
        self.assertEqual(bot.calls, [])

    def test_no_fee_line_without_a_move(self):
        q = run(Chain(), "quote", OWNER, "10")
        self.assertEqual((q["fee_usd"], q["fee_weeks"]), (0, 0))
        self.assertEqual(len(q["summary"].split("\n")), 2)

    def test_refuses_a_bad_amount_or_fee(self):
        for args in [("0",), ("lots",), ("10", "$0.06"), ("10", "-1")]:
            self.assertEqual(run(Chain(), "quote", OWNER, *args)["error"], "bad_amount", args)


class Row(unittest.TestCase):
    def duty(self, recipe="earn-account@2", state="live", id=DUTY):
        return {"id": id, "name": "earn-account-aave", "mode": "code", "recipe": recipe, "state": state}

    def test_status_restarts_the_live_duty(self):
        bot = Automation([{"id": "x", "name": "btc-dca", "state": "live"}, self.duty()])
        s = run(Chain(), "status", OWNER, automation=bot)
        self.assertEqual((s["row"], s["duty_id"]), ("restarted", DUTY))
        self.assertEqual(bot.calls, [["list"], ["disable", DUTY], ["enable", DUTY]])

    def test_says_when_there_is_no_duty(self):
        bot = Automation([{"id": "x", "name": "btc-dca", "state": "live"}])
        self.assertEqual(run(Chain(), "status", OWNER, automation=bot)["row"], "no_duty")
        self.assertEqual(bot.calls, [["list"]])

    def test_names_a_duty_still_on_the_old_recipe(self):
        bot = Automation([self.duty(recipe="earn-account@1")])
        s = run(Chain(), "status", OWNER, automation=bot)
        self.assertEqual((s["row"], s["duty_id"]), ("old_recipe", DUTY))
        self.assertEqual(bot.calls, [["list"]])

    def test_turns_a_duty_that_is_off_back_on(self):
        bot = Automation([self.duty(state="disabled")])
        s = run(Chain(), "status", OWNER, automation=bot)
        self.assertEqual((s["row"], s["duty_id"]), ("turned_on", DUTY))
        self.assertEqual(bot.calls, [["list"], ["enable", DUTY]])

    def test_says_when_a_duty_that_is_off_would_not_turn_on(self):
        bot = Automation([self.duty(state="disabled")], fail={"enable"})
        self.assertEqual(run(Chain(), "status", OWNER, automation=bot)["row"], "left_off")

    def test_prefers_the_live_duty_when_there_are_two(self):
        bot = Automation([self.duty(state="disabled", id="off"), self.duty()])
        self.assertEqual(run(Chain(), "status", OWNER, automation=bot)["row"], "restarted")
        self.assertEqual(bot.calls, [["list"], ["disable", DUTY], ["enable", DUTY]])

    def test_leaves_a_duty_not_yet_armed_alone(self):
        bot = Automation([self.duty(state="pending")])
        self.assertEqual(run(Chain(), "status", OWNER, automation=bot)["row"], "pending")
        self.assertEqual(bot.calls, [["list"]])

    def test_says_when_a_restart_left_the_duty_off(self):
        bot = Automation([self.duty()], fail={"enable"})
        s = run(Chain(), "status", OWNER, automation=bot)
        self.assertEqual((s["row"], s["duty_id"]), ("left_off", DUTY))
        self.assertEqual(bot.calls, [["list"], ["disable", DUTY], ["enable", DUTY], ["enable", DUTY]])

    def test_an_unreadable_duty_list_still_answers_the_status(self):
        s = run(Chain(), "status", OWNER, automation=Automation(fail={"list"}))
        self.assertEqual((s["row"], s["earning_usdc"]), ("unknown", 20.0))

    def test_building_transactions_touches_no_duty(self):
        bot = Automation([self.duty()])
        for args in [("supply", OWNER, "1"), ("withdraw", OWNER, "all")]:
            self.assertNotIn("row", run(Chain(), *args, automation=bot))
        self.assertEqual(bot.calls, [])


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
