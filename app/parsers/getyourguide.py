import re
from typing import Optional, List
from app.models.booking import NormalizedBooking
from app.models.operations import OperationType
from app.parsers.date_parser import parse_date, parse_price

class GetYourGuideParser:
    
    @staticmethod
    def detect_operation(text: str) -> OperationType:
        text_lower = text.lower()
        if "has been canceled" in text_lower or "cancelled" in text_lower or "cancellation" in text_lower:
            return OperationType.CANCEL
        if "detail change" in text_lower or "update" in text_lower or "modified" in text_lower:
            return OperationType.UPDATE
        if "booking confirmed" in text_lower or "new booking" in text_lower:
            return OperationType.CREATE
        
        # Strict fallback
        if "booking nr" in text_lower:
            return OperationType.CREATE
            
        return OperationType.CREATE # default if unknown but parser invoked

    @staticmethod
    def extract_field(text: str, current_label: str, next_labels: List[str]) -> Optional[str]:
        """
        Extracts text after `current_label` up to the first occurrence of any label in `next_labels` at the start of a line.
        """
        # Find position of current_label
        # Match label optionally preceded by newline
        start_match = re.search(r'(?:^|\n)\s*' + re.escape(current_label) + r'[\s:]*', text, re.IGNORECASE)
        if not start_match:
            # fallback to anywhere in text for certain fields like Booking Nr if not at start of line
            start_match = re.search(re.escape(current_label) + r'[\s:]*', text, re.IGNORECASE)
            if not start_match:
                return None
        
        start_idx = start_match.end()
        
        # Find the earliest next label after start_idx
        end_idx = len(text)
        for label in next_labels:
            # Match label at the beginning of a line
            match = re.search(r'(?:^|\n)\s*' + re.escape(label) + r'[\s:]*', text[start_idx:], re.IGNORECASE)
            if match:
                found_pos = start_idx + match.start()
                if found_pos < end_idx:
                    end_idx = found_pos
                    
        extracted = text[start_idx:end_idx].strip()
        # Clean up leading/trailing artifacts
        extracted = re.sub(r'^>>\s*|^\s*\[image.*?\]\s*', '', extracted, flags=re.MULTILINE).strip()
        return extracted if extracted else None

    @classmethod
    def parse(cls, text: str) -> NormalizedBooking:
        operation = cls.detect_operation(text)
        
        all_labels = [
            "Booking Nr.", "Reference number", "Date", "Trip Name", "Your offer has been booked:", "Option", 
            "Customer Name", "Main customer", "Customer Email", "Customer Phone", 
            "Guide", "Language", "Tour language", "Price", "Total price", 
            "Participants", "Number of participants", "Hotel Name"
        ]
        
        def get_val(label: str) -> Optional[str]:
            next_labels = [l for l in all_labels if l != label]
            return cls.extract_field(text, label, next_labels)
            
        booking_nr = get_val("Booking Nr.") or get_val("Reference number")
        if booking_nr:
            match = re.search(r'([A-Z0-9]{8,15})', booking_nr.replace('*', ''))
            if match:
                booking_nr = match.group(1).strip()
        if not booking_nr:
            # Strict inline check
            match = re.search(r'(?:Booking Nr\.|Reference number)\s*:\s*([A-Z0-9]+)', text, re.IGNORECASE)
            if match:
                booking_nr = match.group(1).strip()
            else:
                raise ValueError("Could not find Booking Nr.")
                
        date_str = get_val("Date")
        if date_str:
            date_str = date_str.replace('*', '').strip()
        date_obj = parse_date(date_str) if date_str else None
        
        trip_name = get_val("Trip Name") or get_val("Your offer has been booked:")
        if trip_name:
            trip_name = trip_name.split('\n')[0].strip()
        option = get_val("Option")
        if not option and get_val("Your offer has been booked:"):
            opt_match = re.search(r'(Option\s*\d+\s*-.*?)(?:\n|$)', get_val("Your offer has been booked:"), re.IGNORECASE)
            if opt_match: option = opt_match.group(1).strip()
        customer_name = get_val("Customer Name") or get_val("Main customer")
        if customer_name:
            customer_name = customer_name.split('\n')[0].strip() # Take only first line in case email/phone are on next lines
        customer_email = get_val("Customer Email")
        if not customer_email and get_val("Main customer"):
            em_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', get_val("Main customer"))
            if em_match: customer_email = em_match.group(1).strip()
            
        customer_phone = get_val("Customer Phone")
        if not customer_phone and get_val("Main customer"):
            ph_match = re.search(r'Phone:\s*([+\d\s]+)', get_val("Main customer"), re.IGNORECASE)
            if ph_match: customer_phone = ph_match.group(1).strip()
            
        # Prioritize 'Tour language' to avoid 'Guide' falsely matching 'getyourguide.com'
        guide_raw = get_val("Tour language") or get_val("Guide") or get_val("Language")
        guide = None
        if guide_raw:
            for line in guide_raw.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Skip tracking URLs, email addresses, and metadata artifacts
                if "http" in line or "ls/click" in line or ".com" in line or "@" in line or "Phone:" in line:
                    continue
                # Found the actual language line
                guide = re.sub(r'\(.*?\)', '', line).strip()
                if not guide:
                    guide = None
                break
        price_str = get_val("Total price") or get_val("Price")
        total_price, currency = parse_price(price_str) if price_str else (None, None)
        
        participants_str = get_val("Participants") or get_val("Number of participants")
        adt, chd = None, None
        if participants_str:
            adt_match = re.search(r'(\d+)\s*(?:x\s*)?(?:Adult|Adults)', participants_str, re.IGNORECASE)
            chd_match = re.search(r'(\d+)\s*(?:x\s*)?(?:Child|Children)', participants_str, re.IGNORECASE)
            if adt_match:
                adt = int(adt_match.group(1))
            if chd_match:
                chd = int(chd_match.group(1))
                
        hotel_name = get_val("Hotel Name")
        
        return NormalizedBooking(
            provider="GetYourGuide",
            booking_number=booking_nr,
            operation=operation,
            date_trip=date_obj,
            trip_name=trip_name,
            option=option,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            guide=guide,
            total_price=total_price,
            currency=currency,
            adt=adt,
            chd=chd,
            hotel_name=hotel_name
        )
