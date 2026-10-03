import os
import requests
from typing import Optional, Dict, Any
from app.models.booking import AirtableBookingRecord
from app.repositories.booking_repository import BookingRepository

class AirtableRepository(BookingRepository):
    def __init__(self, base_id: str = None, table_name: str = None, token: str = None):
        self.base_id = base_id or os.getenv("AIRTABLE_BASE_ID")
        self.table_name = table_name or os.getenv("AIRTABLE_TABLE_NAME")
        self.token = token or os.getenv("AIRTABLE_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        # In a real scenario, base_id and table_name shouldn't be None. 
        # Defaulting them prevents immediate crashes on import if not passed.
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}/{self.table_name}" if self.base_id and self.table_name else ""
        
    def find_by_booking_number(self, booking_nr: str) -> Optional[AirtableBookingRecord]:
        params = {
            "filterByFormula": f"{{Booking Nr.}} = '{booking_nr}'",
            "maxRecords": 1
        }
        response = requests.get(self.base_url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("records"):
            return None
            
        record_data = data["records"][0]["fields"]
        return AirtableBookingRecord(**record_data)

    def create(self, record: AirtableBookingRecord) -> bool:
        fields = record.model_dump(by_alias=True, exclude_none=True)
        payload = {
            "records": [
                {
                    "fields": fields
                }
            ],
            "typecast": True
        }
        response = requests.post(self.base_url, headers=self.headers, json=payload)
        response.raise_for_status()
        return True

    def update(self, booking_nr: str, changed_fields: Dict[str, Any]) -> bool:
        # We need the record ID to PATCH in Airtable. Fetch it first.
        params = {
            "filterByFormula": f"{{Booking Nr.}} = '{booking_nr}'",
            "maxRecords": 1
        }
        response = requests.get(self.base_url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("records"):
            return False
            
        record_id = data["records"][0]["id"]
        
        payload = {
            "records": [
                {
                    "id": record_id,
                    "fields": changed_fields
                }
            ],
            "typecast": True
        }
        
        patch_response = requests.patch(self.base_url, headers=self.headers, json=payload)
        patch_response.raise_for_status()
        return True
