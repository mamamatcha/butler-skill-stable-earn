---
name: stable-earn
description: Earn interest on idle stablecoins by lending them as USDC on Aave (Base) - for asks like what is my USDC earning, lend $2k but keep $500 free, can I get it out today, or pull it all out.
version: 0.3.1
metadata: {"butler":{"moneyMoving":true,"keywords":["earn interest","earn interest on usdc","interest on my usdc","earn on my usdc","earn on idle usdc","idle usdc","idle stables","idle cash","my stables to work","make my money work","earn on my cash","stablecoin yield","stablecoin interest","stablecoins interest","earn on stablecoins","best yield on usdc","best yield on stablecoins","usdc yield","usdc apy","usdc interest rate","passive income on usdc","lend usdc","lend my usdc","usdc lending","earn on usdt","usdt yield","lend usdt","aave","aave usdc","lend on aave","deposit usdc to aave","supply usdc to aave","withdraw from aave","stable earn","earn","savings","usdc savings","how much am i earning","my earn balance","withdraw from earn","withdraw my savings","low risk yield","safest yield"],"requires":{"bins":["acp","bevo-automation","bevo-read","python3"]}}}
---

## When to use

Your owner wants idle cash earning interest, or wants to check or take out what is:

| They ask | Steps |
| --- | --- |
| "my USDC is just sitting there, can it earn something?", "what's Aave paying today?" | 1-2, rate first |
| "how much is my USDC making?", "can I get it out today?" | 1-2, then answer |
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

2. **How much.** Dollars of their cash, never more than `cashUsd`: every verified
   stablecoin on every chain. `wallet_usdc` is the part already USDC on the venue's
   chain; step 5 moves the rest in. "Keep $500 free" means supply `cashUsd` less $500.
   Never "you only have X on Base" when they hold more elsewhere.
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

2. [FIXED] Read the market, their position and their cash. A question ends here,
   answered from `earning_usdc`, `apy_pct`, `est_week_usd` and `withdrawable_now_usdc`;
   never invent an "earned so far":

   ```sh
   python3 "$HOME/skills/stable-earn/scripts/<venue>.py" status <ADDRESS>
   acp wallet balance --json
   ```

   `earning_usdc` above 0 and no `earn-account` duty in `duty_list`, or one on `@1`: step 9.

3. [ADAPT] Plan. Supplying more than `wallet_usdc` needs a top-up:
   - Sources, in order: `spot.tokens` rows with `symbol` USDC, USDT or USDG, `verified`
     true and no `hidden`, on Base (8453), then Ethereum (1) or Arbitrum (42161), the
     fewest and largest first; last, free USDC on Hyperliquid (1337, `acp trade
     hl-status`), never margin an open position holds. Cash on any other chain is not
     moved: say it is there.
   - First check step 2's `active`, `frozen`, `paused` and `cap_room_usdc`: never top
     up for a market that will not take it.

   With no top-up, build now (step 6) so an `error` shows before asking.

4. [FIXED] Preview each top-up leg (nothing is sent; a `summary` reading "⚠ Would
   fail" drops that source), then ask once:

   ```sh
   acp trade --token-in <symbol> --chain-in <chain> --amount-in <AMOUNT> --token-out usdc --chain-out <chain_id> --dry-run --json
   ```

   Fees above about 13 weeks of the moved amount's interest (`amount × apy_pct / 5200`
   a week): say so, and offer to lend only `wallet_usdc`. In one message say the venue,
   chain, amount, `apy_pct` (variable) and each leg with its fee, and get a clear yes.
   Their yes fixes `KEY`: `earn-<venue>-<short address>-<UTC yyyymmddHHMM of their yes>`.

5. [FIXED] Top up, only the legs agreed in step 4, in order, once each:

   ```sh
   acp trade --token-in <symbol> --chain-in <chain> --amount-in <AMOUNT> --token-out usdc --chain-out <chain_id> --idempotency-key <KEY>:topup-<n> --json
   ```

   A card is the owner's to approve: tell them. Wait until each leg executed (see
   "Idempotency"), then re-run step 2 and supply the agreed amount or `wallet_usdc`,
   whichever is less; say so when fees left it short.

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
   moved by about the amount.

9. [FIXED] Once it moved, unasked, update their Aave row on the wallet's Platforms tab.
   With no `earn-account` duty in `duty_list` and something lent, `duty_create`:

   ```json
   {"recipe": "earn-account@2", "movesFunds": false, "title": "Aave lending", "triggers": [{"kind": "timer", "intervalSeconds": 900}], "params": {"WALLET": "<ADDRESS>"}}
   ```

   With one on `@1`, `duty_update` it with this recipe. With one on `@2`, restart it; it
   re-reads the position as it starts:

   ```sh
   bevo-automation disable <id>
   bevo-automation enable <id>
   ```

   It alone writes the row, and removes it once nothing is lent; never `bevo-platforms set`.

## Idempotency and retries

Reads are free; re-run them rather than trust a figure minutes old. Each send has its
own key (`<KEY>:topup-1`, `:approve`, `:supply`, `:withdraw`). On an error, a timeout or
an unclear answer, do not re-run the send; look it up (`--route trade` for a top-up):

```sh
bevo-read request <KEY>:<op> --route execute
```

Pending is not failed: wait, then re-read step 2. A new `KEY` only for a new request.

## Failure handling

| Outcome | What to do |
| --- | --- |
| More than `cashUsd` | Say `cashUsd`; offer that, less anything they keep free. |
| `not_enough_usdc` | Re-read step 2; offer `wallet_usdc`, or a top-up (step 3). |
| A top-up leg refused, failed or declined | Stop. What moved stays USDC on the venue's chain, still cash; ask whether to lend that. |
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
