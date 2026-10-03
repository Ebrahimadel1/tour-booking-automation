import pytest
from datetime import datetime
from app.models.booking import NormalizedBooking
from app.models.operations import OperationType
from app.validators.booking import BookingValidator

def create_valid_normalized_booking() -> NormalizedBooking:
    return NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG12345",
        operation=OperationType.CREATE,
        date_trip=datetime(2026, 10, 23, 16, 0),
        trip_name="Test Trip",
        customer_name="John Doe",
        customer_email="john@example.com",
        customer_phone="+123456789",
        guide="English",
        total_price=93.75,
        currency="EUR",
        adt=2,
        chd=0,
        hotel_name="Some Hotel"
    )

# CREATE tests
def test_create_valid():
    booking = create_valid_normalized_booking()
    result = BookingValidator.validate(booking)
    assert result.is_valid
    assert len(result.errors) == 0

def test_create_missing_booking_nr():
    booking = create_valid_normalized_booking()
    booking.booking_number = ""
    result = BookingValidator.validate(booking)
    assert not result.is_valid
    assert any("booking_number" in e for e in result.errors)

def test_create_missing_date_trip():
    booking = create_valid_normalized_booking()
    booking.date_trip = None
    result = BookingValidator.validate(booking)
    assert not result.is_valid
    assert any("date_trip" in e for e in result.errors)

def test_create_missing_customer_name():
    booking = create_valid_normalized_booking()
    booking.customer_name = "   "
    result = BookingValidator.validate(booking)
    assert not result.is_valid

def test_create_missing_customer_email():
    booking = create_valid_normalized_booking()
    booking.customer_email = None
    result = BookingValidator.validate(booking)
    assert not result.is_valid

def test_create_invalid_customer_email():
    booking = create_valid_normalized_booking()
    booking.customer_email = "invalid-email"
    result = BookingValidator.validate(booking)
    assert not result.is_valid

def test_create_missing_customer_phone():
    booking = create_valid_normalized_booking()
    booking.customer_phone = None
    result = BookingValidator.validate(booking)
    assert not result.is_valid

def test_create_invalid_price():
    booking = create_valid_normalized_booking()
    booking.total_price = None
    result = BookingValidator.validate(booking)
    assert not result.is_valid

def test_create_negative_price():
    booking = create_valid_normalized_booking()
    booking.total_price = -10.0
    result = BookingValidator.validate(booking)
    assert not result.is_valid

def test_create_negative_adt():
    booking = create_valid_normalized_booking()
    booking.adt = -1
    result = BookingValidator.validate(booking)
    assert not result.is_valid

def test_create_negative_chd():
    booking = create_valid_normalized_booking()
    booking.chd = -1
    result = BookingValidator.validate(booking)
    assert not result.is_valid

# UPDATE tests
def test_update_valid_full():
    booking = create_valid_normalized_booking()
    booking.operation = OperationType.UPDATE
    result = BookingValidator.validate(booking)
    assert result.is_valid

def test_update_only_booking_nr_and_date():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG12345",
        operation=OperationType.UPDATE,
        date_trip=datetime(2026, 10, 23, 16, 0)
    )
    result = BookingValidator.validate(booking)
    assert result.is_valid
    
def test_update_with_missing_optional_fields():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG12345",
        operation=OperationType.UPDATE,
        customer_name="Jane Doe"
        # Everything else missing
    )
    result = BookingValidator.validate(booking)
    assert result.is_valid

def test_update_invalid_booking_nr():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="",
        operation=OperationType.UPDATE,
        date_trip=datetime(2026, 10, 23, 16, 0)
    )
    result = BookingValidator.validate(booking)
    assert not result.is_valid

# CANCEL tests
def test_cancel_valid():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG12345",
        operation=OperationType.CANCEL
    )
    result = BookingValidator.validate(booking)
    assert result.is_valid

def test_cancel_missing_booking_nr():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="",
        operation=OperationType.CANCEL
    )
    result = BookingValidator.validate(booking)
    assert not result.is_valid
    
def test_cancel_without_customer_name():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG12345",
        operation=OperationType.CANCEL
    )
    result = BookingValidator.validate(booking)
    assert result.is_valid
    
def test_cancel_without_date_trip():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG12345",
        operation=OperationType.CANCEL
    )
    result = BookingValidator.validate(booking)
    assert result.is_valid
    
def test_cancel_without_price():
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG12345",
        operation=OperationType.CANCEL
    )
    result = BookingValidator.validate(booking)
    assert result.is_valid

# Regression integrations
from app.parsers.getyourguide import GetYourGuideParser
from pathlib import Path

def test_regression_no_date_artifact_leak():
    text = (Path(__file__).parent / "fixtures" / "create" / "create_artifact_date.txt").read_text(encoding="utf-8")
    booking = GetYourGuideParser.parse(text)
    result = BookingValidator.validate(booking)
    assert result.is_valid
    assert booking.date_trip == datetime(2026, 10, 23, 16, 0)

def test_regression_no_price_artifact_leak():
    text = (Path(__file__).parent / "fixtures" / "create" / "create_artifact_price.txt").read_text(encoding="utf-8")
    booking = GetYourGuideParser.parse(text)
    result = BookingValidator.validate(booking)
    assert result.is_valid
    assert booking.total_price == 93.75
