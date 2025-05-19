#!/bin/bash

LOGFILE="logs/api.log"
mkdir -p "$(dirname "$LOGFILE")"
touch logs/api.log

timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log_and_display() {
    echo "$1" | tee -a "$LOGFILE"
}

# Timestamp header
log_and_display "[$(timestamp)]"

# API test function
run_api_test() {
    local label="$1"
    local cmd="$2"
    local output

    log_and_display "===== $label ====="
    log_and_display "api: $cmd"
    output=$(eval "$cmd" 2>&1)
    log_and_display "output: $output"
    log_and_display ""
}

# === API list ===

run_api_test "Create Provider" \
'curl -s -X POST http://127.0.0.1:5500/provider -H "Content-Type: application/json" -d '\''{"name": "MyProvider"}'\'''

run_api_test "Update Provider" \
'curl -s -X PUT http://127.0.0.1:5500/provider/10004 -H "Content-Type: application/json" -d '\''{"name": "Updated_Name!"}'\'''

run_api_test "Health Check" \
'curl -s http://127.0.0.1:5500/health'


# === Truck Registration Tests ===
run_api_test "Register Truck (new T-88888)" \
'curl -s -X POST http://127.0.0.1:5500/truck -H "Content-Type: application/json" -d '\''{"provider": 10001, "id": "T-88888"}'\'''

run_api_test "Register Truck (duplicate T-88888)" \
'curl -s -X POST http://127.0.0.1:5500/truck -H "Content-Type: application/json" -d '\''{"provider": 10001, "id": "T-88888"}'\'''

run_api_test "Register Truck (missing provider)" \
'curl -s -X POST http://127.0.0.1:5500/truck -H "Content-Type: application/json" -d '\''{"id": "T-99999"}'\'''

run_api_test "Register Truck (nonexistent provider)" \
'curl -s -X POST http://127.0.0.1:5500/truck -H "Content-Type: application/json" -d '\''{"provider": 99999, "id": "T-77777"}'\'''