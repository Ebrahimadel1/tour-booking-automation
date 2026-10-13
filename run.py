import os
import logging
from dotenv import load_dotenv

from app.gmail.google_client import GoogleGmailClient
from app.gmail.reader import GmailReader
from app.repositories.airtable_repository import AirtableRepository
from app.repositories.baserow_repository import BaserowRepository
from app.repositories.dual_repository import DualBookingRepository
from app.main import Orchestrator

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting Tour Booking Automation...")
    logger.info("Loading environment...")
    
    # Load environment variables from .env
    load_dotenv()
    
    try:
        logger.info("Connecting to Gmail...")
        gmail_client = GoogleGmailClient()
        logger.info("Gmail connected successfully.")
        
        # Read generic query from environment or default to GYG Booking label within last 24 hours
        gmail_query = os.getenv("GMAIL_QUERY") or "label:GYG-Booking newer_than:1d -label:BOOKING_PROCESSED -label:BOOKING_IGNORED"
        logger.info(f"Using GMAIL_QUERY: {gmail_query}")
        gmail_reader = GmailReader(client=gmail_client, gmail_query=gmail_query)
        
        enable_airtable = os.getenv("ENABLE_AIRTABLE", "true").lower() == "true"
        enable_baserow = os.getenv("ENABLE_BASEROW", "true").lower() == "true"
        logger.info(f"Repository Configuration -> Airtable: {enable_airtable}, Baserow: {enable_baserow}")
        
        airtable_repo = AirtableRepository() if enable_airtable else None
        baserow_repo = BaserowRepository() if enable_baserow else None
        
        dual_repo = DualBookingRepository(
            airtable_repo=airtable_repo,
            baserow_repo=baserow_repo,
            enable_airtable=enable_airtable,
            enable_baserow=enable_baserow
        )
        
        dry_run_env = os.getenv("DRY_RUN", "true").lower() == "true"
        logger.info(f"Initializing Orchestrator (DRY RUN = {dry_run_env})...")
        orchestrator = Orchestrator(
            gmail_reader=gmail_reader,
            repository=dual_repo,
            dry_run=dry_run_env  
        )
        
        logger.info("Searching for unprocessed booking emails...")
        results = orchestrator.process_all()
        
        logger.info(f"Processing finished. Processed {len(results)} messages.")
        for res in results:
            logger.info(
                f"Result -> Message ID: {res.message_id} | "
                f"Booking Nr: {res.booking_number} | "
                f"Operation: {res.operation.name if res.operation else None} | "
                f"Status: {res.status.name} | "
                f"Error: {res.error}"
            )
            
    except Exception as e:
        logger.error(f"Application Initialization Failed: {str(e)}")

if __name__ == "__main__":
    main()
