import os
import json
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai
from pydantic import BaseModel, Field

from app.models.booking import NormalizedBooking

logger = logging.getLogger(__name__)

class ExtractedBookingData(BaseModel):
    booking_number: Optional[str] = Field(None, description="The booking reference number (e.g. GYG...).")
    hotel_name: Optional[str] = Field(None, description="The hotel name or pickup location mentioned in the message.")
    customer_name: Optional[str] = Field(None, description="The customer's name, if explicitly stated.")
    customer_email: Optional[str] = Field(None, description="The customer's email address, if stated.")
    customer_phone: Optional[str] = Field(None, description="The customer's phone number, if stated.")
    adt: Optional[int] = Field(None, description="The number of adult participants.")
    chd: Optional[int] = Field(None, description="The number of child participants.")
    option: Optional[str] = Field(None, description="The specific tour option requested.")
    guide: Optional[str] = Field(None, description="The requested guide language.")
    message: Optional[str] = Field(None, description="A summary of the customer's message or request.")

class GeminiService:

    @staticmethod
    def enhance_booking(booking: NormalizedBooking, raw_text: str, is_customer_message: bool) -> NormalizedBooking:
        """
        Uses Gemini to extract missing or updated fields from unstructured text (like a customer message)
        and merges them into the booking object.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. Skipping AI enhancement.")
            return booking
            
        genai.configure(api_key=api_key)

        prompt = (
            "You are an AI assistant that extracts tour booking data from emails.\n"
            f"The email is a {'customer message/update' if is_customer_message else 'booking notification'}.\n"
            "Extract any relevant information that might be an update or missing from standard parsing.\n"
            "If the customer is asking to change their pickup location or hotel, extract it as hotel_name.\n"
            "Return ONLY a JSON object that matches the schema provided.\n\n"
            f"--- EMAIL TEXT ---\n{raw_text}\n--- END EMAIL TEXT ---"
        )

        try:
            model = genai.GenerativeModel('gemini-3.8-flash', generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1
            })
            response = model.generate_content(prompt)
            data = json.loads(response.text)

            
            # Merge extracted data into booking
            if data.get("booking_number") and not booking.booking_number:
                booking.booking_number = data["booking_number"]
            if data.get("hotel_name"):
                booking.hotel_name = data["hotel_name"]
            if data.get("customer_name") and not booking.customer_name:
                booking.customer_name = data["customer_name"]
            if data.get("customer_email") and not booking.customer_email:
                booking.customer_email = data["customer_email"]
            if data.get("customer_phone") and not booking.customer_phone:
                booking.customer_phone = data["customer_phone"]
            if data.get("adt") and not booking.adt:
                booking.adt = data["adt"]
            if data.get("chd") and not booking.chd:
                booking.chd = data["chd"]
            if data.get("option") and not booking.option:
                booking.option = data["option"]
            if data.get("guide") and not booking.guide:
                booking.guide = data["guide"]
                
            logger.info(f"AI enhanced booking {booking.booking_number} with data: {data}")
            
        except Exception as e:
            logger.error(f"Gemini AI extraction failed: {str(e)}")

        return booking
