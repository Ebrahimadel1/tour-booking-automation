from dataclasses import dataclass, field
from typing import List
from app.models.booking import NormalizedBooking
from app.models.operations import OperationType
from app.validators.fields import (
    is_valid_email, 
    is_not_empty_string, 
    is_valid_price, 
    is_valid_participant_count
)

@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, msg: str):
        self.errors.append(msg)
        self.is_valid = False
        
    def add_warning(self, msg: str):
        self.warnings.append(msg)

class BookingValidator:
    """
    Validates a NormalizedBooking object based on business rules for CREATE, UPDATE, CANCEL.
    Does NOT mutate the input object. Does NOT interact with Airtable.
    """
    
    @staticmethod
    def validate(booking: NormalizedBooking) -> ValidationResult:
        result = ValidationResult()
        
        # General checks for all operations
        if not is_not_empty_string(booking.booking_number):
            result.add_error("booking_number: required field is missing or empty")
            
        if booking.operation == OperationType.CREATE:
            BookingValidator._validate_create(booking, result)
        elif booking.operation == OperationType.UPDATE:
            BookingValidator._validate_update(booking, result)
        elif booking.operation == OperationType.CANCEL:
            BookingValidator._validate_cancel(booking, result)
        else:
            result.add_error("operation: unknown or missing operation type")
            
        return result

    @staticmethod
    def _validate_create(booking: NormalizedBooking, result: ValidationResult):
        if booking.date_trip is None:
            result.add_error("date_trip: required field is missing for CREATE")
            
        if not is_not_empty_string(booking.trip_name):
            result.add_error("trip_name: required field is missing for CREATE")
            
        if not is_not_empty_string(booking.customer_name):
            result.add_error("customer_name: required field is missing for CREATE")
            
        if not is_valid_email(booking.customer_email):
            result.add_error("customer_email: invalid email format")
            
        if not is_not_empty_string(booking.customer_phone):
            result.add_error("customer_phone: required field is missing for CREATE")
            
        if not is_not_empty_string(booking.guide):
            result.add_warning("guide: missing optional field")
            
        if not is_valid_price(booking.total_price):
            result.add_error("total_price: missing or negative")
            
        if booking.total_price is not None and not is_not_empty_string(booking.currency):
            result.add_error("currency: missing while price is provided")
            
        if not is_valid_participant_count(booking.adt):
            result.add_error("adt: cannot be negative")
            
        if not is_valid_participant_count(booking.chd):
            result.add_error("chd: cannot be negative")
            
        if booking.adt is None and booking.chd is None:
            result.add_warning("participants: no adults or children specified")

        if not is_not_empty_string(booking.hotel_name):
            result.add_warning("hotel_name: missing optional field")

    @staticmethod
    def _validate_update(booking: NormalizedBooking, result: ValidationResult):
        # In UPDATE, missing fields are fine (they just won't be updated).
        # However, IF they are present, they must be valid.
        if booking.customer_email is not None and not is_valid_email(booking.customer_email):
            result.add_error("customer_email: invalid email format")
            
        if booking.total_price is not None:
            if not is_valid_price(booking.total_price):
                result.add_error("total_price: negative value is invalid")
            if not is_not_empty_string(booking.currency):
                result.add_error("currency: missing while price is provided")
                
        if booking.adt is not None and not is_valid_participant_count(booking.adt):
            result.add_error("adt: cannot be negative")
            
        if booking.chd is not None and not is_valid_participant_count(booking.chd):
            result.add_error("chd: cannot be negative")
            
        # Optional warnings for missing data in updates? Not strictly necessary since updates can be sparse.
        
    @staticmethod
    def _validate_cancel(booking: NormalizedBooking, result: ValidationResult):
        # CANCEL only strictly requires booking_number and operation type, which are already checked globally.
        # It's completely fine if everything else is missing.
        pass
