import pytest
from unittest.mock import MagicMock
from app.repositories.baserow_repository import BaserowRepository
from app.repositories.dual_repository import DualBookingRepository
from app.models.booking import AirtableBookingRecord


@pytest.fixture
def baserow_repo():
    return BaserowRepository(
        base_url="https://booking.tourcare.ai",
        table_id="1194",
        token="test_token"
    )


def test_baserow_find_by_booking_number_exists(mocker, baserow_repo):
    mock_get = mocker.patch("requests.get")
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "count": 1,
        "results": [
            {
                "id": 42,
                "Agency": "GetYourGuide",
                "Booking Nr.": "GYG12345",
                "trip Name": "Nile Sunset Dinner Cruise",
                "Customer Name": "John Doe",
                "Booking Status": {"id": 55080, "value": "Active", "color": "light-blue"}
            }
        ]
    }
    mock_get.return_value = mock_response

    record = baserow_repo.find_by_booking_number("GYG12345")
    assert record is not None
    assert record.agency == "GetYourGuide"
    assert record.booking_nr == "GYG12345"
    assert record.booking_status == "Active"


def test_baserow_find_by_booking_number_missing(mocker, baserow_repo):
    mock_get = mocker.patch("requests.get")
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"count": 0, "results": []}
    mock_get.return_value = mock_response

    record = baserow_repo.find_by_booking_number("GYG999")
    assert record is None


def test_baserow_find_by_booking_number_error(mocker, baserow_repo):
    mock_get = mocker.patch("requests.get")
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_get.return_value = mock_response

    with pytest.raises(RuntimeError):
        baserow_repo.find_by_booking_number("GYG12345")


def test_baserow_create_record(mocker, baserow_repo):
    mock_post = mocker.patch("requests.post")
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 100}
    mock_post.return_value = mock_response

    record = AirtableBookingRecord(
        agency="GetYourGuide",
        booking_nr="GYG12345",
        booking_status="Active"
    )
    success = baserow_repo.create(record)
    assert success is True
    mock_post.assert_called_once()


def test_baserow_update_record(mocker, baserow_repo):
    mock_get = mocker.patch("requests.get")
    mock_get_response = MagicMock()
    mock_get_response.ok = True
    mock_get_response.json.return_value = {
        "results": [{"id": 42, "Booking Nr.": "GYG12345"}]
    }
    mock_get.return_value = mock_get_response

    mock_patch = mocker.patch("requests.patch")
    mock_patch_response = MagicMock()
    mock_patch_response.ok = True
    mock_patch.return_value = mock_patch_response

    success = baserow_repo.update("GYG12345", {"Booking Status": "Canceled"})
    assert success is True
    mock_patch.assert_called_once()
    assert "42" in mock_patch.call_args[0][0]


def test_dual_repository_both_enabled(mocker):
    mock_airtable = MagicMock()
    mock_baserow = MagicMock()

    mock_airtable.create.return_value = True
    mock_baserow.create.return_value = True

    dual_repo = DualBookingRepository(
        airtable_repo=mock_airtable,
        baserow_repo=mock_baserow,
        enable_airtable=True,
        enable_baserow=True
    )

    record = AirtableBookingRecord(booking_nr="GYG100")
    success = dual_repo.create(record)

    assert success is True
    mock_airtable.create.assert_called_once_with(record)
    mock_baserow.create.assert_called_once_with(record)


def test_dual_repository_airtable_disabled(mocker):
    mock_airtable = MagicMock()
    mock_baserow = MagicMock()

    mock_baserow.create.return_value = True

    dual_repo = DualBookingRepository(
        airtable_repo=mock_airtable,
        baserow_repo=mock_baserow,
        enable_airtable=False,
        enable_baserow=True
    )

    record = AirtableBookingRecord(booking_nr="GYG100")
    success = dual_repo.create(record)

    assert success is True
    mock_airtable.create.assert_not_called()
    mock_baserow.create.assert_called_once_with(record)


def test_dual_repository_baserow_disabled(mocker):
    mock_airtable = MagicMock()
    mock_baserow = MagicMock()

    mock_airtable.create.return_value = True

    dual_repo = DualBookingRepository(
        airtable_repo=mock_airtable,
        baserow_repo=mock_baserow,
        enable_airtable=True,
        enable_baserow=False
    )

    record = AirtableBookingRecord(booking_nr="GYG100")
    success = dual_repo.create(record)

    assert success is True
    mock_airtable.create.assert_called_once_with(record)
    mock_baserow.create.assert_not_called()


def test_dual_repository_resilient_error_handling(mocker):
    mock_airtable = MagicMock()
    mock_baserow = MagicMock()

    # Airtable crashes with an unexpected exception
    mock_airtable.create.side_effect = RuntimeError("Airtable down")
    # Baserow succeeds
    mock_baserow.create.return_value = True

    dual_repo = DualBookingRepository(
        airtable_repo=mock_airtable,
        baserow_repo=mock_baserow,
        enable_airtable=True,
        enable_baserow=True
    )

    record = AirtableBookingRecord(booking_nr="GYG100")
    success = dual_repo.create(record)

    # Should still succeed overall because Baserow succeeded
    assert success is True
    mock_airtable.create.assert_called_once()
    mock_baserow.create.assert_called_once()


def test_dual_repository_find_fallback(mocker):
    mock_airtable = MagicMock()
    mock_baserow = MagicMock()

    # Not in Airtable, but found in Baserow
    mock_airtable.find_by_booking_number.return_value = None
    expected_record = AirtableBookingRecord(booking_nr="GYG200")
    mock_baserow.find_by_booking_number.return_value = expected_record

    dual_repo = DualBookingRepository(
        airtable_repo=mock_airtable,
        baserow_repo=mock_baserow,
        enable_airtable=True,
        enable_baserow=True
    )

    found = dual_repo.find_by_booking_number("GYG200")
    assert found == expected_record


def test_baserow_create_converts_local_date_to_utc(mocker, baserow_repo):
    mock_post = mocker.patch("requests.post")
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 101}
    mock_post.return_value = mock_response

    # Cairo Summer (EEST, UTC+3)
    record = AirtableBookingRecord(
        agency="GetYourGuide",
        booking_nr="GYGVN2Y6MBRN",
        date_trip="2026-10-21T18:00:00"
    )
    success = baserow_repo.create(record)
    assert success is True

    posted_json = mock_post.call_args[1]["json"]
    # 18:00 local Cairo time in October (EEST UTC+3) becomes 15:00 UTC
    assert posted_json["Date Trip"] == "2026-10-21T15:00:00Z"


def test_baserow_update_converts_local_date_to_utc_without_mutating_original(mocker, baserow_repo):
    mock_get = mocker.patch("requests.get")
    mock_get_response = MagicMock()
    mock_get_response.ok = True
    mock_get_response.json.return_value = {
        "results": [{"id": 55, "Booking Nr.": "GYGVN2Y6MBRN"}]
    }
    mock_get.return_value = mock_get_response

    mock_patch = mocker.patch("requests.patch")
    mock_patch_response = MagicMock()
    mock_patch_response.ok = True
    mock_patch.return_value = mock_patch_response

    original_changes = {
        "Date Trip": "2026-10-21T18:00:00",
        "Booking Status": "Active"
    }
    success = baserow_repo.update("GYGVN2Y6MBRN", original_changes)
    assert success is True

    patched_json = mock_patch.call_args[1]["json"]
    # Verify sent payload was converted to UTC
    assert patched_json["Date Trip"] == "2026-10-21T15:00:00Z"
    # Verify original dictionary was NOT mutated (so Airtable is untouched)
    assert original_changes["Date Trip"] == "2026-10-21T18:00:00"


def test_baserow_find_converts_utc_to_local_time(mocker, baserow_repo):
    mock_get = mocker.patch("requests.get")
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "count": 1,
        "results": [
            {
                "id": 99,
                "Agency": "GetYourGuide",
                "Booking Nr.": "GYGVN2Y6MBRN",
                "Date Trip": "2026-10-21T15:00:00Z"
            }
        ]
    }
    mock_get.return_value = mock_response

    record = baserow_repo.find_by_booking_number("GYGVN2Y6MBRN")
    assert record is not None
    # 15:00 UTC converted back to Cairo local time (EEST UTC+3) is 18:00
    assert record.date_trip == "2026-10-21T18:00:00"


def test_baserow_winter_time_conversion(mocker, baserow_repo):
    mock_post = mocker.patch("requests.post")
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 102}
    mock_post.return_value = mock_response

    # Cairo Winter (EET, UTC+2 in January)
    record = AirtableBookingRecord(
        agency="GetYourGuide",
        booking_nr="GYGWINTER",
        date_trip="2026-01-15T18:00:00"
    )
    baserow_repo.create(record)
    posted_json = mock_post.call_args[1]["json"]
    # 18:00 local Cairo time in January (EET UTC+2) becomes 16:00 UTC
    assert posted_json["Date Trip"] == "2026-01-15T16:00:00Z"

