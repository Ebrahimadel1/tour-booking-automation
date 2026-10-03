from typing import Iterator
from app.gmail.client import GmailClient
from app.gmail.messages import GmailMessage
from app.gmail.labels import GmailLabels

class GmailReader:
    def __init__(self, client: GmailClient, gmail_query: str):
        self.client = client
        self.gmail_query = gmail_query
        
    def get_unprocessed_bookings(self) -> Iterator[GmailMessage]:
        messages = self.client.search_messages(self.gmail_query)
        
        # Process oldest messages first so CREATE happens before UPDATE/CANCEL
        for msg in reversed(messages):
            if GmailLabels.BOOKING_PROCESSED not in msg.labels and GmailLabels.BOOKING_IGNORED not in msg.labels:
                yield msg

    def mark_as_processed(self, message_id: str) -> bool:
        label_id = self.client.get_label_id(GmailLabels.BOOKING_PROCESSED)
        if not label_id:
            return False
        return self.client.add_label(message_id, label_id)

    def mark_as_ignored(self, message_id: str) -> bool:
        label_id = self.client.get_label_id(GmailLabels.BOOKING_IGNORED)
        if not label_id:
            return False
        return self.client.add_label(message_id, label_id)
