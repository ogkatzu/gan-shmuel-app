# Billing Dev Environment - team guide

- This environment includes a Flask API and a MySQL database,
  fully controlled via Docker Compose. Use the following aliases for fast interaction:
- each team member creates his own branch
  e.g: feat/api-get-session-id
- write in slack when you push changes

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

## Before pushing changes:
Always run api-test and check logs/api.log to ensure there are no errors or crashes in your code.


## app file python code need to check:
    not checked yet:
    POST rates + GET rates

    POST Truck - implemented twice - choose what is better.

    neet to do:
    1. GET /item/<id>
    2. GET /session/<id>
    3. GET /weight
    4. GET /bill/<id>