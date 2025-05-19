## Billing Dev Environment - team guide

This environment includes a Flask API and a MySQL database,
fully controlled via Docker Compose. Use the following aliases for fast interaction:

each team member creates his own branch
e.g: feat/api-get-session-id

---


## Load aliases into your shell
source scripts/env-alias-list.txt

## Start the environment (build + run containers)
up

## Stop and remove all containers
down

## Run API test script
api-test

---

# Project tree:
.
├── billing
│   ├── billdb
│   │   └── billdb.sql
│   └── flask-in
│       ├── app.py
│       ├── __pycache__
│       │   └── app.cpython-312.pyc
│       └── requirements.txt
├── docker-compose-billing.yml
├── logs
│   └── api.log
└── scripts
    ├── env-alias-list.txt
    └── test-api.sh

## instructions:
- full dev env for testing

