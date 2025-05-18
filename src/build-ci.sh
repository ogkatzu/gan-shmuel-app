#!/bin/bash

# Start in detached mode (background)
docker compose -f docker-compose-ci.yml up && echo "Container is up and running..."           

# Run for 2 seconds 
sleep 2

# Stop & remove the container
docker compose -f docker-compose-ci.yml down && echo "Container stopped"            

