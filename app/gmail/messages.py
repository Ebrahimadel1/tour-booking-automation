from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime

class GmailMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    thread_id: str
    message_id: str
    subject: str
    sender: str
    received_at: datetime
    plain_text: str
    html: str
    labels: List[str]
