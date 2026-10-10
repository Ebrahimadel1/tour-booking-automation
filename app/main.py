import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

from app.gmail.reader import GmailReader
from app.gmail.messages import GmailMessage
from app.parsers.getyourguide import GetYourGuideParser
from app.validators.booking import BookingValidator
from app.models.operations import OperationType
from app.repositories.booking_repository import BookingRepository
from app.logic.create import CreateLogic
from app.logic.update import UpdateLogic
from app.logic.cancel import CancelLogic
from app.logic.results import CreateResult

logger = logging.getLogger(__name__)

class ProcessingStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

@dataclass
class ProcessingResult:
    message_id: str
    status: ProcessingStatus
    booking_number: Optional[str] = None
    operation: Optional[OperationType] = None
    error: Optional[str] = None

class Orchestrator:
    def __init__(self, gmail_reader: GmailReader, repository: BookingRepository, dry_run: bool = False):
        self.gmail_reader = gmail_reader
        self.repository = repository
        self.dry_run = dry_run
        
        self.create_logic = CreateLogic(repository)
        self.update_logic = UpdateLogic(repository)
        self.cancel_logic = CancelLogic(repository)
        
    def process_all(self) -> List[ProcessingResult]:
        results = []
        for msg in self.gmail_reader.get_unprocessed_bookings():
            result = self._process_single_message(msg)
            results.append(result)
        return results
        
    def _process_single_message(self, msg: GmailMessage) -> ProcessingResult:
        booking_nr = None
        operation = None
        
        try:
            # 0. Detect Booking & Provider
            is_booking = False
            provider = None
            
            subject_lower = msg.subject.lower()
            sender_lower = msg.sender.lower()
            
            if "getyourguide" in sender_lower or "getyourguide" in subject_lower or "gyg" in subject_lower:
                # We want to process ANY email that is related to a booking (has booking/canceled/change/messaged in subject)
                if "booking" in subject_lower or "canceled" in subject_lower or "detail change" in subject_lower or "messaged you" in subject_lower:
                    is_booking = True
                    provider = "GetYourGuide"
            
            if not is_booking:
                logger.info(f"Message {msg.message_id} is NOT a booking. Marking as ignored and skipping.")
                self.gmail_reader.mark_as_ignored(msg.message_id)
                return ProcessingResult(msg.message_id, ProcessingStatus.SKIPPED, error="Not a booking")
                
            logger.info(f"Message {msg.message_id} detected as {provider} booking.")
            
            # 1. Parse
            try:
                if provider == "GetYourGuide":
                    booking = GetYourGuideParser.parse(msg.plain_text)
                else:
                    raise ValueError(f"No parser for provider: {provider}")
                    
                booking_nr = booking.booking_number
                operation = booking.operation
            except Exception as e:
                logger.error(f"Message {msg.message_id} Parser failure: {str(e)}")
                return ProcessingResult(msg.message_id, ProcessingStatus.FAILED, error=f"Parser Error: {str(e)}")
                
            # 2. Validate
            validation_result = BookingValidator.validate(booking)
            if not validation_result.is_valid:
                error_msg = "; ".join(validation_result.errors)
                logger.error(f"Message {msg.message_id} Validator failure: {error_msg}")
                return ProcessingResult(msg.message_id, ProcessingStatus.FAILED, booking_nr, operation, error=f"Validation Error: {error_msg}")
                
            # 3. Business Logic Execution
            if self.dry_run:
                logger.info(f"[DRY RUN] Would execute {operation.value} for {booking_nr}")
                return ProcessingResult(msg.message_id, ProcessingStatus.SUCCESS, booking_nr, operation)

            success = False
            
            if operation == OperationType.CREATE:
                result = self.create_logic.execute(booking)
                if result in (CreateResult.CREATED, CreateResult.ALREADY_EXISTS):
                    success = True
                else:
                    success = False
                    
            elif operation == OperationType.UPDATE:
                success = self.update_logic.execute(booking)
                
            elif operation == OperationType.CANCEL:
                success = self.cancel_logic.execute(booking)
                
            else:
                success = False

            if not success:
                logger.error(f"Message {msg.message_id} Business logic failure for {booking_nr} ({operation.value})")
                return ProcessingResult(msg.message_id, ProcessingStatus.FAILED, booking_nr, operation, error="Business logic or repository failure")
                
            # 4. Apply Label
            label_success = self.gmail_reader.mark_as_processed(msg.message_id)
            if not label_success:
                logger.warning(f"Message {msg.message_id} Business logic succeeded but label application failed.")
                return ProcessingResult(msg.message_id, ProcessingStatus.FAILED, booking_nr, operation, error="Label application failed")
                
            logger.info(f"Message {msg.message_id} processed successfully.")
            return ProcessingResult(msg.message_id, ProcessingStatus.SUCCESS, booking_nr, operation)
            
        except Exception as e:
            logger.exception(f"Message {msg.message_id} unexpected error: {str(e)}")
            return ProcessingResult(msg.message_id, ProcessingStatus.FAILED, booking_nr, operation, error=f"Unexpected Error: {str(e)}")
