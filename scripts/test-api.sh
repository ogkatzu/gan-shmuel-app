#!/bin/bash

LOGFILE="logs/api.log"
mkdir -p "$(dirname "$LOGFILE")"
touch "$LOGFILE"

timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log() {
    echo "[$(timestamp)] $1" | tee -a "$LOGFILE"
}

run_api_test() {
    local label="$1"
    local cmd="$2"
    local output

    log "=== $label ==="
    log "Command: $cmd"
    output=$(eval "$cmd" 2>&1)
    log "Output: $output"
    echo | tee -a "$LOGFILE"
}

# ------------------------
# ✅ Provider Tests
# ------------------------
run_api_test "Create Provider" \
'curl -s -X POST http://127.0.0.1:5500/provider -H "Content-Type: application/json" -d '\''{"name": "MyProvider"}'\'''

run_api_test "Update Provider (ID=10004)" \
'curl -s -X PUT http://127.0.0.1:5500/provider/10004 -H "Content-Type: application/json" -d '\''{"name": "Updated_Name"}'\'''

# ------------------------
# ✅ Health Check
# ------------------------
run_api_test "Health Check" \
'curl -s http://127.0.0.1:5500/health'

# ------------------------
# ✅ Truck Tests
# ------------------------
run_api_test "Register New Truck (T-88888)" \
'curl -s -X POST http://127.0.0.1:5500/truck -H "Content-Type: application/json" -d '\''{"provider": 10001, "id": "T-88888"}'\'''

run_api_test "Register Duplicate Truck (T-88888)" \
'curl -s -X POST http://127.0.0.1:5500/truck -H "Content-Type: application/json" -d '\''{"provider": 10001, "id": "T-88888"}'\'''

run_api_test "Register Truck (Missing Provider)" \
'curl -s -X POST http://127.0.0.1:5500/truck -H "Content-Type: application/json" -d '\''{"id": "T-99999"}'\'''

run_api_test "Register Truck (Invalid Provider)" \
'curl -s -X POST http://127.0.0.1:5500/truck -H "Content-Type: application/json" -d '\''{"provider": 99999, "id": "T-77777"}'\'''
