from app.models.booking import NormalizedBooking
from app.repositories.booking_repository import BookingRepository

class CancelLogic:
    def __init__(self, repository: BookingRepository):
        self.repo = repository
        
    def execute(self, booking: NormalizedBooking) -> bool:
        existing = self.repo.find_by_booking_number(booking.booking_number)
        if not existing:
            return False
            
        if existing.booking_status == "Canceled":
            return True
            
        return self.repo.update(booking.booking_number, {"Booking Status": "Canceled"})
