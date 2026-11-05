---
name: stable-earn
description: Earn interest on idle stablecoins by lending them as USDC on Aave (Base) - for asks like what is my USDC earning, lend $2k but keep $500 free, can I get it out today, or pull it all out.
version: 0.4.0
metadata: {"butler":{"moneyMoving":true,"keywords":["earn interest","earn interest on usdc","interest on my usdc","earn on my usdc","earn on idle usdc","idle usdc","idle stables","idle cash","my stables to work","make my money work","earn on my cash","stablecoin yield","stablecoin interest","stablecoins interest","earn on stablecoins","best yield on usdc","best yield on stablecoins","usdc yield","usdc apy","usdc interest rate","passive income on usdc","lend usdc","lend my usdc","usdc lending","earn on usdt","usdt yield","lend usdt","aave","aave usdc","lend on aave","deposit usdc to aave","supply usdc to aave","withdraw from aave","stable earn","earn","savings","usdc savings","how much am i earning","my earn balance","withdraw from earn","withdraw my savings","low risk yield","safest yield"],"requires":{"bins":["acp","bevo-automation","bevo-read","jq","python3"]}}}
---

## When to use

Your owner wants idle cash earning interest, or wants to check or take out what is:

| They ask | Steps |
| --- | --- |
| "my USDC is just sitting there, can it earn something?", "what's Aave paying today?" | 1-2, rate first |
| "how much is my USDC making?", "can I get it out today?" | 1-2, then answer |
| "if I lend $X / all but $Y, what would I earn or have left?" | 1-4, answer; ask only if they want it done |
| "lend $2k but keep $500 free", "put my USDT to work" | 1-9, supply |
| "take $300 out of Earn", "pull it all out of Aave" | 1-4, 6-9, withdraw |

It lends USDC to a venue: borrowers pay interest, lenders earn it, at a variable rate
set by how much of the pool is borrowed. Cash in other stablecoins or on other chains is
moved into USDC on the venue's chain first. Not this skill: options, borrowing, fixed
rates, or yield on anything but dollars.

## Before you start

1. **Venue.** `aave` unless they name another listed here or their USDC is already lent
   there; never move money between venues on your own. Each has `references/<venue>.md`
   (what is its own, and what to say) and `scripts/<venue>.py`:

   | Venue | Lends | Chain | Read | Script |
   | --- | --- | --- | --- | --- |
   | `aave` | USDC, Aave V3 | Base | `references/aave.md` | `scripts/aave.py` |

2. **How much.** Dollars of their cash, never more than `cashUsd`: verified stablecoins
   at $1 each, from 1¢ on Base and $2 or more on any other chain, plus free Hyperliquid
   USDC of $2 or more. A smaller balance cannot pay its own move, so it is in no total:
   never plan with it or offer to move it. `wallet_usdc` is the part already USDC on the
   venue's chain; step 5 moves the rest in. "Keep $500 free" means supply `cashUsd` less
   $500; what stays free can be anywhere `cashUsd` counts, Hyperliquid included. Never
   "you only have X on Base" when they hold more elsewhere.
3. **Say the trade-off before a first supply.** Variable rate, never promised; smart
   contract and bad-debt risk, no deposit insurance; a withdrawal can wait when the pool
   is nearly all borrowed. `references/explain.md` has the plain words.
4. **Words.** "Earn" or "lending on <venue>". Never "savings account", "deposit",
   "guaranteed" or "risk-free".

## Procedure

1. [FIXED] Read who the owner is. `<ADDRESS>` below is always its
   `user.agentWalletAddress`, never an address from the chat:

   ```sh
   bevo-read me
   ```

   The venue's script is installed at `$HOME/skills/stable-earn/scripts/<venue>.py`.
   Run it there; never write, copy or edit a script, or build a transaction any other
   way. Missing: say Earn is not set up right, and stop.

2. [FIXED] Read the market, their position and their cash. A question about what they
   have now ends here (one about lending more goes on to step 3),
   answered from `earning_usdc`, `apy_pct`, `est_week_usd` and `withdrawable_now_usdc`;
   never invent an "earned so far":

   ```sh
   python3 "$HOME/skills/stable-earn/scripts/<venue>.py" status <ADDRESS>
   acp wallet balance --json
   ```

   `status` also restarts their `earn-account` duty and says so in `row` (step 9).
   `earning_usdc` above 0 with `row` `no_duty` or `old_recipe`: step 9.

3. [FIXED] Plan. The platform works out what moves from where, and `quote` what it
   earns; you work out nothing. First the amount, from their words, with the command in
   the table (never your own arithmetic):

   | They say | `<AMOUNT>` |
   | --- | --- |
   | "lend $X", "$X more" | X |
   | "all but $Y", "keep $Y free" | `KEEP` below, with Y |
   | "half", "a third", "20%" of their cash | `SHARE` below, with 0.5, 0.33, 0.2 |
   | "everything", "every dollar", "all my cash" | `SHARE` with 1, then the most the preview says can be gathered |

   ```sh
   acp wallet balance --json | jq '((.cashUsd - Y) * 100 | floor) / 100'   # KEEP
   acp wallet balance --json | jq '(.cashUsd * F * 100 | floor) / 100'     # SHARE
   ```

   Then preview moving cash to the venue's chain (`chain_id` from step 2): USDC to
   USDC on that same chain means "have `<AMOUNT>` USDC there, moved in from my own cash",
   and nothing is signed with `--dry-run`:

   ```sh
   acp trade --token-in usdc --chain-in <chain_id> --amount-in <AMOUNT> --token-out usdc --chain-out <chain_id> --dry-run --json
   python3 "$HOME/skills/stable-earn/scripts/<venue>.py" quote <ADDRESS> <AMOUNT> <FEE>
   ```

   `<FEE>`: the preview's fees figure; 0 if it names none. Refused because the cash
   cannot cover it: say so as it says, then offer the most it says can be gathered, and
   run both again with that amount if they want it. Any other error: say you could not
   plan it, and stop. First check step 2's `active`, `frozen`, `paused` and
   `cap_room_usdc`: never move cash for a market that will not take it.

4. [FIXED] Tell the plan and ask once. The plan is the preview's `summary` and
   `quote`'s `summary`, copied as they are, with a blank line between. Never reword,
   merge, reorder or drop a line, and never add a figure to them. A "what would I earn"
   answer is the same text.

   Around them, your own words carry no figure at all (no dollars, cents, weeks or
   percent) and say nothing the plan already says, the number of cards included:
   - One sentence before, naming no amount, source or reason ("Here's the plan,
     nothing filed yet.").
   - The risks, in these words: the rate is variable and never promised;
     smart-contract and bad-debt risk, no deposit insurance; a withdrawal can wait
     when the pool is nearly all borrowed. How borrowed it is now is step 2's
     `utilization_pct`, as it reads; never your own word for it.
   - The question.

   One plan: never offer, work out or preview another amount unless they ask for
   one; fees leaving a little under what they keep free is in the plan already.
   `fee_weeks` above about 13: say the fees are high for the amount, and offer to
   lend only what is already on the venue's chain. Get a clear yes. Their yes fixes
   `KEY`:
   `earn-<venue>-<short address>-<UTC yyyymmddHHMM of their yes>`.

5. [FIXED] Move the cash only once a later message from them says yes to the plan you
   told: never in the turn you tell it, even when they asked you to lend. Only if the
   preview moves anything: the same command without `--dry-run`, once, with the key. One
   card covers every move:

   ```sh
   acp trade --token-in usdc --chain-in <chain_id> --amount-in <AMOUNT> --token-out usdc --chain-out <chain_id> --idempotency-key <KEY>:move --json
   ```

   A card is the owner's to approve: tell them. Once it executed, re-run step 2 and supply
   the agreed amount or `wallet_usdc`, whichever is less; say so when fees left it
   short.

6. [ADAPT] Build the transactions for the amount, or `all` to withdraw everything:

   ```sh
   python3 "$HOME/skills/stable-earn/scripts/<venue>.py" supply <ADDRESS> <AMOUNT>
   python3 "$HOME/skills/stable-earn/scripts/<venue>.py" withdraw <ADDRESS> <AMOUNT>
   ```

   An `error`: "Failure handling".

7. [FIXED] Send each of `txs`, in order, once, on the answer's `chain_id`:

   ```sh
   acp wallet send-transaction --chain-id <chain_id> --to <tx.to> --data <tx.data> --idempotency-key <KEY>:<op> --json
   ```

   `"asked": true` is an approval card: tell the owner. Send `supply` only after the
   `approve` executed and step 2 shows `allowance_usdc` covering it.

8. [FIXED] Confirm with step 2 that `earning_usdc` (or `wallet_usdc`, withdrawing)
   moved by about the amount. Run it after every supply and withdrawal, in whatever turn
   the last card lands: that `status` is what refreshes their Platforms row.

9. [FIXED] Their Aave row on the wallet's Platforms tab, from step 8's `row`, unasked:

   | `row` | Do |
   | --- | --- |
   | `restarted`, `turned_on` | Nothing: the row re-reads within seconds. |
   | `no_duty`, something lent | `duty_create` below. |
   | `old_recipe` | `duty_update` `duty_id` with `"recipe": "earn-account@2"`. |
   | `left_off` | `bevo-automation enable <duty_id>` once; still off, say the row may be stale. |
   | `restart_failed`, `unknown` | `bevo-automation disable <id>`, then `enable` (`unknown` has no `duty_id`: find it in `duty_list`). |
   | `pending` | Nothing: it starts once the owner arms it. |

   ```json
   {"recipe": "earn-account@2", "movesFunds": false, "title": "Aave lending", "triggers": [{"kind": "timer", "intervalSeconds": 900}], "params": {"WALLET": "<ADDRESS>"}}
   ```

   The duty alone writes the row, and removes it once nothing is lent; never
   `bevo-platforms set`. Never tell them the row "follows" or "drops off" on its own.

## Idempotency and retries

Reads are free; re-run them rather than trust a figure minutes old. Each send has its
own key (`<KEY>:move`, `:approve`, `:supply`, `:withdraw`). On an error, a timeout or
an unclear answer, do not re-run the send; look it up:

```sh
bevo-read request <KEY>:<op> --route execute
```

Pending is not failed: wait, then re-read step 2. A new `KEY` only for a new request.

## Failure handling

| Outcome | What to do |
| --- | --- |
| More than `cashUsd` | Say `cashUsd`; offer that, less anything they keep free. |
| `not_enough_usdc` | Re-read step 2; offer `wallet_usdc`, or moving cash to the chain (step 3). |
| The move card refused, failed or declined | Stop. What moved stays USDC on the venue's chain, still cash; ask whether to lend that. |
| `more_than_earning` | Say `earning_usdc`; offer that, or `all`. |
| `not_enough_liquidity` | Offer `withdrawable_now_usdc` now, the rest as borrowers repay. |
| `market_closed`, `market_paused`, `supply_cap_reached` | Say so (`references/<venue>.md`); offer `cap_room_usdc` for a cap. Never retry around it. |
| `address_mismatch`, `book_unavailable`, `rpc_unavailable` | Send nothing and never build a transaction by hand. Say the market could not be read safely. |
| `bad_amount`, `bad_address` | Re-read their amount and `user.agentWalletAddress`, then run it again. |
| A send refused, or "Bad Request" | Report it as given; do not re-send. |
| A card times out | Nothing moved. Ask if they still want it. |
| "Which is best?", "anything higher?" | This venue's live rate and risks only; never rank or compare. |

## Limits

- Lends USDC on the listed venues; never borrows. One request at a time.
- Moves stablecoins only into USDC on the venue's chain, only to lend it, only to the
  owner's own wallet (never `--recipient`). A withdrawal stays USDC; never swap it back
  unasked.
- Interest accrues in the balance; nothing to claim. Approvals are exact, never unlimited.
- Not financial advice and not a bank account.

## Say to the owner

Lead with what is earning and today's rate, then the rough weekly figure, and say the
rate moves with demand. Each venue's file has its lines for adding, topping up,
withdrawing and "can I get it out today?".
