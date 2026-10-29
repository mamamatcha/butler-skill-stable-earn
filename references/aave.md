# Aave: what is different

Everything in `SKILL.md` holds on Aave. This file is only what is Aave's own. `aave` is
the default venue: use it unless the owner names another venue this skill lists, or the
USDC they mean is already lent there.

## The market

Aave V3's USDC market on **Base** (chain `8453`), native USDC only. Lenders get aUSDC,
whose balance grows every block as interest arrives: nothing to claim, nothing locked.
The rate is variable, set by how much of the pool is borrowed, and moves block by block.

Reads and calldata come from `scripts/aave.py`, installed with this skill. Add money is
`approve` (exact amount, skipped when the allowance covers it) then `supply`; take it out
is one `withdraw`, an amount or `all`.

## What the script answers

Every venue's script answers with these:

| Field | Means |
| --- | --- |
| `venue`, `chain_id` | `aave`, and `8453` (Base): the chain step 4 sends on |
| `apy_pct` | what lenders earn now, variable |
| `wallet_usdc`, `earning_usdc` | USDC on Base in the wallet, and lent on Aave |
| `withdrawable_now_usdc` | what can come out right now, given the pool's cash |
| `allowance_usdc` | what the Pool may already take from the wallet |
| `est_week_usd` | a week at today's rate on what is lent; never an "earned so far" |
| `txs` | `supply` / `withdraw` only: the transactions to send, in order |
| `error` | why nothing was built; `SKILL.md` "Failure handling" |

Aave's own: `utilization_pct`, the share of the pool lent out, and `active`, `frozen`,
`paused` and `cap_room_usdc`, below.

The script reads Aave's address book at one pinned commit, never a branch, so nobody
can change which contracts the owner approves. It checks the Pool against the address
provider's `getPool` and aUSDC against the Pool's own `getReserveData` before any figure
is trusted; a mismatch is `address_mismatch`.

## Reading the status

- `utilization_pct` near 100: nearly the whole pool is lent out. A withdrawal can take
  only `withdrawable_now_usdc` until borrowers repay or new money arrives. The rate
  jumps when that happens, which usually clears it within hours. Say so before a
  supply, not only when a withdrawal is short.
- `frozen`: Aave governance stopped new supply. Withdrawing still works.
- `paused`: nothing moves, in or out, until governance unpauses it.
- `cap_room_usdc`: how much more the market takes before its supply cap. `null` is no
  cap.

## Risks, Aave's words

- **Bad debt.** Every loan is backed by more collateral than it borrows, and is
  liquidated when that cushion runs thin. If prices crash faster than liquidations can
  run, the pool can take a loss, and lenders share it.
- **Smart contracts and price feeds.** Long-running and audited, never risk-free.
- **USDC itself.** aUSDC is only as good as the USDC under it.

## Say to the owner

"Lend 2,000 USDC on Aave (Base) at about 3.9% today, variable. You can take it out
whenever the pool has room."

When `utilization_pct` is high: "Almost all of Aave's USDC is lent out right now, so a
large withdrawal could wait a few hours. Rates are higher while that lasts."

After adding: "Done: 2,000 USDC is now earning about 3.9% (variable) on Aave. That's
roughly $1.50 a week at today's rate. Say 'withdraw from Earn' anytime."

After withdrawing: "500 USDC is back in your wallet. 1,500 USDC is still earning."

Asked "can I get it out today?": answer from `withdrawable_now_usdc` against
`earning_usdc`. All of it: "Yes, all 2,000 can come out now." Not all: "1,200 can come
out right now; the rest as borrowers repay, usually within hours."
