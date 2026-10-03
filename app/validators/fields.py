import re
from typing import Optional

def is_valid_email(email: Optional[str]) -> bool:
    if not email:
        return False
    # Basic email format check without full RFC strictly
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()) is not None

def is_not_empty_string(value: Optional[str]) -> bool:
    if not value:
        return False
    return bool(value.strip())

def is_valid_price(price: Optional[float]) -> bool:
    if price is None:
        return False
    return price >= 0

def is_valid_participant_count(count: Optional[int]) -> bool:
    if count is None:
        return True # Considered valid if omitted/optional
    return count >= 0
