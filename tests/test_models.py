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
        booking_status="Active",
        hotel_name="Some Hotel",
        google_maps="https://maps.google.com/test",
        inf=1,
        country_from_phone="South Africa",
        customer_country="South Africa"
    )
    
    # Test that model dumps using aliases correctly
    dumped = record.model_dump(by_alias=True, exclude_none=True)
    assert "Agency" in dumped
    assert dumped["Agency"] == "GetYourGuide"
    assert "Booking Nr." in dumped
    assert dumped["Booking Nr."] == "GYGN6BWBM54M"
    assert "Booking Status" in dumped
    assert dumped["Booking Status"] == "Active"
    assert dumped["Hotel Name"] == "Some Hotel"
    assert dumped["Google Maps"] == "https://maps.google.com/test"
    assert dumped["Inf"] == 1
    assert dumped["Country from Phone"] == "South Africa"
    assert dumped["Customer Country"] == "South Africa"

def test_airtable_booking_record_population_by_alias():
    # Test we can instantiate using alias names (simulating reading from Airtable)
    data = {
        "Agency": "GetYourGuide",
        "Booking Nr.": "GYG12345",
        "Date Trip": "2026-10-23T16:00:00.000Z",
        "Booking Status": "Canceled",
        "Hotel Name": "Nile Boutique Hotel",
        "Google Maps": "https://mail.getyourguide.com/ls/click",
        "Inf": 2,
        "Country from Phone": "France",
        "Customer Country": "France"
    }
    
    record = AirtableBookingRecord(**data)
    assert record.agency == "GetYourGuide"
    assert record.booking_nr == "GYG12345"
    assert record.date_trip == "2026-10-23T16:00:00.000Z"
    assert record.booking_status == "Canceled"
    assert record.hotel_name == "Nile Boutique Hotel"
    assert record.google_maps == "https://mail.getyourguide.com/ls/click"
    assert record.inf == 2
    assert record.country_from_phone == "France"
    assert record.customer_country == "France"


def test_airtable_booking_record_ai_and_lookup_dict_fields():
    # Test handling Airtable AI generated field dictionaries
    data = {
        "Agency": "GetYourGuide",
        "Booking Nr.": "GYGMX37XQY9L",
        "Country from Phone": {
            "state": "generated",
            "value": "France",
            "isStale": False
        },
        "Customer Country": ["France"],
        "Booking Status": {"id": 1, "value": "Canceled"}
    }
    record = AirtableBookingRecord(**data)
    assert record.country_from_phone == "France"
    assert record.customer_country == "France"
    assert record.booking_status == "Canceled"


def test_airtable_booking_record_ai_error_field():
    # Test handling Airtable AI error or empty field dictionaries
    data = {
        "Booking Nr.": "GYGMX37XQY9L",
        "Country from Phone": {
            "state": "error",
            "error": "#ERROR! Not found",
            "isStale": False
        },
        "Customer Country": []
    }
    record = AirtableBookingRecord(**data)
    assert record.country_from_phone is None
    assert record.customer_country is None


def test_airtable_booking_record_add_ons():
    record = AirtableBookingRecord(
        booking_nr="GYGADDON1",
        add_ons="2 x Round Trip Transportation (Per Person)"
    )
    dumped = record.model_dump(by_alias=True, exclude_none=True)
    assert "Add - Ons" in dumped
    assert dumped["Add - Ons"] == "2 x Round Trip Transportation (Per Person)"

    # Test reading alias from dict
    data = {
        "Booking Nr.": "GYGADDON1",
        "Add - Ons": "2 x Round Trip Transportation (Per Person)"
    }
    rec2 = AirtableBookingRecord(**data)
    assert rec2.add_ons == "2 x Round Trip Transportation (Per Person)"

    # Test reading from select/dict or list
    data_dict = {
        "Booking Nr.": "GYGADDON1",
        "Add - Ons": {"value": "2 x Round Trip Transportation"}
    }
    rec3 = AirtableBookingRecord(**data_dict)
    assert rec3.add_ons == "2 x Round Trip Transportation"

    data_list = {
        "Booking Nr.": "GYGADDON1",
        "Add - Ons": ["2 x Round Trip Transportation"]
    }
    rec4 = AirtableBookingRecord(**data_list)
    assert rec4.add_ons == "2 x Round Trip Transportation"


def test_airtable_booking_record_participants_aliases():
    record = AirtableBookingRecord(
        booking_nr="GYG12345",
        adt=2,
        std=0,
        chd=1,
        inf=0,
        youth=0
    )
    dumped = record.model_dump(by_alias=True, exclude_none=True)
    assert dumped["ADT"] == 2
    assert dumped["STD"] == 0
    assert dumped["CHD"] == 1
    assert dumped["Inf"] == 0
    assert dumped["Youth"] == 0

    # Test instantiation from Airtable dict with aliases
    airtable_data = {
        "Booking Nr.": "GYG12345",
        "ADT": 2,
        "STD": 0,
        "CHD": 1,
        "Inf": 0,
        "Youth": 0
    }
    rec2 = AirtableBookingRecord(**airtable_data)
    assert rec2.adt == 2
    assert rec2.std == 0
    assert rec2.chd == 1
    assert rec2.inf == 0
    assert rec2.youth == 0


