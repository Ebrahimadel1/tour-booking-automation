import pytest
from datetime import datetime
from app.models.operations import OperationType
from app.models.booking import NormalizedBooking, AirtableBookingRecord

def test_normalized_booking_creation():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYGN6BWBM54M",
        operation=OperationType.CREATE,
        date_trip=datetime(2026, 10, 23, 16, 0),
        trip_name="Test Trip",
        total_price=93.75,
        currency="EUR"
    )
    
    assert booking.provider == "GetYourGuide"
    assert booking.booking_number == "GYGN6BWBM54M"
    assert booking.operation == OperationType.CREATE
    assert booking.date_trip == datetime(2026, 10, 23, 16, 0)
    assert booking.total_price == 93.75
    assert booking.currency == "EUR"

def test_airtable_booking_record_aliases():
    record = AirtableBookingRecord(
        agency="GetYourGuide",
        booking_nr="GYGN6BWBM54M",
        booking_status="Active"
    )
    
    # Test that model dumps using aliases correctly
    dumped = record.model_dump(by_alias=True, exclude_none=True)
    assert "Agency" in dumped
    assert dumped["Agency"] == "GetYourGuide"
    assert "Booking Nr." in dumped
    assert dumped["Booking Nr."] == "GYGN6BWBM54M"
    assert "Booking Status" in dumped
    assert dumped["Booking Status"] == "Active"

def test_airtable_booking_record_population_by_alias():
    # Test we can instantiate using alias names (simulating reading from Airtable)
    data = {
        "Agency": "GetYourGuide",
        "Booking Nr.": "GYG12345",
        "Date Trip": "2026-10-23T16:00:00.000Z",
        "Booking Status": "Canceled"
    }
    
    record = AirtableBookingRecord(**data)
    assert record.agency == "GetYourGuide"
    assert record.booking_nr == "GYG12345"
    assert record.date_trip == "2026-10-23T16:00:00.000Z"
    assert record.booking_status == "Canceled"
