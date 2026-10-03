from typing import List, Dict
from app.gmail.client import GmailClient
from app.gmail.messages import GmailMessage

class MockGmailClient(GmailClient):
    def __init__(self):
        self.messages: Dict[str, GmailMessage] = {}
        self.labels: Dict[str, str] = {
            "BOOKING_PROCESSED": "label_123",
            "BOOKING_IGNORED": "label_ignore_123"
        }
        
    def search_messages(self, query: str) -> List[GmailMessage]:
        return list(self.messages.values())
        
    def add_label(self, message_id: str, label_id: str) -> bool:
        if message_id not in self.messages:
            return False
        
        label_name = next((name for name, i in self.labels.items() if i == label_id), None)
        if label_name and label_name not in self.messages[message_id].labels:
            self.messages[message_id].labels.append(label_name)
        return True
        
    def remove_label(self, message_id: str, label_id: str) -> bool:
        if message_id not in self.messages:
            return False
            
        label_name = next((name for name, i in self.labels.items() if i == label_id), None)
        if label_name and label_name in self.messages[message_id].labels:
            self.messages[message_id].labels.remove(label_name)
        return True
        
    def get_label_id(self, label_name: str) -> str:
        return self.labels.get(label_name, "")
