# stable-earn

The `stable-earn` skill for [Butler](https://github.com/Virtual-Protocol/butler-skills):
earning interest on idle stablecoins. It lends USDC on Base into Aave V3, topping it up
from the owner's other stablecoins and chains first, shows what is earning, and
withdraws it, and keeps an "Aave" row on the wallet's Platforms tab. This README is for the people maintaining the repo. A butler receives `SKILL.md` and the
`references/*.md` and `scripts/*.py` files it names.

- **Version:** 0.3.1 (`SKILL.md`). What changed in each release: `CHANGELOG.md`.
- **Name:** `stable-earn`, listed in the skill hub with its duty template
  `earn-account` (`templates/earn-account/`). It requires no other skill.

## What it does

- **Lending.** Supplies an amount of the owner's USDC to a lending venue, shows the live
  rate and what they have lent, and withdraws part or all of it.
- **Lending from cash.** The amount is sized against the owner's cash (`cashUsd`:
  every verified stablecoin on every chain, the figure their wallet shows), not only
  USDC on the venue's chain. What the chain is missing is moved in first by one
  same-chain `acp trade` (USDC to USDC on Base), which the trading bot plans as a cash
  move: which balances, how much from each, fees and minimums are its, not the skill's.
  Its `--dry-run` summary says the plan in lines the skill quotes as written, and
  `aave.py quote` says what the amount earns; a move costing more than about 13 weeks
  of the new amount's interest is advised against.
- **Tracking.** After a supply or withdrawal, the `earn-account` duty keeps one "Aave"
  row on the wallet's Platforms tab: what is lent, interest included, the APY and about
  a week's interest, re-read every 15 minutes and removed once nothing is lent. The
  skill files it after the first supply (or on the first read that finds USDC already
  lent) and restarts it after each later move, so the row updates at once.

Not covered: borrowing, options, lending anything but USDC, cash on chains `acp trade`
does not reach (Solana, NEAR), fixed-rate products, and
sweeping idle cash on a schedule. It never sends an owner to another skill or compares
against one: a question about selling puts is that skill's to be found for.

## Discovery

What decides whether a butler uses this skill, so change it deliberately:

- **Installed from a link**, the model chooses from `<available_skills>`, which shows
  only `name` and `description` (at most 200 characters, the registry's cap). The
  description leads with the job, *earn interest on idle stablecoins by lending them as
  USDC on Aave (Base)*, then four asks in an owner's own words, one per thing the skill does: *what
  is my USDC earning*, *lend $2k but keep $500 free*, *can I get it out today*, *pull it
  all out*. "When to use" maps fuller asks to the steps that answer them.
- **Listed in the hub**, `hub_search` offers a skill only when a query names it or hits
  one of its `keywords`; description words only rank. The keywords cover the ways
  owners ask: earning interest (`earn interest on usdc`, `usdc apy`, `stablecoin
  yield`, `usdt yield`), idle money (`idle usdc`, `my stables to work`, `earn on my
  cash`), Aave by name (`aave`,
  `lend on aave`, `withdraw from aave`), and checking or leaving (`how much am i
  earning`, `withdraw from earn`). `trade`, `buy`, `sell`, `token` and `crypto` count
  for nothing there, so none are used.
- `earn on my usdc`, `make my money work` and `idle cash` are also `options-trading`
  keywords. Both skills are offered for them, and each says what it does.

## Venues

| | Aave |
| --- | --- |
| Lends | USDC, Aave V3 |
| Chain | Base (`8453`) |
| Getting out | any time the pool has cash; near 100% utilization it waits |
| Script | `scripts/aave.py` |
| What differs | `references/aave.md` |

Aave is used unless the owner names another venue or already lends there.

## Installing

Send the butler, in chat:

```text
Install this skill: https://github.com/mamamatcha/butler-skill-stable-earn/blob/main/SKILL.md
```

The link install (`hub_install_url`) writes `SKILL.md` and every `references/*.md` and
`scripts/*.py` it names, from the same ref; a named file missing from the repo refuses
the install. That needs virtuals-agent with Virtual-Protocol/virtuals-agent#314: an
older agent installs `SKILL.md` alone, and step 1 then stops rather than run without
its script. Send the line again to update; to switch to another repo or fork,
`hub_remove stable-earn` first.

Once the hub lists it, the butler installs it from the hub by name. Either way, step 9
files `earn-account@2` from the hub's index, so the Platforms row needs the template
listed in butler-skills.

## How the pieces fit

| Piece | Where | Does |
| --- | --- | --- |
| Who the owner is | `bevo-read me` | `user.agentWalletAddress`, the wallet that sends and receives. Never an address from the chat. |
| Reads and calldata | `scripts/<venue>.py`, run in place with `python3 "$HOME/skills/stable-earn/scripts/<venue>.py"` | Keyless and read-only. Aave's takes the Pool, USDC, aUSDC and address-provider addresses from Aave's address book at a pinned commit, checks them on-chain, reads rate, utilization, balances, allowance, reserve flags and supply cap over public Base RPC, and builds `approve`, `supply` or `withdraw` calldata. It never sends. |
| Cash | `acp wallet balance --json` | `cashUsd`, from which a fixed `jq` sizes "keep $Y free" and "half". |
| Moving cash | `acp trade --token-in usdc --chain-in <chain_id> --amount-in <n> --token-out usdc --chain-out <chain_id>`, first with `--dry-run --json`, then with `--idempotency-key <KEY>:move --json` | "Have n USDC on the venue's chain": the trading bot's cash move (only what is missing plus fee headroom, never taxed, one card), to the owner's own wallet. Its dry-run `summary` is the plan. |
| Earnings | `scripts/<venue>.py quote <ADDRESS> <AMOUNT> <FEE>` | What the amount earns at today's rate, alone and with what is already lent, and how many weeks of it the fee costs, as lines to quote. |
| Sending | `acp wallet send-transaction --chain-id <chain_id> ... --idempotency-key <KEY>:<op> --json` | One approval card per transaction, on the chain the helper names. `asked: true` means a card is up. |
| Outcome | `bevo-read request <KEY>:<op> --route execute` | Whether a send executed. A retry is always this lookup, never a second send. |
| Platforms row | `templates/earn-account/`, filed with `duty_create {"recipe": "earn-account@2", ...}`, restarted with `bevo-automation disable` + `enable` | A read-only duty: checks once as it starts and every 15 minutes, reading the position on Base through `bevo-rpc`, and writes or removes the one "Aave" row. The only writer of that row. |

## Safety model

- **The contracts come from a pinned source and are checked on-chain.** The address book
  (`bgd-labs/aave-address-book`, `src/ts/AaveV3Base.ts`) is read at one commit, so a
  change upstream cannot move what the owner approves. The Pool must equal the address
  provider's `getPool`, and aUSDC the Pool's own `getReserveData`, or nothing is built
  (`address_mismatch`). The `earn-account` duty cannot fetch the book, so it pins the
  same four addresses, checks them on-chain the same way every run, and only reads.
- **Exact approvals.** `approve` is for the amount being supplied, never unlimited, and
  is skipped when the allowance already covers it.
- **Money only goes to the owner.** `supply` credits `onBehalfOf` the owner, and
  `withdraw` pays `to` the owner. Both are the `bevo-read me` address, which the helper
  checks is a 20-byte address before it goes into any calldata.
- **Every amount is checked before building.** Against wallet USDC, the supply cap, the
  reserve's active, frozen and paused flags, what is lent, and the pool's cash for a
  withdrawal. A refused build is an `error`, never a partial `txs`.
- **One key per transaction, never re-sent.** The owner approves each card in the app,
  and `supply` is sent only after `status` shows the allowance landed.
- **Moving cash only feeds the lend.** It moves the owner's cash into USDC on the
  venue's chain, to their own wallet (`--recipient` is never passed), only after a yes
  to the plan with its moves and fees in front of them, and never for a market that is
  closed or at its cap. A refused, failed or declined card stops the run; what moved is
  still USDC in their wallet. A withdrawal is never swapped back.
- **No secrets.** Nothing here signs: Butler's server signs with the owner's wallet after
  the owner approves the card.

What it does not protect against, so review knows: the public RPCs are trusted for
figures (a lying node can misstate a balance or rate, but cannot change where a
transaction goes). The approval card's "Lend 5 USDC on Aave" title comes from
bevo-server decoding the calldata against Aave's Pool (Virtual-Protocol/bevo-server#1452);
a server without it shows "Sign transaction".

## Testing the helper

`tests/` runs offline in CI (`python3 -m unittest discover -s tests`), and so does the
duty's (`python3 -m unittest discover -s templates/earn-account/tests`). Against mainnet,
with any Base address that holds some USDC (the burn address does):

```sh
python3 scripts/aave.py status <ADDRESS>
python3 scripts/aave.py supply <ADDRESS> 10
python3 scripts/aave.py withdraw <ADDRESS> all
```

Check by hand after any change to the helper:

- `status` has no `error`, and `pool`, `usdc` and `ausdc` are Aave V3 Base's Pool, native
  USDC and aBasUSDC.
- `supply` builds `approve` then `supply` with no allowance, and `supply` alone with one.
  Over the wallet is `not_enough_usdc`.
- `withdraw all` builds one `withdraw` for everything lent; more than lent is
  `more_than_earning`.
- A missing or negative amount is `bad_amount`, a bad address `bad_address`, an unknown
  command `bad_command`, each with no network read.

### Moving the pin

The pin is the commit in `BOOK`, in `scripts/aave.py`. To move it, take the latest commit to
`src/ts/AaveV3Base.ts` in `bgd-labs/aave-address-book`, read that file's `POOL`,
`POOL_ADDRESSES_PROVIDER` and `USDC` block, check them against Aave's own docs, run the
checks above, and release it as a new version.

## Validating a change

```sh
curl -sSLO https://virtual-protocol.github.io/butler-skills/tools/validate.py
python3 validate.py --standalone .
```

CI runs the same. The validator refuses a `SKILL.md` body over 12,000 characters, so new
detail goes into a reference file with a pointer to it in `SKILL.md`.

## Releasing

1. Bump `version` in `SKILL.md` and add the `CHANGELOG.md` entry.
2. A change to `templates/earn-account/` bumps `version` in its `recipe.json` (and the
   `earn-account@<n>` in step 9), with its own `CHANGELOG.md` entry.
3. Merge to `main` with a merge commit, and tag `vX.Y.Z`. The hub lists the skill and
   the template at that tag, so moving to it is a `ref` change in butler-skills.

## Adding a venue

Everything about earning on stablecoins lands here, not in a new repo. A venue is two
files and a row; `SKILL.md`'s steps do not change:

1. **`scripts/<venue>.py`**: standard library only, taking `status <ADDRESS>`,
   `supply <ADDRESS> <AMOUNT>` and `withdraw <ADDRESS> <AMOUNT|all>`, and printing one
   JSON object with the shared fields in `aave.md`: `venue`, `chain_id`, `apy_pct`, `wallet_usdc`, `earning_usdc`,
   `withdrawable_now_usdc`, `allowance_usdc`, `est_week_usd`, and `txs` (each
   `{op, to, data}`, in send order) or `error`. Errors `SKILL.md` already handles keep
   their names; a new one gets its row in `<venue>.md`. Addresses come from a pinned
   source and are checked on-chain, as Aave's are, never written in the file.
2. **`references/<venue>.md`**: only what differs, as `aave.md`: the market, what its
   status fields mean, its risks, and its "Say to the owner" lines.
3. **A row** in `SKILL.md`'s venue table (Before you start), and in this README's.

A sweep duty is a `templates/<name>/`.

Planned:

- A server-side `acp earn deposit|withdraw|account --venue <venue>` command, so the owner
  approves one card that says what it does, reads go through Butler's server rather than
  public RPC, and no helper is written at all.
- A sweep duty that lends idle USDC above a floor and withdraws in time when a trade or
  duty needs cash.
- Morpho vaults (ERC-4626 `deposit`/`redeem`) as a second venue.

## Layout

```
SKILL.md              the procedure a butler follows
scripts/
  aave.py             Aave's read and calldata script
tests/
  test_aave.py        offline checks of the script
templates/
  earn-account/       the duty that keeps the Aave Platforms row (recipe.json, duty.py, tests/)
references/
  aave.md             what is Aave's own: the market, its status, its risks
  explain.md          how lending works and its risks, in plain words
```
