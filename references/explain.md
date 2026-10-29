# How Earn works, in plain words

Use this when the owner asks where the yield comes from or what can go wrong.

## Where the yield comes from

- Lenders put USDC into a shared pool and get a receipt back (aUSDC on Aave). The
  receipt's balance grows as interest arrives; that growth is the yield.
- Borrowers post collateral worth more than they borrow (for example $10,000 of ETH to
  borrow up to about $7,500 of USDC) and pay interest into the pool.
- If a borrower's collateral falls too far, it is sold off to repay the loan. That is
  what keeps lenders whole.
- The rate follows demand: the more of the pool is borrowed, the higher the rate.
  Roughly, lender rate = borrow rate × share borrowed × (1 − the venue's cut). A 5% borrow
  rate with 80% borrowed and a 10% cut pays lenders about 3.6%.
- Who borrows: traders using leverage, people looping yield strategies, and people who
  want cash without selling their crypto. Rates are higher when markets are busy.

## Risks to state, briefly

- **Variable rate.** It can fall. Never promise a number.
- **Withdrawal can wait.** If nearly all the pool is lent out, withdrawals wait until
  borrowers repay or new money arrives. The rate jumps when that happens, which
  usually fixes it within hours.
- **Bad debt.** If prices crash faster than collateral can be sold, the pool can take
  a loss.
- **Smart contracts.** No contract is risk-free, however long-running and audited.
  Each venue's own risks are in `references/<venue>.md`.
- **No insurance.** This is not a bank account and has no deposit protection.

## Worked example

"You lend 2,000 USDC at 3.9%. If the rate stays there for a year you'd have about
2,078 USDC. In a week that's roughly $1.50. If borrowing demand drops, so does the rate."

## Words to avoid

"Savings account", "deposit", "guaranteed", "risk-free", "fixed".
