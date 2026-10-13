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

def test_update_real():
    text = load_fixture("update", "update_real.txt")
    booking = GetYourGuideParser.parse(text)
    assert booking.operation == OperationType.UPDATE
    assert booking.booking_number == "GYG83W783H7V"
    assert booking.date_trip == datetime(2026, 10, 15, 20, 0)
    assert booking.adt == 2
    assert booking.guide == "English"

def test_cancel_real():
    text = load_fixture("cancel", "cancel_real.txt")
    booking = GetYourGuideParser.parse(text)
    assert booking.operation == OperationType.CANCEL
    assert booking.booking_number == "GYG83W783H7V"
    assert booking.trip_name == "Cairo: Opal Nile Romantic Dinner Cruise & Live Entertainment"
    assert booking.customer_name == "Shangar Sentharajah"
    assert booking.date_trip == datetime(2026, 10, 15, 20, 0)

def test_hotel_and_google_maps_separation():
    raw_email = """
Booking confirmed
Booking Nr.: GYG999TEST
Date
October 23, 2026, 4:00 PM
Trip Name
Hurghada: City Tour
Option
Standard Option
Customer Name
John Doe
Customer Email
john@example.com
Customer Phone
+20123456789
Price
€ 100.00
Hotel Name
— Nile Boutique Hotel, Nile Street, Al Agouzah, Agouza, Egypt <https://mail.getyourguide.com/ls/click?upn=u001.maps.google.com%2Ftest>
"""
    booking = GetYourGuideParser.parse(raw_email)
    assert booking.hotel_name == "Nile Boutique Hotel, Nile Street, Al Agouzah, Agouza, Egypt"
    assert booking.google_maps == "https://mail.getyourguide.com/ls/click?upn=u001.maps.google.com%2Ftest"

def test_pickup_location_with_open_in_google_maps():
    raw_email = """
Booking detail change: - S707722 - GYGN6BWBM54M
Booking reference
*GYGN6BWBM54M*
Date
October 23, 2026 at 4:00 PM
Pickup location New
Pickalbatros Jungle Aqua Park Resort - Neverland Hurghada, Al Ismaileya,
Hurghada 1, Ägypten
(coordinates: 27.0886061, 33.8257797)
Open in Google Maps
<https://mail.getyourguide.com/ls/click?upn=u001.cgvWDPhZtte8w9SmEnPFbJpEukibyIP5>
Customer hasn't specified a pickup location. We will remind them to specify a location.
Number of participants
3
Language
German
"""
    booking = GetYourGuideParser.parse(raw_email)
    assert "Open in Google Maps" not in (booking.hotel_name or "")
    assert "https://" not in (booking.hotel_name or "")
    assert "Pickalbatros Jungle Aqua Park Resort" in booking.hotel_name
    assert booking.google_maps == "https://mail.getyourguide.com/ls/click?upn=u001.cgvWDPhZtte8w9SmEnPFbJpEukibyIP5"

def test_main_customer_isolation_and_infant_participants():
    raw_email = """
Hi Supply Partner, great news!
You've received a last-minute booking:

Cairo: Opal Nile Romantic Dinner Cruise & Live Entertainment
Excluding Transfer (Pickup & Drop-off)

Reference number
GYG996RG4VG7

Date
October 13, 2026, 6:00 PM

Number of participants
1 x Infant (Age 0 - 4)
2 x Adults (Age 10 - 99)

Main customer
— Ziyaad Khan customer-37g3geb2kjsxlnlv@reply.getyourguide.com Phone: +27842613320 Language: English

Tour language
English (Live guide)

Price
€ 80.00
"""
    booking = GetYourGuideParser.parse(raw_email)
    assert booking.booking_number == "GYG996RG4VG7"
    assert booking.customer_name == "Ziyaad Khan"
    assert booking.customer_email == "customer-37g3geb2kjsxlnlv@reply.getyourguide.com"
    assert booking.customer_phone == "+27842613320"
    assert booking.guide == "English"
    assert booking.adt == 2
    assert booking.inf == 1
    assert booking.country == "South Africa"
    assert booking.total_price == 80.0


