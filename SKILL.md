---
name: stable-earn
description: Earn interest on idle USDC by lending it on Aave (Base) - for asks like what is my USDC earning, lend $2k but keep $500 free, can I get it out today, or pull it all out.
version: 0.2.0
metadata: {"butler":{"moneyMoving":true,"keywords":["earn interest","earn interest on usdc","interest on my usdc","earn on my usdc","earn on idle usdc","idle usdc","idle stables","idle cash","my stables to work","make my money work","stablecoin yield","stablecoin interest","stablecoins interest","earn on stablecoins","best yield on usdc","best yield on stablecoins","usdc yield","usdc apy","usdc interest rate","passive income on usdc","lend usdc","lend my usdc","usdc lending","aave","aave usdc","lend on aave","deposit usdc to aave","supply usdc to aave","withdraw from aave","stable earn","earn","savings","usdc savings","how much am i earning","my earn balance","withdraw from earn","withdraw my savings","low risk yield","safest yield"],"requires":{"bins":["acp","bevo-read","python3"]}}}
---

## When to use

Your owner wants idle USDC earning interest, or wants to check or take out what is:

| They ask | Steps |
| --- | --- |
| "my USDC is just sitting there, can it earn something?", "what's Aave paying today?" | 1-2, rate first |
| "how much is my USDC making?", "can I get it out today?" | 1-2, then answer |
| "lend $2k but keep $500 free", "put $300 more in" | 1-5, supply |
| "take $300 out of Earn", "pull it all out of Aave" | 1-5, withdraw |

It lends USDC to a venue: borrowers pay interest, lenders earn it, at a variable rate
set by how much of the pool is borrowed. Not this skill: options, borrowing,
fixed rates, or yield on anything but dollars.

## Before you start

1. **Venue.** `aave` unless they name another listed here or their USDC is already lent
   there; never move money between venues on your own. Each has `references/<venue>.md`
   (what is its own, and what to say) and `scripts/<venue>.py`:

   | Venue | Lends | Chain | Read | Script |
   | --- | --- | --- | --- | --- |
   | `aave` | USDC, Aave V3 | Base | `references/aave.md` | `scripts/aave.py` |

2. **How much.** Dollars of USDC on the venue's chain, never more than they hold. "Keep
   $500 free" means supply what they hold less $500.
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

2. [FIXED] Read the market and their position. A question ends here, answered from
   `earning_usdc`, `apy_pct`, `est_week_usd` and `withdrawable_now_usdc`; never invent
   an "earned so far":

   ```sh
   python3 "$HOME/skills/stable-earn/scripts/<venue>.py" status <ADDRESS>
   ```

3. [ADAPT] Build the transactions for the agreed amount, or `all` to withdraw
   everything:

   ```sh
   python3 "$HOME/skills/stable-earn/scripts/<venue>.py" supply <ADDRESS> <AMOUNT>
   python3 "$HOME/skills/stable-earn/scripts/<venue>.py" withdraw <ADDRESS> <AMOUNT>
   ```

   An `error`: "Failure handling". Otherwise say the venue, chain, amount and
   `apy_pct` (variable) in one line and get a clear yes.

4. [FIXED] Send each of `txs`, in order, once, on the answer's `chain_id`. `KEY` is
   `earn-<venue>-<short address>-<UTC yyyymmddHHMM of their yes>`:

   ```sh
   acp wallet send-transaction --chain-id <chain_id> --to <tx.to> --data <tx.data> --idempotency-key <KEY>:<op> --json
   ```

   `"asked": true` is an approval card: tell the owner. Send `supply` only after the
   `approve` executed and step 2 shows `allowance_usdc` covering it.

5. [FIXED] Confirm with step 2 that `earning_usdc` (or `wallet_usdc`, withdrawing)
   moved by about the amount.

## Idempotency and retries

Reads are free; re-run them rather than trust a figure minutes old. Each send has its
own key (`<KEY>:approve`, `:supply`, `:withdraw`). On an error, a timeout or an unclear
answer, do not re-run the send; look it up:

```sh
bevo-read request <KEY>:<op> --route execute
```

Pending is not failed: wait, then re-read step 2. A new `KEY` only for a new request.

## Failure handling

| Outcome | What to do |
| --- | --- |
| `not_enough_usdc` | Say what they hold on that chain; offer that, or bridging or swapping in first. |
| `more_than_earning` | Say `earning_usdc`; offer that, or `all`. |
| `not_enough_liquidity` | Offer `withdrawable_now_usdc` now, the rest as borrowers repay. |
| `market_closed`, `market_paused`, `supply_cap_reached` | Say so (`references/<venue>.md`); offer `cap_room_usdc` for a cap. Never retry around it. |
| `address_mismatch`, `book_unavailable`, `rpc_unavailable` | Send nothing and never build a transaction by hand. Say the market could not be read safely. |
| `bad_amount`, `bad_address` | Re-read their amount and `user.agentWalletAddress`, then run it again. |
| A send refused, or "Bad Request" | Report it as given; do not re-send. |
| A card times out | Nothing moved. Ask if they still want it. |
| "Which is best?", "anything higher?" | This venue's live rate and risks only; never rank or compare. |

## Limits

- USDC on the listed venues only; never borrows. One request at a time.
- Interest accrues in the balance; nothing to claim. Approvals are exact, never unlimited.
- Not financial advice and not a bank account.

## Say to the owner

Lead with what is earning and today's rate, then the rough weekly figure, and say the
rate moves with demand. Each venue's file has its lines for adding, withdrawing and
"can I get it out today?".
