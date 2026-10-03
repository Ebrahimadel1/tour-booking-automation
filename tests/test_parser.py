import pytest
from pathlib import Path
from datetime import datetime
from app.models.operations import OperationType
from app.parsers.getyourguide import GetYourGuideParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_fixture(type_dir: str, filename: str) -> str:
    path = FIXTURES_DIR / type_dir / filename
    return path.read_text(encoding="utf-8")

def test_normal_create():
    text = load_fixture("create", "create_normal.txt")
    booking = GetYourGuideParser.parse(text)
    
    assert booking.operation == OperationType.CREATE
    assert booking.booking_number == "GYGN6BWBM54M"
    assert booking.date_trip == datetime(2026, 10, 23, 16, 0)
    assert booking.trip_name == "Hurghada: City Tour & Bazaar with Optional Sand Museum Visit"
    assert booking.customer_name == "Ivon Schmied"
    assert booking.total_price == 93.75
    assert booking.currency == "EUR"
    assert booking.adt == 2
    assert booking.chd == 1
    assert booking.hotel_name == "Desert Rose Resort"

def test_date_with_image_artifact():
    text = load_fixture("create", "create_artifact_date.txt")
    booking = GetYourGuideParser.parse(text)
    
    assert booking.booking_number == "GYGDATEARTIF"
    # October 23, 2026 at 4:00 PM -> Should parse successfully despite '>>'
    assert booking.date_trip == datetime(2026, 10, 23, 16, 0)
    
def test_price_with_artifact():
    text = load_fixture("create", "create_artifact_price.txt")
    booking = GetYourGuideParser.parse(text)
    
    assert booking.booking_number == "GYGPRICEART"
    assert booking.total_price == 93.75
    assert booking.currency == "EUR"
    
def test_time_parsing():
    text = load_fixture("update", "update_time_only.txt")
    booking = GetYourGuideParser.parse(text)
    
    assert booking.operation == OperationType.UPDATE
    assert booking.booking_number == "GYGUPDATE1"
    # October 23, 2026, 6:00 PM
    assert booking.date_trip == datetime(2026, 10, 23, 18, 0)

def test_operation_detection_update():
    text = load_fixture("update", "update_date_change.txt")
    booking = GetYourGuideParser.parse(text)
    
    assert booking.operation == OperationType.UPDATE
    assert booking.booking_number == "GYGUPDATE2"
    assert booking.date_trip == datetime(2026, 10, 25, 16, 0)
    
def test_operation_detection_cancel():
    text = load_fixture("cancel", "cancel_normal.txt")
    booking = GetYourGuideParser.parse(text)
    
    assert booking.operation == OperationType.CANCEL
    assert booking.booking_number == "GYGCANCEL1"

def test_customer_boundaries():
    text = load_fixture("create", "create_normal.txt")
    booking = GetYourGuideParser.parse(text)
    
    assert booking.customer_name == "Ivon Schmied"
    assert booking.customer_email == "customer-642njiva65b7cpv6@reply.getyourguide.com"
    assert booking.customer_phone == "+491624326774"
    assert booking.option == "Hurghada: City Tour & Bazaar with Sand Museum Visit"

def test_booking_number():
    text = load_fixture("create", "create_normal.txt")
    booking = GetYourGuideParser.parse(text)
    assert booking.booking_number == "GYGN6BWBM54M"

def test_tour_language_tracking_url_ignored():
    text = load_fixture("create", "create_with_tour_language.txt")
    booking = GetYourGuideParser.parse(text)
    assert booking.booking_number == "GYG83W783H7V"
    assert booking.guide == "English"
    assert booking.total_price == 80.00
