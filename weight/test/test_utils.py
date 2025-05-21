import pytest
from datetime import datetime
from unittest.mock import MagicMock
# from weight.auxillary_functions import lb_to_kg, parse_date, get_transactions_by_time_range
import sys
import os
host = os.environ.get('TEST_HOST', 'localhost')
BASE_URL = f"http://{host}:5000"
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auxillary_functions import lb_to_kg, parse_date, get_transactions_by_time_range


# Test that 2205 pounds is correctly converted to 1000 kilograms
def test_lb_to_kg_conversion():
    unit, weight = lb_to_kg('lb', 2205)
    assert unit == 'kg'
    assert weight == 1000

# Test that 0 pounds is correctly converted to 0 kilograms
def test_lb_to_kg_zero_weight():
    unit, weight = lb_to_kg('lb', 0)
    assert unit == 'kg'
    assert weight == 0

# Test that if unit is already kg, no conversion is performed
def test_lb_to_kg_no_conversion_if_unit_not_lb():
    unit, weight = lb_to_kg('kg', 1000)
    assert unit == 'kg'
    assert weight == 1000

# Test that if weight is not an integer, no conversion is performed
def test_lb_to_kg_no_conversion_if_weight_not_int():
    unit, weight = lb_to_kg('lb', '2205')
    assert unit == 'lb'
    assert weight == '2205'

# Test parsing a valid date string to datetime object
def test_parse_date_valid_format():
    date_str = "20250518143000"
    dt = parse_date(date_str)
    assert isinstance(dt, datetime)
    assert dt.year == 2025
    assert dt.month == 5
    assert dt.day == 18
    assert dt.hour == 14
    assert dt.minute == 30
    assert dt.second == 0

# Test that an invalid date string returns the default datetime
def test_parse_date_invalid_format_returns_default():
    default = datetime(2020, 1, 1)
    dt = parse_date("invalid_date", default)
    assert dt == default

# Test that an empty string returns the default datetime
def test_parse_date_empty_string_returns_default():
    default = datetime(2020, 1, 1)
    dt = parse_date("", default)
    assert dt == default

# Fixture that mocks the database session and model
@pytest.fixture
def mock_db_session_and_model():
    mock_transaction = MagicMock()
    mock_transaction.id = 1
    mock_transaction.direction = "in"
    mock_transaction.datetime = datetime.now()
    mock_transaction.bruto = 12000
    mock_transaction.neto = 10000
    mock_transaction.produce = "Apples"
    mock_transaction.containers = "C001,C002"

    mock_model = MagicMock()
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = [mock_transaction]

    return mock_session, mock_model

# Test that get_transactions_by_time_range returns a correctly formatted dictionary
def test_get_transactions_by_time_range_returns_correct_format(mock_db_session_and_model):
    mock_session, mock_model = mock_db_session_and_model

    results = get_transactions_by_time_range(
        mock_session, 
        mock_model, 
        from_time="20250101000000", 
        to_time="20251231235959", 
        directions="in,out"
    )

    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]
    assert item["id"] == 1
    assert item["direction"] == "in"
    assert item["bruto"] == 12000
    assert item["neto"] == 10000
    assert item["produce"] == "Apples"
    assert item["containers"] == ["C001", "C002"]

# Test that if containers is None, it returns an empty list
def test_get_transactions_by_time_range_handles_empty_containers(mock_db_session_and_model):
    mock_session, mock_model = mock_db_session_and_model
    mock_session.query.return_value.filter.return_value.all.return_value[0].containers = None

    results = get_transactions_by_time_range(
        mock_session,
        mock_model,
        from_time=None,
        to_time=None,
        directions=None
    )

    assert results[0]["containers"] == []

# Test that if a DB error occurs, the function returns an empty list
def test_get_transactions_by_time_range_handles_exception():
    mock_session = MagicMock()
    mock_session.query.side_effect = Exception("DB error")
    mock_model = MagicMock()

    results = get_transactions_by_time_range(
        mock_session,
        mock_model,
        from_time=None,
        to_time=None,
        directions=None
    )

    assert results == []
