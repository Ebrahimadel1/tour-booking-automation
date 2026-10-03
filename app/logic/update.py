from app.models.booking import NormalizedBooking
from app.repositories.booking_repository import BookingRepository
from app.logic.comparison import ComparisonLogic

class UpdateLogic:
    def __init__(self, repository: BookingRepository):
        self.repo = repository
        
    def execute(self, booking: NormalizedBooking) -> bool:
        existing = self.repo.find_by_booking_number(booking.booking_number)
        if not existing:
            return False
            
        changed_fields = ComparisonLogic.compare(existing, booking)
        if not changed_fields:
            return True
            
        return self.repo.update(booking.booking_number, changed_fields)
