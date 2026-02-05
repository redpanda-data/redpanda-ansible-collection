#!/usr/bin/env bats

SCRIPT="$BATS_TEST_DIRNAME/../files/idempotent-config-set.sh"

setup() {
  mkdir -p "$BATS_TEST_TMPDIR/bin"

  # Write mock rpk
  cat > "$BATS_TEST_TMPDIR/bin/rpk" <<'MOCK'
#!/bin/bash
if [[ "$*" == *"cluster config get"* ]]; then
  echo "${MOCK_RPK_GET_OUTPUT}"
  exit "${MOCK_RPK_GET_RC:-0}"
elif [[ "$*" == *"cluster config set"* ]]; then
  echo "Successfully updated configuration."
  exit 0
fi
MOCK
  chmod +x "$BATS_TEST_TMPDIR/bin/rpk"

  export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
  export CONFIG_KEY="test_key"
  export RPK_OPTS=""
}

@test "null always changes" {
  export MOCK_RPK_GET_OUTPUT="null"
  export CONFIG_VALUE="some_value"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RESULT:CHANGED"* ]]
}

@test "scalar match (case-insensitive)" {
  export MOCK_RPK_GET_OUTPUT="true"
  export CONFIG_VALUE="True"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RESULT:OK"* ]]
}

@test "scalar mismatch" {
  export MOCK_RPK_GET_OUTPUT="false"
  export CONFIG_VALUE="true"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RESULT:CHANGED"* ]]
}

@test "integer match" {
  export MOCK_RPK_GET_OUTPUT="42"
  export CONFIG_VALUE="42"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RESULT:OK"* ]]
}

@test "integer mismatch" {
  export MOCK_RPK_GET_OUTPUT="42"
  export CONFIG_VALUE="99"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RESULT:CHANGED"* ]]
}

@test "empty array vs empty desired" {
  export MOCK_RPK_GET_OUTPUT="[]"
  export CONFIG_VALUE="[]"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RESULT:OK"* ]]
}

@test "array match (different order)" {
  export MOCK_RPK_GET_OUTPUT=$'- bar\n- foo'
  export CONFIG_VALUE="['foo', 'bar']"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RESULT:OK"* ]]
}

@test "array mismatch" {
  export MOCK_RPK_GET_OUTPUT="- foo"
  export CONFIG_VALUE="['foo', 'bar']"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RESULT:CHANGED"* ]]
}

@test "rpk get failure" {
  export MOCK_RPK_GET_RC=1
  export MOCK_RPK_GET_OUTPUT="error: unable to connect"
  export CONFIG_VALUE="anything"
  run bash "$SCRIPT"
  [ "$status" -eq 1 ]
  [[ "$output" == *"RESULT:ERROR"* ]]
}
