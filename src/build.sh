#!/bin/bash

# Start in detached mode (background)
docker compose up -d && echo "Container is up and running..."           

# Run for 2 seconds 
sleep 2

# Stop & remove the container
docker compose down && echo "Container stopped"            

