import requests

BASE_URL = "http://127.0.0.1:5500"

def test_health_check():
    res = requests.get(f"{BASE_URL}/health")
    assert res.status_code == 200

def test_create_provider():
    payload = {"name": "MyProvider"}
    res = requests.post(f"{BASE_URL}/provider", json=payload)
    assert res.status_code == 200

def test_update_provider():
    payload = {"name": "Updated_Name!"}
    res = requests.put(f"{BASE_URL}/provider/10004", json=payload)
    assert res.status_code in [200, 404]

def test_register_truck_new():
    payload = {"provider": 10001, "id": "T-88888"}
    res = requests.post(f"{BASE_URL}/truck", json=payload)
    assert res.status_code == 200

def test_register_truck_duplicate():
    payload = {"provider": 10001, "id": "T-88888"}
    res = requests.post(f"{BASE_URL}/truck", json=payload)
    assert res.status_code in [400, 409]

def test_register_truck_missing_provider():
    payload = {"id": "T-99999"}
    res = requests.post(f"{BASE_URL}/truck", json=payload)
    assert res.status_code == 400

def test_register_truck_nonexistent_provider():
    payload = {"provider": 99999, "id": "T-77777"}
    res = requests.post(f"{BASE_URL}/truck", json=payload)
    assert res.status_code == 400

# Run pytest and log output
if __name__ == "__main__":
    import subprocess
    with open("billing_test.log", "w") as f:
        subprocess.run(["pytest", "-v", "billing_test_api.py"], stdout=f, stderr=subprocess.STDOUT)
