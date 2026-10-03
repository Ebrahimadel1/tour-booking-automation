from typing import Dict, Any
from app.models.booking import NormalizedBooking, AirtableBookingRecord
from dateutil import parser

class ComparisonLogic:
    """
    Compares existing Airtable record with incoming normalized booking.
    Returns a dictionary of changed fields mapped to their Airtable aliases.
    """
    
    PROTECTED_FIELDS = {
        "Booking Nr.", 
        "Trip Name", 
        "Customer Name"
    }
    
    @staticmethod
    def compare(current: AirtableBookingRecord, incoming: NormalizedBooking) -> Dict[str, Any]:
        changed_fields = {}
        
        if incoming.date_trip is not None:
            incoming_dt = incoming.date_trip.replace(tzinfo=None)
            incoming_iso = incoming.date_trip.isoformat()
            
            if current.date_trip:
                try:
                    current_dt = parser.parse(current.date_trip).replace(tzinfo=None)
                    if current_dt != incoming_dt:
                        changed_fields["Date Trip"] = incoming_iso
                except Exception:
                    changed_fields["Date Trip"] = incoming_iso
            else:
                changed_fields["Date Trip"] = incoming_iso
                
        def check_optional_field(incoming_val, current_val, alias: str):
            if alias in ComparisonLogic.PROTECTED_FIELDS:
                return
            if incoming_val is not None and incoming_val != current_val:
                changed_fields[alias] = incoming_val

        check_optional_field(incoming.option, current.option, "Option")
        check_optional_field(incoming.guide, current.guide, "Guide")
        check_optional_field(incoming.total_price, current.total_price_eur, "Total price EUR")
        check_optional_field(incoming.adt, current.adt, "ADT")
        check_optional_field(incoming.chd, current.chd, "CHD")
        check_optional_field(incoming.hotel_name, current.hotel_name, "Hotel Name")
        check_optional_field(incoming.customer_email, current.customer_email, "Customer Email")
        check_optional_field(incoming.customer_phone, current.customer_phone, "Customer Phone")
        
        return changed_fields
