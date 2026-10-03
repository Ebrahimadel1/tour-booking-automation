from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.operations import OperationType

class NormalizedBooking(BaseModel):
    """
    Internal normalized representation of a parsed booking email.
    """
    provider: str
    booking_number: str
    operation: OperationType
    
    date_trip: Optional[datetime] = None
    trip_name: Optional[str] = None
    option: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    guide: Optional[str] = None
    total_price: Optional[float] = None
    currency: Optional[str] = None
    adt: Optional[int] = None
    chd: Optional[int] = None
    hotel_name: Optional[str] = None

class AirtableBookingRecord(BaseModel):
    """
    Representation of the record for Airtable interactions.
    Fields correspond exactly to Airtable column names as per specification.
    """
    model_config = ConfigDict(populate_by_name=True)
    
    agency: Optional[str] = Field(None, alias="Agency")
    booking_nr: Optional[str] = Field(None, alias="Booking Nr.")
    date_trip: Optional[str] = Field(None, alias="Date Trip")
    trip_name: Optional[str] = Field(None, alias="Trip Name")
    option: Optional[str] = Field(None, alias="Option")
    customer_name: Optional[str] = Field(None, alias="Customer Name")
    customer_email: Optional[str] = Field(None, alias="Customer Email")
    customer_phone: Optional[str] = Field(None, alias="Customer Phone")
    guide: Optional[str] = Field(None, alias="Guide")
    total_price_eur: Optional[float] = Field(None, alias="Total price EUR")
    adt: Optional[int] = Field(None, alias="ADT")
    chd: Optional[int] = Field(None, alias="CHD")
    hotel_name: Optional[str] = Field(None, alias="Hotel Name")
    booking_status: Optional[str] = Field(None, alias="Booking Status")
