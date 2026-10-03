import pytest
from datetime import datetime
from app.main import Orchestrator, ProcessingStatus
from tests.mocks.mock_gmail_client import MockGmailClient
from app.gmail.reader import GmailReader
from tests.mocks.mock_booking_repository import MockBookingRepository
from app.gmail.messages import GmailMessage
from app.gmail.labels import GmailLabels
from pathlib import Path
from app.models.booking import AirtableBookingRecord

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_fixture(type_dir: str, filename: str) -> str:
    path = FIXTURES_DIR / type_dir / filename
    return path.read_text(encoding="utf-8")

@pytest.fixture
def repo():
    return MockBookingRepository()

@pytest.fixture
def gmail_client():
    return MockGmailClient()

@pytest.fixture
def gmail_reader(gmail_client):
    return GmailReader(gmail_client, "provider@example.com")

def create_mock_message(client, msg_id, content) -> GmailMessage:
    msg = GmailMessage(
        thread_id=msg_id, message_id=msg_id, subject="Booking",
        sender="getyourguide@example.com", received_at=datetime.now(),
        plain_text=content, html="html", labels=[]
    )
    client.messages[msg_id] = msg
    return msg

def test_e2e_create(repo, gmail_client, gmail_reader):
    text = load_fixture("create", "create_normal.txt")
    create_mock_message(gmail_client, "m1", text)
    
    orchestrator = Orchestrator(gmail_reader, repo)
    results = orchestrator.process_all()
    
    assert len(results) == 1
    assert results[0].status == ProcessingStatus.SUCCESS
    
    saved = repo.find_by_booking_number("GYGN6BWBM54M")
    assert saved is not None
    assert saved.booking_status == "Active"
    assert GmailLabels.BOOKING_PROCESSED in gmail_client.messages["m1"].labels

def test_e2e_duplicate_create(repo, gmail_client, gmail_reader):
    text = load_fixture("create", "create_normal.txt")
    create_mock_message(gmail_client, "m1", text)
    
    orchestrator = Orchestrator(gmail_reader, repo)
    orchestrator.process_all() 
    
    # Manual reprocessing
    gmail_client.messages["m1"].labels.clear()
    
    results2 = orchestrator.process_all()
    assert len(results2) == 1
    assert results2[0].status == ProcessingStatus.SUCCESS 
    assert GmailLabels.BOOKING_PROCESSED in gmail_client.messages["m1"].labels

def test_e2e_update(repo, gmail_client, gmail_reader):
    # Setup initial db
    repo.records["GYGUPDATE1"] = AirtableBookingRecord(
        agency="GetYourGuide", booking_nr="GYGUPDATE1", booking_status="Active", date_trip="2026-10-23T16:00:00"
    )
    
    text_update = load_fixture("update", "update_time_only.txt")
    create_mock_message(gmail_client, "m2", text_update)
    
    results = Orchestrator(gmail_reader, repo).process_all()
    assert len(results) == 1
    assert results[0].status == ProcessingStatus.SUCCESS
    
    updated = repo.find_by_booking_number("GYGUPDATE1")
    assert updated.date_trip == "2026-10-23T18:00:00"
    assert GmailLabels.BOOKING_PROCESSED in gmail_client.messages["m2"].labels

def test_e2e_cancel(repo, gmail_client, gmail_reader):
    repo.records["GYGCANCEL1"] = AirtableBookingRecord(
        agency="GetYourGuide", booking_nr="GYGCANCEL1", booking_status="Active"
    )
    
    text_cancel = load_fixture("cancel", "cancel_normal.txt")
    create_mock_message(gmail_client, "m3", text_cancel)
    
    results = Orchestrator(gmail_reader, repo).process_all()
    assert len(results) == 1
    assert results[0].status == ProcessingStatus.SUCCESS
    
    canceled = repo.find_by_booking_number("GYGCANCEL1")
    assert canceled.booking_status == "Canceled"
    assert GmailLabels.BOOKING_PROCESSED in gmail_client.messages["m3"].labels

def test_e2e_missing_booking_no_label(repo, gmail_client, gmail_reader):
    # Cancel for non-existent booking
    text_cancel = load_fixture("cancel", "cancel_normal.txt") # GYGCANCEL1
    create_mock_message(gmail_client, "m4", text_cancel)
    
    results = Orchestrator(gmail_reader, repo).process_all()
    assert len(results) == 1
    assert results[0].status == ProcessingStatus.FAILED
    
    # Label MUST NOT be added
    assert GmailLabels.BOOKING_PROCESSED not in gmail_client.messages["m4"].labels

def test_e2e_parser_failure_no_label(repo, gmail_client, gmail_reader):
    create_mock_message(gmail_client, "m5", "This is complete garbage and not an email")
    
    results = Orchestrator(gmail_reader, repo).process_all()
    assert len(results) == 1
    assert results[0].status == ProcessingStatus.FAILED
    assert GmailLabels.BOOKING_PROCESSED not in gmail_client.messages["m5"].labels

def test_e2e_dry_run(repo, gmail_client, gmail_reader):
    text = load_fixture("create", "create_normal.txt")
    create_mock_message(gmail_client, "m6", text)
    
    orchestrator = Orchestrator(gmail_reader, repo, dry_run=True)
    results = orchestrator.process_all()
    
    assert len(results) == 1
    assert results[0].status == ProcessingStatus.SUCCESS
    
    # DB must be empty
    assert repo.find_by_booking_number("GYGN6BWBM54M") is None
    # Label must NOT be added
    assert GmailLabels.BOOKING_PROCESSED not in gmail_client.messages["m6"].labels

def test_e2e_exception_isolation(repo, gmail_client, gmail_reader):
    # Message 1: garbage
    create_mock_message(gmail_client, "m_bad", "garbage")
    # Message 2: valid
    create_mock_message(gmail_client, "m_good", load_fixture("create", "create_normal.txt"))
    
    orchestrator = Orchestrator(gmail_reader, repo)
    results = orchestrator.process_all()
    
    assert len(results) == 2
    assert results[0].status == ProcessingStatus.FAILED
    assert results[1].status == ProcessingStatus.SUCCESS
    
    # Ensure second message processed properly despite first failing
    assert repo.find_by_booking_number("GYGN6BWBM54M") is not None
    assert GmailLabels.BOOKING_PROCESSED in gmail_client.messages["m_good"].labels
    assert GmailLabels.BOOKING_PROCESSED not in gmail_client.messages["m_bad"].labels

def test_e2e_repo_failure_no_label(repo, gmail_client, gmail_reader, mocker):
    text = load_fixture("create", "create_normal.txt")
    create_mock_message(gmail_client, "m1", text)
    
    mocker.patch.object(repo, "create", return_value=False)
    
    orchestrator = Orchestrator(gmail_reader, repo)
    results = orchestrator.process_all()
    
    assert len(results) == 1
    assert results[0].status == ProcessingStatus.FAILED
    assert GmailLabels.BOOKING_PROCESSED not in gmail_client.messages["m1"].labels

def test_e2e_non_booking_skip(repo, gmail_client, gmail_reader):
    msg = GmailMessage(
        thread_id="m_spam", message_id="m_spam", subject="50% Off Sale",
        sender="marketing@spam.com", received_at=datetime.now(),
        plain_text="Buy now!", html="html", labels=[]
    )
    gmail_client.messages["m_spam"] = msg
    
    orchestrator = Orchestrator(gmail_reader, repo)
    results = orchestrator.process_all()
    
    assert len(results) == 1
    assert results[0].status == ProcessingStatus.SKIPPED
    assert GmailLabels.BOOKING_PROCESSED not in gmail_client.messages["m_spam"].labels
    assert GmailLabels.BOOKING_IGNORED in gmail_client.messages["m_spam"].labels

def test_e2e_already_processed_skip(repo, gmail_client, gmail_reader):
    msg = create_mock_message(gmail_client, "m_proc", "content")
    msg.labels.append(GmailLabels.BOOKING_PROCESSED)
    
    orchestrator = Orchestrator(gmail_reader, repo)
    results = orchestrator.process_all()
    
    assert len(results) == 0

def test_e2e_already_ignored_skip(repo, gmail_client, gmail_reader):
    msg = create_mock_message(gmail_client, "m_ign", "content")
    msg.labels.append(GmailLabels.BOOKING_IGNORED)
    
    orchestrator = Orchestrator(gmail_reader, repo)
    results = orchestrator.process_all()
    
    assert len(results) == 0
