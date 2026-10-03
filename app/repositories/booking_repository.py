from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.models.booking import AirtableBookingRecord

class BookingRepository(ABC):
    
    @abstractmethod
    def find_by_booking_number(self, booking_nr: str) -> Optional[AirtableBookingRecord]:
        """Finds a booking by its Booking Nr."""
        pass
        
    @abstractmethod
    def create(self, record: AirtableBookingRecord) -> bool:
        """Creates a new booking record."""
        pass
        
    @abstractmethod
    def update(self, booking_nr: str, changed_fields: Dict[str, Any]) -> bool:
        """Updates an existing booking record with only the changed fields."""
        pass
