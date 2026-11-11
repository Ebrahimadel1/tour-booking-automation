import os
import glob
import email
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.models.operations import OperationType
from app.models.booking import NormalizedBooking, AirtableBookingRecord
from app.parsers.tripster import TripsterParser
from app.validators.booking import BookingValidator
from app.logic.create import CreateLogic
from app.logic.results import CreateResult
from app.main import Orchestrator, ProcessingStatus
from app.gmail.messages import GmailMessage
from app.gmail.google_client import GoogleGmailClient


def test_parse_eml_files():
    """Verify that all 3 downloaded Tripster .eml files parse correctly."""
    eml_files = glob.glob(r"c:\Users\aslam\Desktop\by_python\*.eml")
    tripster_emls = [f for f in eml_files if "Новый" in f]
    assert len(tripster_emls) >= 3, "Expected at least 3 Tripster .eml files"

    parsed_bookings = []
    for eml_path in tripster_emls:
        with open(eml_path, "rb") as f:
            msg = email.message_from_binary_file(f)
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_content = part.get_payload(decode=True).decode("utf-8", errors="replace")
                plain_text = GoogleGmailClient._html_to_text(html_content)
                booking = TripsterParser.parse(plain_text, html_content=html_content)
                parsed_bookings.append(booking)

    by_nr = {b.booking_number: b for b in parsed_bookings}

    # 1. Booking 7414909 (Dec 31, 20:30, 1 pax, sedan transfer)
    b1 = by_nr.get("7414909")
    assert b1 is not None
    assert b1.provider == "Tripster"
    assert b1.operation == OperationType.CREATE
    assert b1.date_trip.day == 31
    assert b1.date_trip.month == 12
    assert b1.date_trip.hour == 20
    assert b1.date_trip.minute == 30
    assert b1.customer_name == "Vladimir"
    assert b1.option == "Round-trip transfer: Sedan (1–3 persons)"
    assert b1.adt == 1
    assert b1.chd == 0
    assert b1.std == 0
    assert b1.inf == 0
    assert b1.youth == 0
    assert b1.total_price_usd == 70.0
    assert b1.collecting_usd == 54.0
    assert b1.booking_status == "PENDING"

    # 2. Booking 7406840 (Nov 7, 18:00, 2 pax, Excluding Transfer)
    b2 = by_nr.get("7406840")
    assert b2 is not None
    assert b2.customer_name == "Цветкова А."
    assert b2.option == "Excluding Transfer (Pickup & Drop-off)"
    assert b2.adt == 2
    assert b2.chd == 0
    assert b2.total_price_usd == 80.0
    assert b2.collecting_usd == 62.0
    assert b2.booking_status == "PENDING"

    # 3. Booking 7409111 (Nov 8, 18:00, 5 pax, minivan transfer)
    b3 = by_nr.get("7409111")
    assert b3 is not None
    assert b3.customer_name == "Екатерина"
    assert b3.option == "Round-trip transfer: Minivan (4–8 persons)"
    assert b3.adt == 5
    assert b3.chd == 0
    assert b3.total_price_usd == 240.0
    assert b3.collecting_usd == 185.0
    assert b3.booking_status == "PENDING"


def test_tripster_children_and_adults_parsing():
    """Verify parsing when children are present alongside adults."""
    sample_text = """
    Новый заказ
    На 6 ноября в 20:30 «Вечерний круиз по Нилу в Каире с ужином и шоу», №7310502.
    Светлана К.
    Путешественник
    6 ноя, пт 20:30—23:00
    4
    1 · Дети до 7 лет
    3 · Стандартный
    $145
    $34.2 на Трипстере
    $113 оплата вам
    """
    booking = TripsterParser.parse(sample_text)
    assert booking.booking_number == "7310502"
    assert booking.customer_name == "Светлана К."
    assert booking.option == "Excluding Transfer (Pickup & Drop-off)"
    assert booking.adt == 3
    assert booking.chd == 1
    assert booking.std == 0
    assert booking.inf == 0
    assert booking.youth == 0
    assert booking.total_price_usd == 145.0
    assert booking.collecting_usd == 113.0
    assert booking.booking_status == "PENDING"


def test_tripster_validator_passes_without_email_and_phone():
    """Tripster bookings must pass validation even when customer email and phone are absent."""
    booking = NormalizedBooking(
        provider="Tripster",
        booking_number="7409111",
        operation=OperationType.CREATE,
        date_trip=datetime(2026, 11, 8, 18, 0),
        trip_name="Cairo: Opal Nile Romantic Dinner Cruise & Live Entertainment",
        customer_name="Екатерина",
        customer_email=None,
        customer_phone=None,
        total_price=240.0,
        total_price_usd=240.0,
        collecting_usd=185.0,
        currency="USD",
        adt=5,
        booking_status="PENDING"
    )
    res = BookingValidator.validate(booking)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_tripster_create_logic_sets_zero_for_omitted_participants():
    """CreateLogic must populate all omitted counts with 0 and use PENDING status with USD prices."""
    mock_repo = MagicMock()
    mock_repo.find_by_booking_number.return_value = None
    mock_repo.create.return_value = True

    logic = CreateLogic(mock_repo)
    booking = NormalizedBooking(
        provider="Tripster",
        booking_number="7409111",
        operation=OperationType.CREATE,
        date_trip=datetime(2026, 11, 8, 18, 0),
        trip_name="Cairo: Opal Nile Romantic Dinner Cruise & Live Entertainment",
        customer_name="Екатерина",
        option="1 · Трансфер в обе стороны: минивэн (4–8 чел.)",
        total_price_usd=240.0,
        collecting_usd=185.0,
        currency="USD",
        adt=5,
        # std, chd, inf, youth left as None
        booking_status="PENDING"
    )

    result = logic.execute(booking)
    assert result == CreateResult.CREATED

    saved_record: AirtableBookingRecord = mock_repo.create.call_args[0][0]
    assert saved_record.agency == "Tripster"
    assert saved_record.booking_nr == "7409111"
    assert saved_record.booking_status == "PENDING"
    assert saved_record.total_price_eur is None
    assert saved_record.total_price_usd == 240.0
    assert saved_record.collecting_usd == 185.0
    assert saved_record.adt == 5
    assert saved_record.std == 0
    assert saved_record.chd == 0
    assert saved_record.inf == 0
    assert saved_record.youth == 0


def test_orchestrator_dispatches_tripster_email():
    """Orchestrator must recognize Tripster sender/label and dispatch to TripsterParser."""
    mock_reader = MagicMock()
    mock_repo = MagicMock()
    mock_repo.find_by_booking_number.return_value = None
    mock_repo.create.return_value = True

    sample_html = """
    <div>
      <h1>Новый заказ</h1>
      <p>На 8 ноября в 18:00 «Вечерний круиз по Нилу в Каире с ужином и шоу», №7409111.</p>
      <p>Екатерина</p>
      <p>Путешественник</p>
      <p>5 · Стандартный</p>
      <p>$240</p>
      <p>$58.6 на Трипстере</p>
      <p>$185 оплата вам</p>
    </div>
    """

    msg = GmailMessage(
        thread_id="t123",
        message_id="m123",
        subject="Новый заказ на 8 ноября в 18:00 · №7409111",
        sender="Tripster <support@tripster.ru>",
        received_at=datetime.now(),
        plain_text="",
        html=sample_html,
        labels=["Tripster Booking", "INBOX"]
    )
    mock_reader.get_unprocessed_bookings.return_value = [msg]
    mock_reader.mark_as_processed.return_value = True

    orchestrator = Orchestrator(gmail_reader=mock_reader, repository=mock_repo, dry_run=False)
    results = orchestrator.process_all()

    assert len(results) == 1
    assert results[0].status == ProcessingStatus.SUCCESS
    assert results[0].booking_number == "7409111"
    assert results[0].operation == OperationType.CREATE
    mock_repo.create.assert_called_once()
