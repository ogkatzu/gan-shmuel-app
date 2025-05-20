#!/bin/sh
set -e

# Log: entrypoint start
echo "[ENTRYPOINT] Starting Flask billing service..."

# Static wait instead of netcat
echo "[ENTRYPOINT] Sleeping 15 seconds to wait for MySQL at $MYSQL_HOST..."
sleep 15

echo "[ENTRYPOINT] Proceeding to start Flask app"

# Start Flask in host mode
exec flask run --host=0.0.0.0 --port=5500


