import re
from typing import Optional, List
from app.models.booking import NormalizedBooking
from app.models.operations import OperationType
from app.parsers.date_parser import parse_date, parse_price

class GetYourGuideParser:
    
    @staticmethod
    def detect_operation(text: str) -> OperationType:
        text_lower = text.lower()
        if "was cancelled" in text_lower or "has been canceled" in text_lower or "cancellation" in text_lower:
            return OperationType.CANCEL
        if "booking detail change" in text_lower or "booking has changed" in text_lower or "update" in text_lower or "modified" in text_lower:
            return OperationType.UPDATE
        if "your offer has been booked" in text_lower or "booking confirmed" in text_lower or "new booking" in text_lower:
            return OperationType.CREATE
        
        # Strict fallback
        if "booking nr" in text_lower or "reference number" in text_lower:
            return OperationType.CREATE
            
        return OperationType.CREATE # default if unknown but parser invoked

    @staticmethod
    def extract_field(text: str, current_label: str, next_labels: List[str]) -> Optional[str]:
        """
        Extracts text after `current_label` up to the first occurrence of any label in `next_labels` at the start of a line.
        Handles forwarded email quote marks (>, >>).
        """
        # Find position of current_label
        # Match label optionally preceded by newline and quote marks
        quote_prefix = r'(?:>[>\s]*)?'
        start_match = re.search(r'(?:^|\n)\s*' + quote_prefix + re.escape(current_label) + r'[\s:]*', text, re.IGNORECASE)
        if not start_match:
            # fallback to anywhere in text for certain fields like Booking Nr if not at start of line
            start_match = re.search(re.escape(current_label) + r'[\s:]*', text, re.IGNORECASE)
            if not start_match:
                return None
        
        start_idx = start_match.end()
        
        # Find the earliest next label after start_idx
        end_idx = len(text)
        for label in next_labels:
            # Match label at the beginning of a line (with optional quote marks)
            match = re.search(r'(?:^|\n)\s*' + quote_prefix + re.escape(label) + r'[\s:]*', text[start_idx:], re.IGNORECASE)
            if match:
                found_pos = start_idx + match.start()
                if found_pos < end_idx:
                    end_idx = found_pos
                    
        extracted = text[start_idx:end_idx].strip()
        # Clean up leading/trailing artifacts
        extracted = re.sub(r'^(?:>[>\s]*)+\s*|^\s*\[image.*?\]\s*', '', extracted, flags=re.MULTILINE).strip()
        return extracted if extracted else None

    @classmethod
    def parse(cls, text: str) -> NormalizedBooking:
        # Strip forwarded email headers to avoid matching 'Date:' from the header
        text = re.sub(r'---------- Forwarded message ---------.*?To:\s*[^\n]+\n', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Strip image tags that cause extraction artifacts
        text = re.sub(r'\[image:.*?\]', '', text, flags=re.IGNORECASE)
        
        operation = cls.detect_operation(text)
        
        all_labels = [
            "Booking Nr.", "Reference number", "Booking reference", "Date New", "Date", "Trip Name", "Tour", "Your offer has been booked:", "Option", 
            "Customer Name", "Name", "Main customer", "Customer Email", "Customer Phone", 
            "Guide", "Language", "Tour language", "Price", "Total price", 
            "Participants", "Number of participants", "Hotel Name", "Pickup location"
        ]
        
        def get_val(label: str) -> Optional[str]:
            next_labels = [l for l in all_labels if l != label]
            return cls.extract_field(text, label, next_labels)
            
        booking_nr = get_val("Booking Nr.") or get_val("Reference number") or get_val("Booking reference")
        if booking_nr:
            match = re.search(r'([A-Z0-9]{8,15})', booking_nr.replace('*', ''))
            if match:
                booking_nr = match.group(1).strip()
        if not booking_nr:
            # Strict inline check including CANCEL format (Reference Number: GYG...)
            match = re.search(r'(?:Booking Nr\.|Reference number|Booking reference)\s*:\s*([A-Z0-9]+)', text, re.IGNORECASE)
            if match:
                booking_nr = match.group(1).strip()
            else:
                raise ValueError("Could not find Booking Nr.")
                
        date_str = get_val("Date New") or get_val("Date")
        if date_str:
            # If multiple dates (e.g. New Date then Old Date), take the first line
            date_str = date_str.split('\n')[0].replace('*', '').strip()
            # Also handle inline 'Date: October 15...'
            if date_str.lower().startswith("date:"):
                date_str = date_str[5:].strip()
        date_obj = parse_date(date_str) if date_str else None
        
        trip_name = get_val("Trip Name") or get_val("Tour") or get_val("Your offer has been booked:")
        if trip_name:
            if trip_name.lower().startswith("tour:"):
                trip_name = trip_name[5:].strip()
            trip_name = trip_name.split('\n')[0].strip()
        option = get_val("Option")
        if not option and get_val("Your offer has been booked:"):
            raw_booked = get_val("Your offer has been booked:")
            opt_match = re.search(r'(Option\s*\d+\s*-.*?)(?:\n|$)', raw_booked, re.IGNORECASE)
            if opt_match: 
                option = opt_match.group(1).strip()
            else:
                lines = [line.strip() for line in raw_booked.split('\n') if line.strip() and not line.startswith('[image:')]
                if len(lines) >= 2:
                    option = lines[1]
                    
        customer_name = get_val("Customer Name") or get_val("Name") or get_val("Main customer")
        if customer_name:
            if customer_name.lower().startswith("name:"):
                customer_name = customer_name[5:].strip()
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
                guide = re.sub(r'\(.*?\)', '', line).replace('*', '').strip()
                if not guide:
                    guide = None
                break
        price_str = get_val("Total price") or get_val("Price")
        total_price, currency = parse_price(price_str) if price_str else (None, None)
        
        participants_str = get_val("Participants") or get_val("Number of participants")
        adt, chd = None, None
        if participants_str:
            participants_clean = participants_str.replace('*', '')
            adt_match = re.search(r'(\d+)\s*(?:x\s*)?(?:Adult|Adults)', participants_clean, re.IGNORECASE)
            chd_match = re.search(r'(\d+)\s*(?:x\s*)?(?:Child|Children)', participants_clean, re.IGNORECASE)
            if adt_match:
                adt = int(adt_match.group(1))
            if chd_match:
                chd = int(chd_match.group(1))
            # Fallback for just a number e.g. "2"
            if adt is None and chd is None:
                just_num = re.search(r'^(\d+)$', participants_clean.strip())
                if just_num:
                    adt = int(just_num.group(1))
                
        hotel_name = get_val("Hotel Name") or get_val("Pickup location")
        # In GYG update emails, it might be labeled as "Pickup location"
        if hotel_name:
            if hotel_name.startswith("New\n"):
                hotel_name = hotel_name[4:].strip()
            elif hotel_name.startswith("New "):
                hotel_name = hotel_name[4:].strip()
            
            # Clean up common appended texts from plain text emails
            hotel_name = hotel_name.replace("Open in Google Maps", "").strip()
            if "Customer hasn't specified a pickup location" in hotel_name:
                hotel_name = hotel_name.split("Customer hasn't specified a pickup location")[0].strip()
            if "Customer hasn't" in hotel_name and "specified a pickup" in hotel_name:
                hotel_name = hotel_name.split("Customer hasn't")[0].strip()
        
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
