#!/bin/bash

# Start in detached mode (background)
docker compose -f docker-compose-deploy.yml up && echo "Container is up and running..."           



