from abc import ABC, abstractmethod
from typing import List
from app.gmail.messages import GmailMessage

class GmailClient(ABC):
    @abstractmethod
    def search_messages(self, query: str) -> List[GmailMessage]:
        pass
        
    @abstractmethod
    def add_label(self, message_id: str, label_id: str) -> bool:
        pass
        
    @abstractmethod
    def remove_label(self, message_id: str, label_id: str) -> bool:
        pass
        
    @abstractmethod
    def get_label_id(self, label_name: str) -> str:
        pass
