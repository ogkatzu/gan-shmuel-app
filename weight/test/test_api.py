import requests

BASE_URL = "http://localhost:5000"

def test_health_check():
    res = requests.get(f"{BASE_URL}/health")
    assert res.status_code == 200
    assert res.text == "OK"

def test_db_check():
    res = requests.get(f"{BASE_URL}/db-check")
    assert res.status_code == 200
    assert res.json().get("db") == "connected"

def test_get_weight():
    res = requests.get(f"{BASE_URL}/weight")
    assert res.status_code == 200
    assert res.text == "some value"
