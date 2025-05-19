#!/bin/bash

LOGFILE="logs/api.log"
mkdir -p "$(dirname "$LOGFILE")"

timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log_and_display() {
    echo "$1" | tee -a "$LOGFILE"
}

#timestamp:
log_and_display "[$(timestamp)]"

#api test:
run_api_test() {
    local label="$1"
    local cmd="$2"
    local output

    log_and_display "api: $cmd"

    output=$(eval "$cmd" 2>&1)
    log_and_display "output: $output"
    log_and_display ""
}

### api list:
run_api_test "Create Provider" \
'curl -s -X POST http://127.0.0.1:5500/provider -H "Content-Type: application/json" -d '\''{"name": "MyProvider"}'\'''

run_api_test "Update Provider" \
'curl -s -X PUT http://127.0.0.1:5500/provider/10004 -H "Content-Type: application/json" -d '\''{"name": "Updated_Name!"}'\'''

run_api_test "Health Check" \
'curl -s http://127.0.0.1:5500/health'
