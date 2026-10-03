import re
from datetime import datetime
from dateutil import parser as dateutil_parser
from typing import Tuple, Optional

def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parses date and time robustly, ignoring artifacts like '>>' or '[image]'.
    """
    if not date_string:
        return None
        
    # Remove known artifacts
    cleaned = re.sub(r'>>|\[image.*?\]', '', date_string).strip()
    
    # dateutil's fuzzy=True is generally good at ignoring random text,
    # but we should ensure we don't have too much garbage.
    try:
        return dateutil_parser.parse(cleaned, fuzzy=True)
    except Exception:
        return None

def parse_price(price_string: str) -> Tuple[Optional[float], Optional[str]]:
    """Returns (amount, currency)"""
    if not price_string:
        return None, None
        
    cleaned = re.sub(r'>>|\[image.*?\]', '', price_string).strip()
    
    # Extract amount and currency. Examples: € 93.75, USD 120.00, EUR 93.75
    # Currency symbols: €|$|£ or 3 letters or 
    match = re.search(r'([€$£A-Z\ufffd]+)\s*([\d,\.]+)', cleaned)
    if match:
        currency = match.group(1).replace('\ufffd', 'EUR').replace('€', 'EUR')
        amount_str = match.group(2).replace(',', '')
        try:
            return float(amount_str), currency
        except ValueError:
            pass
    return None, None
