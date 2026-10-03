from typing import Optional, Dict, Any
from app.models.booking import AirtableBookingRecord
from app.repositories.booking_repository import BookingRepository

class MockBookingRepository(BookingRepository):
    def __init__(self):
        self.records: Dict[str, AirtableBookingRecord] = {}
        
    def find_by_booking_number(self, booking_nr: str) -> Optional[AirtableBookingRecord]:
        return self.records.get(booking_nr)
        
    def create(self, record: AirtableBookingRecord) -> bool:
        if record.booking_nr in self.records:
            return False
        self.records[record.booking_nr] = record
        return True
        
    def update(self, booking_nr: str, changed_fields: Dict[str, Any]) -> bool:
        if booking_nr not in self.records:
            return False
            
        record = self.records[booking_nr]
        
        # model_dump with by_alias gives us the dict with "Date Trip", etc.
        current_data = record.model_dump(by_alias=True)
        current_data.update(changed_fields)
        
        self.records[booking_nr] = AirtableBookingRecord(**current_data)
        return True
