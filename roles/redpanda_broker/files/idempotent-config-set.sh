#!/bin/bash
set -euo pipefail

# Idempotent rpk cluster config set
#
# Reads inputs from environment variables:
#   CONFIG_KEY   — the cluster config key to set
#   CONFIG_VALUE — the desired value
#   RPK_OPTS     — extra flags passed to rpk (e.g. --api-urls)
#
# Output protocol (consumed by Ansible changed_when / failed_when):
#   RESULT:CHANGED — value was updated
#   RESULT:OK      — value already matches
#   RESULT:ERROR   — something went wrong

KEY="$CONFIG_KEY"
DESIRED="$CONFIG_VALUE"

# Unset empty auth credentials — rpk reads RPK_USER/RPK_PASS from the
# environment and constructs an Authorization header even when they are
# empty strings, which the Admin API rejects as "Malformed Authorization
# header".
[ -z "${RPK_USER-}" ] && unset RPK_USER
[ -z "${RPK_PASS-}" ] && unset RPK_PASS

# shellcheck disable=SC2086
CURRENT=$(rpk cluster config get "$KEY" $RPK_OPTS 2>&1) || {
  echo "RESULT:ERROR:rpk get failed: $CURRENT"
  exit 1
}
CURRENT=$(echo "$CURRENT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

# null means unset — always apply desired value
if [ "$CURRENT" = "null" ]; then
  # shellcheck disable=SC2086
  rpk cluster config set "$KEY" "$DESIRED" $RPK_OPTS
  echo "RESULT:CHANGED:was null, set to $DESIRED"
  exit 0
fi

# Detect array: rpk returns '[]' or lines starting with '- '
if [ "$CURRENT" = "[]" ] || echo "$CURRENT" | head -1 | grep -q '^- '; then
  # Parse rpk YAML array into sorted lines
  if [ "$CURRENT" = "[]" ]; then
    NORM_CURRENT=""
  else
    NORM_CURRENT=$(echo "$CURRENT" | grep '^- ' | sed 's/^- //' | sort)
  fi
  # Parse Ansible JSON/Python array into sorted lines
  NORM_DESIRED=$(echo "$DESIRED" | tr -d "[]'\"" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' | sort || true)

  if [ "$NORM_CURRENT" = "$NORM_DESIRED" ]; then
    echo "RESULT:OK:array values match"
    exit 0
  fi
  # shellcheck disable=SC2086
  rpk cluster config set "$KEY" "$DESIRED" $RPK_OPTS
  echo "RESULT:CHANGED:array values differ"
  exit 0
fi

# Scalar: case-insensitive string compare
CURRENT_LOWER=$(echo "$CURRENT" | tr '[:upper:]' '[:lower:]')
DESIRED_LOWER=$(echo "$DESIRED" | tr '[:upper:]' '[:lower:]')

if [ "$CURRENT_LOWER" = "$DESIRED_LOWER" ]; then
  echo "RESULT:OK:values match ($CURRENT_LOWER)"
  exit 0
fi

# shellcheck disable=SC2086
rpk cluster config set "$KEY" "$DESIRED" $RPK_OPTS
echo "RESULT:CHANGED:$CURRENT_LOWER -> $DESIRED_LOWER"
