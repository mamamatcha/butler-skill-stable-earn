# Changelog

## 0.4.0

- **The plan is the trading bot's, and the owner reads it as it wrote it.** Moving cash
  to Base is now one same-chain `acp trade` (USDC to USDC on Base), which the trading
  bot plans as a cash move: only what the chain is missing plus fee headroom, never
  taxed, one approval card. Its `--dry-run` `summary` names each move, about what
  arrives, the fees, what Base then holds and the cash left on each chain; step 4
  quotes it as written, with no figure of Butler's own around it. In 0.3.1 the skill
  carried its own source order and fee rules (which already disagreed with the bot's)
  and Butler worked the figures out: Elise's "all but $5" plan read "$7.03 = $2 +
  $5.03 + $4.75" and moved $0.32, under the $2 minimum. On the eval harness the quoted
  plan was right 60 times in 60, against 9 in 20 before.
- **`aave.py quote <ADDRESS> <AMOUNT> <FEE>`** says what the amount earns at today's
  rate, alone and with what is already lent, and how many weeks of that interest the
  fee costs, as lines to quote. Step 3 sizes "keep $Y free" and "half" with a fixed
  `jq` on `cashUsd`, never Butler's arithmetic.
- **A move is filed only after a yes in a later message**, and is called moving cash,
  never a top-up: `acp wallet topup` is the card on-ramp.

- **The Platforms row updates after every supply and withdrawal, not only the first.**
  `scripts/aave.py status` now restarts the owner's live `earn-account@2` duty itself
  (`bevo-automation list`, then `disable` and `enable`), turns it back on if it was
  off, and says how it went in `row`: `restarted`, `turned_on`, `no_duty`,
  `old_recipe`, `pending`, `left_off`, `restart_failed` or `unknown`. In 0.3.1 the restart was step 9's to run, and a model resuming a supply in
  a later turn re-ran `status` and stopped: the row stayed at the first $1 while $17 more
  was lent, and kept $16 after everything was withdrawn, counting it twice. Step 9 now
  acts on `row`. A duty not yet armed is left alone.
- **`cashUsd` is described as bevo-server counts it.** Verified stablecoins at $1, from
  1¢ on Base and $2 or more on any other chain, plus free Hyperliquid USDC of $2 or
  more; a smaller balance is in no total and is never planned with. What "keep $X free"
  leaves can sit on Hyperliquid.

## 0.3.1

- **The Aave Platforms row now appears.** `earn-account@2` reads Base by running
  `bevo-rpc` itself; `@1`'s `bevo.rpc()` call failed on every `eth_call`, so no row
  was written. Step 9 updates an `@1` duty to `@2` in place, and restarts an `@2` one.

## 0.3.0

- **Their lending shows on the wallet's Platforms tab.** New duty template
  `templates/earn-account/` (`earn-account@1`) keeps one "Aave" row: what is lent,
  interest included, with the APY and about a week's interest, read on-chain through
  `bevo.rpc` every 15 minutes and removed once nothing is lent. Step 9 files it after
  the first supply, and step 2 for an owner already lending with none, so an existing
  lender gets the row on their next Earn question. After each later supply or
  withdrawal step 9 restarts it
  (`bevo-automation disable` + `enable`) so it re-reads at once. It only reads; it is
  the one writer of that row. `bevo-automation` joins `requires.bins`.
- **Lends from cash, not only from USDC on Base.** "How much" is now dollars of the
  owner's cash (`cashUsd` from `acp wallet balance --json`: every verified stablecoin on
  every chain, the figure their wallet shows), and the skill never answers "you only
  have X on Base" when they hold more elsewhere. A supply above `wallet_usdc` is topped
  up first with `acp trade` into USDC on the venue's chain: USDT or USDG on Base, then
  USDC, USDT or USDG on Ethereum or Arbitrum, then free Hyperliquid USDC. Cash on other
  chains is named, not moved.
- **The plan is said once, with its fees.** Each top-up leg is previewed with
  `acp trade --dry-run` (a "⚠ Would fail" preview drops that source), and the venue,
  amount, rate and every leg with its fee go in one message before the owner's yes. A
  top-up costing more than about 13 weeks of the moved amount's interest is advised
  against, with an offer to lend only what is already on the venue's chain. A market
  that is closed, paused or at its cap is never topped up for.
- **Top-up legs are sends like any other.** Each has its own key (`<KEY>:topup-<n>`),
  looked up with `--route trade` and never re-sent. `KEY` is now fixed at the owner's
  yes in step 4. Supply waits for every leg to execute and lends the agreed amount or
  what arrived, whichever is less. A refused, failed or declined leg stops the run.
- The procedure is eight steps: plan (3), preview and ask (4) and top up (5) come
  before build (6), send (7) and confirm (8). The preview is a `[FIXED]` step, as every
  money command must be. Withdrawing skips step 5, and its USDC is never swapped back
  unasked.
- The description leads with idle stablecoins, and `earn on my cash`, `earn on usdt`,
  `usdt yield` and `lend usdt` join the keywords. `references/aave.md` has the top-up
  lines to say. `scripts/aave.py` is unchanged: its `not_enough_usdc` stays the last
  check, after the top-up.

## 0.2.0

- **Lending only, found on its own words.** The skill does one job - earn interest on
  idle USDC, check it, take it out - and never routes an owner to another skill or
  compares against one. The description leads with the owner's words for that job,
  since it is all a link-installed skill is chosen by, and the keywords cover how owners
  ask: earning interest, idle money, Aave by name, checking and withdrawing. The
  description carries four asks in owners' own words, one per thing the skill does, and
  "When to use" maps fuller ones to the steps that answer them. A question about which
  product is best gets this venue's live rate and risks, never a ranking. No
  `requires.skills`.
- **A leaner `SKILL.md`** (about 5,100 characters, from 6,500), every safety rule kept:
  the owner-facing lines for adding, withdrawing and "can I get it out today?" moved to
  `references/aave.md`, and "keep $500 free" is spelled out as an amount.
- **Aave is a venue, and its helper is a real script.** The helper moved from a heredoc
  in `SKILL.md`, which the model retyped into `/tmp` on every use, to `scripts/aave.py`,
  installed with the skill and run in place; what is Aave's own (its market, status
  fields, risks and wording) is `references/aave.md`. `SKILL.md`'s steps run
  `scripts/<venue>.py` and send on the `chain_id` it answers with, so a new venue is a
  script, a reference and a table row. Every script answers with the same fields, now
  including `venue` and `chain_id`. `cat` is no longer a required bin. Installing from a
  link needs virtuals-agent with Virtual-Protocol/virtuals-agent#314, which brings the
  files `SKILL.md` names.
- `tests/test_aave.py` checks the script offline, the address book and every chain read
  stubbed: exact `approve`, `supply` and `withdraw` calldata, every refusal, and both
  address cross-checks. CI runs it.
- **The address book is pinned to a commit.** The helper read `AaveV3Base.ts` from
  bgd-labs/aave-address-book's `main`, and only aUSDC was cross-checked, so a change
  upstream could have pointed the owner's `approve` and `supply` at another contract.
  It now reads one commit, and also checks the Pool against the address provider's
  `getPool` on-chain. A new pin is a release.
- An unreadable address book is `book_unavailable` and a call to an address with no
  code is `rpc_unavailable`, not a Python traceback; an unknown command is
  `bad_command` and a malformed address `bad_address`, both before any network read,
  and a missing amount `bad_amount`. `SKILL.md` gives each error, and
  `more_than_earning`, its row.

## 0.1.0

- Lend USDC on Base into Aave V3, show live rate, balance and utilization, and withdraw
  part or all. Exact-amount approvals, address book cross-checked against the Pool.
- The owner's address comes from `bevo-read me`, the read shipped skills already use.
