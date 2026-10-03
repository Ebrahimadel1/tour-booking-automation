import pytest
from unittest.mock import MagicMock
from app.repositories.airtable_repository import AirtableRepository
from app.models.booking import AirtableBookingRecord

@pytest.fixture
def airtable_repo():
    return AirtableRepository("base123", "table123", "token123")

def test_find_by_booking_number_exists(mocker, airtable_repo):
    mock_get = mocker.patch("requests.get")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "records": [
            {
                "id": "rec123",
                "fields": {
                    "Agency": "GetYourGuide",
                    "Booking Nr.": "GYG123",
                    "Booking Status": "Active"
                }
            }
        ]
    }
    mock_get.return_value = mock_response
    
    record = airtable_repo.find_by_booking_number("GYG123")
    assert record is not None
    assert record.agency == "GetYourGuide"
    assert record.booking_nr == "GYG123"

def test_find_by_booking_number_missing(mocker, airtable_repo):
    mock_get = mocker.patch("requests.get")
    mock_response = MagicMock()
    mock_response.json.return_value = {"records": []}
    mock_get.return_value = mock_response
    
    record = airtable_repo.find_by_booking_number("GYG999")
    assert record is None

def test_create_record(mocker, airtable_repo):
    mock_post = mocker.patch("requests.post")
    mock_response = MagicMock()
    mock_response.json.return_value = {"records": [{"id": "rec123", "fields": {}}]}
    mock_post.return_value = mock_response
    
    record = AirtableBookingRecord(agency="GetYourGuide", booking_nr="GYG123", booking_status="Active")
    success = airtable_repo.create(record)
    assert success

def test_update_record(mocker, airtable_repo):
    mock_get = mocker.patch("requests.get")
    mock_get_response = MagicMock()
    mock_get_response.json.return_value = {
        "records": [{"id": "rec123", "fields": {"Booking Nr.": "GYG123"}}]
    }
    mock_get.return_value = mock_get_response
    
    mock_patch = mocker.patch("requests.patch")
    mock_patch_response = MagicMock()
    mock_patch.return_value = mock_patch_response
    
    success = airtable_repo.update("GYG123", {"Booking Status": "Canceled"})
    assert success
    mock_patch.assert_called_once()
