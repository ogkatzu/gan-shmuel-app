#!/bin/bash

# Start in detached mode (background)
docker compose -f docker-compose-ci.yml up && echo "Container is up and running..."           


