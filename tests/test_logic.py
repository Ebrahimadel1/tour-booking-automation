import pytest
from datetime import datetime
from app.models.booking import NormalizedBooking, AirtableBookingRecord
from app.models.operations import OperationType
from tests.mocks.mock_booking_repository import MockBookingRepository
from app.logic.create import CreateLogic
from app.logic.update import UpdateLogic
from app.logic.cancel import CancelLogic
from app.logic.comparison import ComparisonLogic

@pytest.fixture
def repo():
    return MockBookingRepository()

def create_sample_normalized(op=OperationType.CREATE, date_dt=datetime(2026, 10, 23, 16, 0)):
    return NormalizedBooking(
        provider="GetYourGuide",
        booking_number="GYG123",
        operation=op,
        date_trip=date_dt,
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

from app.logic.results import CreateResult

def test_create_new_booking(repo):
    logic = CreateLogic(repo)
    booking = create_sample_normalized()
    result = logic.execute(booking)
    assert result == CreateResult.CREATED
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved is not None
    assert saved.booking_status == "Active"
    assert saved.agency == "GetYourGuide"
    assert saved.date_trip == "2026-10-23T16:00:00"

def test_create_duplicate_idempotent(repo):
    logic = CreateLogic(repo)
    booking = create_sample_normalized()
    logic.execute(booking)
    
    result = logic.execute(booking)
    assert result == CreateResult.ALREADY_EXISTS

def test_update_missing_booking(repo):
    logic = UpdateLogic(repo)
    booking = create_sample_normalized(OperationType.UPDATE)
    assert not logic.execute(booking)

def test_update_no_changes(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    create_logic.execute(booking)
    
    booking.operation = OperationType.UPDATE
    assert update_logic.execute(booking) 
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.date_trip == "2026-10-23T16:00:00"

def test_update_time_only_change(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    create_logic.execute(booking)
    
    booking.operation = OperationType.UPDATE
    booking.date_trip = datetime(2026, 10, 23, 18, 0)
    assert update_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.date_trip == "2026-10-23T18:00:00"

def test_update_date_change(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    create_logic.execute(booking)
    
    booking.operation = OperationType.UPDATE
    booking.date_trip = datetime(2026, 10, 24, 16, 0) 
    assert update_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.date_trip == "2026-10-24T16:00:00"

def test_update_protected_fields_remain(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    create_logic.execute(booking)
    
    booking.operation = OperationType.UPDATE
    booking.customer_name = "Jane Doe" 
    booking.trip_name = "Another Trip" 
    assert update_logic.execute(booking) 
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.customer_name == "John Doe"
    assert saved.trip_name == "Test Trip"

def test_cancel_missing_booking(repo):
    logic = CancelLogic(repo)
    booking = create_sample_normalized(OperationType.CANCEL)
    assert not logic.execute(booking)

def test_cancel_existing_booking(repo):
    create_logic = CreateLogic(repo)
    cancel_logic = CancelLogic(repo)
    
    booking = create_sample_normalized()
    create_logic.execute(booking)
    
    booking.operation = OperationType.CANCEL
    assert cancel_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.booking_status == "Canceled"
    assert saved.customer_name == "John Doe" 

def test_cancel_idempotent(repo):
    create_logic = CreateLogic(repo)
    cancel_logic = CancelLogic(repo)
    
    booking = create_sample_normalized()
    create_logic.execute(booking)
    
    booking.operation = OperationType.CANCEL
    cancel_logic.execute(booking)
    assert cancel_logic.execute(booking)
