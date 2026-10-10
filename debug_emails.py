import os
from dotenv import load_dotenv
from app.gmail.google_client import GoogleGmailClient
from app.parsers.getyourguide import GetYourGuideParser

load_dotenv()
client = GoogleGmailClient()
msg_ids = ["1a11fbb7e8d45c73", "1a11fbbfb44367d3", "1a11fbca65573e61", "1a11fbcf1a325e83"]

for msg_id in msg_ids:
    print(f"\n--- Processing {msg_id} ---")
    msg = client.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    text, _ = GoogleGmailClient._extract_bodies(msg['payload'])
    print("PLAIN TEXT FIRST 500 CHARS:")
    print(text[:500])
    print("...")
    print("PARSING RESULTS:")
    try:
        booking = GetYourGuideParser.parse(text)
        print(f"Booking Nr: {booking.booking_number}")
        print(f"Operation: {booking.operation}")
        print(f"Trip Name: {booking.trip_name}")
        print(f"Option: {booking.option}")
        print(f"Guide: {booking.guide}")
        print(f"Hotel Name: {booking.hotel_name}")
        
        all_labels = [
            "Booking Nr.", "Reference number", "Booking reference", "Date New", "Date", "Trip Name", "Tour", "Your offer has been booked:", "You've received a last-minute booking:", "Option", 
            "Customer Name", "Name", "Main customer", "Customer Email", "Customer Phone", 
            "Guide", "Language", "Tour language", "Price", "Total price", 
            "Participants", "Number of participants", "Hotel Name", "Pickup location", "Pickup"
        ]
        
        def test_get_val(label):
            next_labels = [l for l in all_labels if l != label]
            return GetYourGuideParser.extract_field(text, label, next_labels)
            
        print("RAW Tour language:", repr(test_get_val("Tour language")))
        print("RAW Pickup location:", repr(test_get_val("Pickup location")))
        print("RAW Pickup:", repr(test_get_val("Pickup")))
    except Exception as e:
        import traceback
        traceback.print_exc()
