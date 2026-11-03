# Changelog

## 2

- Reads Base by running `bevo-rpc` itself. `@1` called `bevo.rpc()`, which cannot
  parse an `eth_call` result (`bevo-rpc` prints it as a bare JSON string, and the SDK
  accepts only a JSON object), so every check failed with "Couldn't read Aave" and
  no row was ever written. Supersedes `earn-account@1`.

## 1

- First version: one "Aave" Platforms row for the owner's USDC lent on Aave V3 (Base),
  read on-chain each check, with its APY and about a week's interest; removed once
  nothing is lent. Checks at start, so a restart refreshes it at once.
