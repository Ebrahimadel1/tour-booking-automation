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

def test_update_hotel_and_google_maps(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    booking.hotel_name = "Old Hotel"
    booking.google_maps = "https://maps.google.com/old"
    create_logic.execute(booking)
    
    # Update with new hotel and new map link
    booking.operation = OperationType.UPDATE
    booking.hotel_name = "Nile Boutique Hotel"
    booking.google_maps = "https://mail.getyourguide.com/ls/click?upn=new"
    assert update_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.hotel_name == "Nile Boutique Hotel"
    assert saved.google_maps == "https://mail.getyourguide.com/ls/click?upn=new"

def test_create_and_update_with_infant(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    booking.inf = 1
    create_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.inf == 1
    
    booking.operation = OperationType.UPDATE
    booking.inf = 2
    assert update_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.inf == 2

def test_create_and_update_with_country(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    booking.country = "South Africa"
    create_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.country_from_phone == "South Africa"
    assert saved.customer_country == "South Africa"
    
    booking.operation = OperationType.UPDATE
    booking.country = "France"
    assert update_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.country_from_phone == "France"
    assert saved.customer_country == "France"


def test_create_and_update_with_add_ons(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    booking.add_ons = "2 x Round Trip Transportation (Per Person)"
    create_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.add_ons == "2 x Round Trip Transportation (Per Person)"
    
    booking.operation = OperationType.UPDATE
    booking.add_ons = "2 x Private Airport Transfer"
    assert update_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.add_ons == "2 x Private Airport Transfer"


def test_create_participant_counts_default_to_zero(repo):
    create_logic = CreateLogic(repo)
    booking = create_sample_normalized()
    # Explicitly set only ADT, leaving std, chd, inf, youth as None
    booking.adt = 2
    booking.std = None
    booking.chd = None
    booking.inf = None
    booking.youth = None
    
    result = create_logic.execute(booking)
    assert result == CreateResult.CREATED
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved is not None
    assert saved.adt == 2
    assert saved.std == 0
    assert saved.chd == 0
    assert saved.inf == 0
    assert saved.youth == 0
    
    # Check the dumped model for Airtable format
    dumped = saved.model_dump(by_alias=True, exclude_none=True)
    assert dumped["ADT"] == 2
    assert dumped["STD"] == 0
    assert dumped["CHD"] == 0
    assert dumped["Inf"] == 0
    assert dumped["Youth"] == 0


def test_update_participant_counts_std_and_youth(repo):
    create_logic = CreateLogic(repo)
    update_logic = UpdateLogic(repo)
    
    booking = create_sample_normalized()
    booking.adt = 2
    booking.std = None
    booking.chd = None
    booking.inf = None
    booking.youth = None
    create_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.std == 0
    assert saved.youth == 0
    
    # Update with youth and student
    booking.operation = OperationType.UPDATE
    booking.std = 1
    booking.youth = 2
    assert update_logic.execute(booking)
    
    saved = repo.find_by_booking_number("GYG123")
    assert saved.std == 1
    assert saved.youth == 2
    assert saved.adt == 2
    assert saved.chd == 0
    assert saved.inf == 0




