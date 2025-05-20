
import pytest
import requests

BASE_URL = "http://weight-weight_app-1:5001"  # Adjust according to your environment

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
        "file": "containers1.csv"
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
