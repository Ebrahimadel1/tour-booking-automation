import os
import logging
from dotenv import load_dotenv

from app.gmail.google_client import GoogleGmailClient
from app.gmail.reader import GmailReader
from app.repositories.airtable_repository import AirtableRepository
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
        
        # Read generic query from environment or default to unlabelled inbox messages
        gmail_query = os.getenv("GMAIL_QUERY", "in:inbox -label:BOOKING_PROCESSED -label:BOOKING_IGNORED")
        logger.info(f"Using GMAIL_QUERY: {gmail_query}")
        gmail_reader = GmailReader(client=gmail_client, gmail_query=gmail_query)
        
        logger.info("Initializing Airtable Repository...")
        airtable_repo = AirtableRepository()
        
        dry_run_env = os.getenv("DRY_RUN", "true").lower() == "true"
        logger.info(f"Initializing Orchestrator (DRY RUN = {dry_run_env})...")
        orchestrator = Orchestrator(
            gmail_reader=gmail_reader,
            repository=airtable_repo,
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
