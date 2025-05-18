#!/bin/bash

# Start in detached mode (background)
docker compose -f docker-compose-test.yml up && echo "Container is up and running..."           

# Run for 2 seconds (actually run tests)
sleep 2

# Stop & remove the container
docker compose -f docker-compose-test.yml down && echo "Container stopped"         

