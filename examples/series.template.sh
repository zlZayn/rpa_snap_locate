#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

FIRST_APP="${FIRST_APP:-<FIRST_APP_PATH>}"
FIRST_WORKFLOW="${FIRST_WORKFLOW:-<FIRST_WORKFLOW_JSON>}"
SECOND_APP="${SECOND_APP:-<SECOND_APP_PATH>}"
SECOND_WORKFLOW="${SECOND_WORKFLOW:-<SECOND_WORKFLOW_JSON>}"

run_command() {
    local name="$1"
    shift
    echo "[series] running: ${name}"
    "$@"
}

start_app() {
    local executable="$1"
    shift
    echo "[series] starting: ${executable}"
    "$executable" "$@" &
}

wait_ready() {
    local seconds="${1:-2}"
    echo "[series] waiting ${seconds} second(s) for UI readiness"
    sleep "$seconds"
}

run_rpa() {
    local workflow="$1"
    if [[ "$workflow" != /* ]]; then
        workflow="${PROJECT_ROOT}/${workflow}"
    fi
    if [[ ! -f "$workflow" ]]; then
        echo "[series] workflow not found: ${workflow}" >&2
        return 1
    fi

    echo "[series] replaying: ${workflow}"
    uv run python "${PROJECT_ROOT}/main.py" run "$workflow"
}

cd "$PROJECT_ROOT"

# Add any foreground CLI or script with run_command.
# run_command "prepare input" python scripts/prepare.py

start_app "$FIRST_APP"
wait_ready 2
run_rpa "$FIRST_WORKFLOW"

start_app "$SECOND_APP"
wait_ready 2
run_rpa "$SECOND_WORKFLOW"

echo "[series] complete"
