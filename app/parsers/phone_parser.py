from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_country_from_phone(phone: Optional[str]) -> Optional[str]:
    """
    Extracts the English country name from an international phone number.
    e.g. "+27842613320" -> "South Africa"
    """
    if not phone:
        return None
        
    clean_phone = phone.strip()
    if clean_phone.startswith("00"):
        clean_phone = "+" + clean_phone[2:]
    elif not clean_phone.startswith("+"):
        clean_phone = "+" + clean_phone
        
    try:
        import phonenumbers
        from phonenumbers import geocoder
        
        parsed = phonenumbers.parse(clean_phone, None)
        country = geocoder.country_name_for_number(parsed, "en")
        return country or None
    except Exception as e:
        logger.debug(f"Failed to resolve country for phone {phone}: {e}")
        return None
