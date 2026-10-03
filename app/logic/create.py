from app.models.booking import NormalizedBooking, AirtableBookingRecord
from app.repositories.booking_repository import BookingRepository
from app.logic.results import CreateResult

class CreateLogic:
    def __init__(self, repository: BookingRepository):
        self.repo = repository
        
    def execute(self, booking: NormalizedBooking) -> CreateResult:
        existing = self.repo.find_by_booking_number(booking.booking_number)
        if existing:
            return CreateResult.ALREADY_EXISTS
            
        record = AirtableBookingRecord(
            agency=booking.provider,
            booking_nr=booking.booking_number,
            date_trip=booking.date_trip.isoformat() if booking.date_trip else None,
            trip_name=booking.trip_name,
            option=booking.option,
            customer_name=booking.customer_name,
            customer_email=booking.customer_email,
            customer_phone=booking.customer_phone,
            guide=booking.guide,
            total_price_eur=booking.total_price,
            adt=booking.adt,
            chd=booking.chd,
            hotel_name=booking.hotel_name,
            booking_status="Active"
        )
        success = self.repo.create(record)
        return CreateResult.CREATED if success else CreateResult.FAILED
