#!/usr/bin/env bash
# Smoke-run every SDK example against whatever .env the loader picks up
# (.env.local takes precedence over .env). Prints pass/fail per example,
# fails the run if any example errors.
#
# Streams are capped at 15s; the runner treats SIGTERM (143) and `timeout`'s
# 124 as success because the stream produced output before being killed.
#
# Brittle examples (those that depend on hardcoded state or leave dangling
# orders) are skipped by default. Pass --include-brittle to run them too.

set -u

cd "$(dirname "$0")/.."

# Examples that terminate on their own + are idempotent / self-funding.
SAFE=(
  examples/mint-platform/login_and_logout.py
  examples/mint-platform/portfolio.py
  examples/dex/swap.py
  examples/dex/liquidity_amm.py
  examples/dex/liquidity_pricefeed.py
)

# Examples with an infinite stream — capped via timeout(1) below.
STREAMS=(
  examples/mint-platform/stocks_and_prices.py
  examples/mint-platform/price_stream/prices_stream_logged.py
  examples/mint-platform/price_stream/prices_stream_not_logged.py
)

# Examples that touch hardcoded state (withdrawal id, expected stock balance,
# leave open orders). Opt-in via --include-brittle.
BRITTLE=(
  examples/mint-platform/buying_and_selling_stocks.py
  examples/mint-platform/deposit_withdraw_distribution.py
)

INCLUDE_BRITTLE=0
[ "${1-}" = "--include-brittle" ] && INCLUDE_BRITTLE=1

STREAM_TIMEOUT_SECS=15
PASS=0
FAIL=0
FAILED=()

run_terminating() {
  local script="$1"
  printf '  %-65s ' "$script"
  if out=$(uv run python "$script" 2>&1); then
    echo "PASS"
    PASS=$((PASS + 1))
  else
    echo "FAIL"
    FAIL=$((FAIL + 1))
    FAILED+=("$script")
    echo "$out" | sed 's/^/      /' | tail -10
  fi
}

run_stream() {
  local script="$1"
  printf '  %-65s ' "$script"
  # Run in background, kill after timeout. Exit codes 0, 124 (timeout coreutils)
  # or 143 (SIGTERM) all mean "ran cleanly and produced output until killed".
  local outfile
  outfile=$(mktemp)
  PYTHONUNBUFFERED=1 uv run python "$script" >"$outfile" 2>&1 &
  local pid=$!
  sleep "$STREAM_TIMEOUT_SECS"
  kill -TERM "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null
  local rc=$?
  local lines
  lines=$(wc -l <"$outfile" | tr -d ' ')
  rm -f "$outfile"
  if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ] || [ "$rc" -eq 143 ]; then
    if [ "$lines" -gt 0 ]; then
      echo "PASS  ($lines lines in ${STREAM_TIMEOUT_SECS}s)"
      PASS=$((PASS + 1))
    else
      echo "FAIL  (no output before kill)"
      FAIL=$((FAIL + 1))
      FAILED+=("$script")
    fi
  else
    echo "FAIL  (exit $rc)"
    FAIL=$((FAIL + 1))
    FAILED+=("$script")
  fi
}

echo "==> safe terminating examples"
for f in "${SAFE[@]}"; do run_terminating "$f"; done

echo
echo "==> stream examples (cap ${STREAM_TIMEOUT_SECS}s)"
for f in "${STREAMS[@]}"; do run_stream "$f"; done

if [ "$INCLUDE_BRITTLE" -eq 1 ]; then
  echo
  echo "==> brittle examples (--include-brittle)"
  for f in "${BRITTLE[@]}"; do run_terminating "$f"; done
fi

echo
echo "==> summary: $PASS pass, $FAIL fail"
if [ "$FAIL" -ne 0 ]; then
  echo "failed:"
  for f in "${FAILED[@]}"; do echo "  - $f"; done
  exit 1
fi
