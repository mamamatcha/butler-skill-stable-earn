# earn-account

Keeps the owner's USDC lent on Aave V3 (Base) on the wallet's Platforms tab: one "Aave" row, keyed by the wallet, at what is lent there now, interest included, with the variable APY and about a week's interest. The stable-earn skill files it after the owner's first supply. Its `scripts/aave.py status`, which the skill runs to confirm every supply and withdrawal, restarts it, so the row updates within seconds. It is the only writer of that row.

## How it is filed

`{"recipe": "earn-account@2", "movesFunds": false, "title": "Aave lending", "triggers": [{"kind": "timer", "intervalSeconds": 900}], "params": {"WALLET": "<user.agentWalletAddress>"}}`. One per owner: a second writes the same row. A duty on `@1` is updated in place with `duty_update {"recipe": "earn-account@2"}`.

## What it does

It checks once when it starts, then on every tick, a random 0 to 60 seconds after the timer fires. Each check reads Base by running `bevo-rpc`: Aave's address provider must name the pinned Pool, and the Pool must name the pinned aToken (aBasUSDC) for USDC, before the wallet's aBasUSDC balance and the reserve's supply rate are read. aBasUSDC is USDC lent plus its interest, one for one, so the balance is the row's value.

| The check reads | The row | Status line |
| --- | --- | --- |
| $0.01 or more lent | set to it: one line, `USDC lent`, with its APY and about a week | `$<value> lent at <apy>%` |
| nothing lent | removed, if there was one | Nothing lent |
| an RPC error, or a contract that is not the pinned one | untouched | Couldn't read Aave |
| `WALLET` is not an address | untouched; no check runs | No wallet address set |

## What it will not do

- **Write 0 for "could not read".** A failed read leaves the row at its last good value.
- **Show an "earned so far".** It cannot tell interest from a later supply, so it never claims one.
- **Follow another venue, chain or token.** USDC on Aave V3 on Base only.
- **Move money.** It makes no `acp` call. It only reads, and removes only its own row.

## Trigger

`{"kind": "timer", "intervalSeconds": 900}`. Between restarts, the row catches up with accrued interest, a change of rate, or a supply or withdrawal made outside the skill, within about 15 minutes.
