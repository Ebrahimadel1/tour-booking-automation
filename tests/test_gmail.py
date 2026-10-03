import pytest
from datetime import datetime
from app.gmail.messages import GmailMessage
from tests.mocks.mock_gmail_client import MockGmailClient
from app.gmail.reader import GmailReader
from app.gmail.labels import GmailLabels
from app.logic.results import CreateResult
from app.logic.create import CreateLogic
from tests.mocks.mock_booking_repository import MockBookingRepository
from app.models.booking import NormalizedBooking
from app.models.operations import OperationType

@pytest.fixture
def mock_client():
    client = MockGmailClient()
    msg1 = GmailMessage(
        thread_id="t1", message_id="m1", subject="New Booking",
        sender="provider@example.com", received_at=datetime.now(),
        plain_text="content", html="html", labels=[]
    )
    msg2 = GmailMessage(
        thread_id="t2", message_id="m2", subject="Canceled",
        sender="provider@example.com", received_at=datetime.now(),
        plain_text="content", html="html", labels=[GmailLabels.BOOKING_PROCESSED]
    )
    client.messages["m1"] = msg1
    client.messages["m2"] = msg2
    return client

def test_reader_ignores_processed(mock_client):
    reader = GmailReader(mock_client, "provider@example.com")
    unprocessed = list(reader.get_unprocessed_bookings())
    
    assert len(unprocessed) == 1
    assert unprocessed[0].message_id == "m1"

def test_reader_marks_as_processed(mock_client):
    reader = GmailReader(mock_client, "provider@example.com")
    assert reader.mark_as_processed("m1")
    
    msg1 = mock_client.messages["m1"]
    assert GmailLabels.BOOKING_PROCESSED in msg1.labels

def test_reader_reprocesses_if_label_removed(mock_client):
    reader = GmailReader(mock_client, "provider@example.com")
    assert len(list(reader.get_unprocessed_bookings())) == 1
    
    label_id = mock_client.get_label_id(GmailLabels.BOOKING_PROCESSED)
    mock_client.remove_label("m2", label_id)
    
    unprocessed = list(reader.get_unprocessed_bookings())
    assert len(unprocessed) == 2
    
def test_mark_processed_missing_message(mock_client):
    reader = GmailReader(mock_client, "provider@example.com")
    assert not reader.mark_as_processed("invalid_id")

def test_manual_reprocessing_idempotent_duplicate():
    repo = MockBookingRepository()
    logic = CreateLogic(repo)
    
    booking = NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG_MANUAL",
        operation=OperationType.CREATE,
        date_trip=datetime(2026, 10, 23, 16, 0),
        trip_name="Test Trip",
        customer_name="John Doe",
        customer_email="john@example.com",
        customer_phone="+123",
        guide="English",
        total_price=10.0,
        currency="EUR",
        adt=1,
        chd=0,
        hotel_name=""
    )
    
    result = logic.execute(booking)
    assert result == CreateResult.CREATED
    
    result2 = logic.execute(booking)
    assert result2 == CreateResult.ALREADY_EXISTS
