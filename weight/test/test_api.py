
import pytest
import requests
import datetime
import os
host = os.environ.get('TEST_HOST', 'localhost')
BASE_URL = f"http://{host}:5000"

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


def test_get_weight_default():
    response = requests.get(f"{BASE_URL}/weight")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    for item in data:
        assert isinstance(item, dict)
        assert "id" in item
        assert "direction" in item
        assert item["direction"] in ("in", "out", "none")

        assert "bruto" in item
        assert isinstance(item["bruto"], int)

        assert "neto" in item
        assert isinstance(item["neto"], (int, str))
        if isinstance(item["neto"], str):
            assert item["neto"] == "na"

        assert "produce" in item
        assert isinstance(item["produce"], str)

        assert "containers" in item
        assert isinstance(item["containers"], list)
        for cid in item["containers"]:
            assert isinstance(cid, str)


def test_get_unknown_containers():
    response = requests.get(f"{BASE_URL}/unknown")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    for item in response.json():
        assert isinstance(item, str)

def test_post_batch_weight_csv():
    payload = {
        "file": "containers2.csv"
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(f"{BASE_URL}/batch-weight", json=payload, headers=headers)

    print(response.status_code, response.text)
    assert response.status_code in (200, 201)
def test_post_batch_weight_csv_file_not_found():
    payload = {
        "file": "nonexistent.csv"
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(f"{BASE_URL}/batch-weight", json=payload, headers=headers)

    assert response.status_code == 400
    assert "File not found" in response.text

def test_get_session_by_id():
    # This requires a valid session ID to be created beforehand
    # Simulating with a known/assumed session ID
    session_id = "test-session-id"  # Replace with actual known session ID
    response = requests.get(f"{BASE_URL}/session/{session_id}")
    if response.status_code == 404:
        pytest.skip("Session ID not found. Create one before running this test.")
    else:
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "bruto" in data

def test_weight_post():
    payload = {
        "direction": "in",
        "truck": "AB9123",
        "containers": ["K-8263", "K-5269", "K-7943"],
        "weight": 18000,
        "unit": "kg",
        "force": False,
        "produce": "tomato",
        "datetime": "2025-05-21T12:00:00"
    }

    response = requests.post(f"{BASE_URL}/weight", json=payload)

    if response.status_code == 400:
        pytest.skip("Truck already exists.")

    assert response.status_code in [200, 201], f"Unexpected status: {response.status_code}"
    data = response.json()
    assert "truck" in data, "The response does not contain a truck ID"
    assert "bruto" in data, "The response does not contain a bruto weight"

def test_get_item():
    # Test with existing truck ID
    truck_id = "AB9123"  # Replace with a known ID
    # Perform the request
    response = requests.get(f"{BASE_URL}/item/{truck_id}")
    # Check if item exists, otherwise skip
    if response.status_code == 404:
        pytest.skip(f"Item {truck_id} not found. Create it before running this test.")
    # Basic assertions
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "id" in data
    assert "tara" in data
    assert "sessions" in data
    # Test with a non-existent ID

def test_get_item_non_existing():
    nonexistent_id = "EEEEE123456"
    response_nonexistent = requests.get(f"{BASE_URL}/item/{nonexistent_id}")
    assert response_nonexistent.status_code == 404



