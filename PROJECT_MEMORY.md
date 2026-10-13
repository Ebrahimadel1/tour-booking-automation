# PROJECT_MEMORY

## Project Overview
Python Tourism Booking Automation that reads GetYourGuide booking emails from Gmail, parses them reliably, detects CREATE/UPDATE/CANCEL operations, and safely synchronizes the data with Airtable.

## Current Architecture
No architecture implemented yet. Currently in the initial planning and setup phase.

## Current Project Structure
```text
/
├── PROJECT_SPECIFICATION.md
├── README.md
├── requirements.txt
└── PROJECT_MEMORY.md
(Along with some sample `.eml` files)
```

## Implemented Features
[COMPLETED]
- Project structure initialized (app/, tests/)
- Virtual environment setup and dependencies installed
- Data Models for Booking and Operations (`NormalizedBooking`, `AirtableBookingRecord`, `OperationType`)
- Realistic Anonymized Email Fixtures (`create`, `update`, `cancel` cases including artifacts)
- GetYourGuide Provider Parser (`app/parsers/getyourguide.py`)
- Robust Date & Price Parsing (`app/parsers/date_parser.py`) that ignores artifacts like `>>` and `[image: coin]`
- Booking Validator Layer (`app/validators/booking.py`, `app/validators/fields.py`) handling CREATE, UPDATE, CANCEL logic strictly and purely without mutation.
- Repository Contract (`app/repositories/booking_repository.py`)
- Mock Repository for Business Logic tests (`tests/mocks/mock_booking_repository.py`)
- Core Business Logic (`app/logic/create.py`, `app/logic/update.py`, `app/logic/cancel.py`, `app/logic/comparison.py`, `app/logic/results.py`)
- Airtable Repository Adapter (`app/repositories/airtable_repository.py`)
- Gmail Integration Layer (`app/gmail/client.py`, `app/gmail/reader.py`, `app/gmail/labels.py`, `app/gmail/messages.py`)
- End-to-End Orchestrator (`app/main.py`) wiring all layers together.

## Current Behavior
- Data models are strictly typed with Pydantic and tested for correct field aliases according to Airtable format.
- **Provider Parser (GetYourGuide)**: Safely extracts fields (Customer Name, Email, Trip Name, Date, Price, etc.) using boundaries based on known labels rather than arbitrary line numbers.
- **Operation Detection**: Differentiates accurately between `CREATE`, `UPDATE` ("detail change"), and `CANCEL` ("has been canceled").
- **Date and Time**: Parses and retains exact local time along with the date (e.g. `2026-10-23 18:00`) handling various formatting artifacts effectively.
- **Validators**: 
  - Ensure that `CREATE` has all required fields (Booking Nr, Date Trip, Trip Name, Customer info, Price).
  - Ensure that `UPDATE` validates explicitly provided fields while allowing missing fields.
  - Ensure that `CANCEL` requires only `Booking Nr` and `Operation`.
  - Validate formats without mutating `NormalizedBooking`.
  - Separate `ValidationResult` explicitly holds errors vs warnings without raising generic exceptions.
- **Business Logic**: 
  - `CREATE`: Idempotent, checks existing records, forces `Booking Status = Active`. Identifies internal state (`CREATED`, `ALREADY_EXISTS`, `FAILED`).
  - `UPDATE`: Compares incoming parsed values with existing records using `ComparisonLogic`, generating a diff of `changed_fields`. Allows updates to optional fields while completely shielding protected ones.
  - `CANCEL`: Fully independent, sets `Booking Status = Canceled` on the matched `Booking Nr.`, keeping all other fields perfectly safe.
- **Airtable Repository**: Encapsulates all Airtable API logic via HTTP `requests`.
- **Gmail Reader**: Queries messages using `GmailClient`, filters out messages with `BOOKING_PROCESSED`.
- **Orchestrator**: Executes a robust pipeline (Parse -> Validate -> Execute Logic). Ensures exceptions in one message do not crash the runner. Prevents applying `BOOKING_PROCESSED` unless the database transaction succeeds. Implements `Dry Run` capability that calculates intended actions without persisting them.

## Important Business Rules
- **CREATE**: Must set `Booking Status = Active`. Requires all core fields present.
- **CANCEL**: Must set `Booking Status = Canceled` and modify ONLY the status. Validation only needs `Booking Nr`.
- **UPDATE**: Modifies only changed fields. Missing fields in incoming emails do not fail validation. Does not overwrite missing data with None/Null.
- **Date Trip**: Must be updated when the actual date or time changes (compare date + time, not just calendar date).
- **Processing State**: `BOOKING_PROCESSED` Gmail label is the sole source of truth for processing state. Message ID history is explicitly NOT used to allow manual reprocessing.
- **Duplicate Protection**: CREATE must check for existing Booking Nr. Operations must be idempotent.
- **Data Safety**: PATCH only fields that have actually changed during UPDATE. No destructive writes.

## Problems Found
```text
Problem: Pydantic configuration warning during test.
Root Cause: Using Pydantic V1 `class Config` style in Pydantic V2.
Fix: Updated `AirtableBookingRecord` to use `model_config = ConfigDict(populate_by_name=True)`.
Regression Test: N/A (Syntax fix)
Status: RESOLVED

Problem: Parser failing to extract specific fields or extracting incorrect data (Phone, Option, Hotel Name).
Root Cause: HTML entities &#43; for plus signs, missing newlines for block tags in html-to-text conversion causing line-merges, and unpredictable label strings like "You've received a last-minute booking:".
Fix: Added HTML entity unescaping, improved _html_to_text to correctly insert newlines for <div>, <tr>, etc. Added new phrases to the label dictionaries and restricted inline fallback matching.
Regression Test: Re-ran parsing script against failing production payloads.
Status: RESOLVED

Problem: Customer name in Airtable contained email, phone, and language; Infant participant count was not populated in Airtable # Inf.
Root Cause: In HTML emails, <br data-v-...> had attributes so regex <br\s*/?> failed to match and turned breaks into spaces, causing name/email/phone to collapse onto one line. Additionally, infant regex and Inf Airtable mapping were missing.
Fix: Updated _html_to_text to handle <br[^>]*> and block tags with attributes, added inline regex boundary splitting for customer_name, and added inf (Infant) parsing and Inf Airtable alias mapping.
Regression Test: Tested with real GYG996RG4VG7 email payload.
Status: RESOLVED

Problem: "Country from Phone" in Airtable was showing error "Something went wrong: Couldn't generate..." because Airtable native AI was failing/over quota and the Python automation was not populating the country.
Root Cause: Automation previously did not resolve country from the customer's phone number or send it to Airtable.
Fix: Integrated `phonenumbers` geocoder in `app/parsers/phone_parser.py`, added `country` to `NormalizedBooking`, and mapped to Airtable fields `Country from Phone` and `Customer Country`.
Regression Test: Tested with multiple international phone numbers and live GYG996RG4VG7 payload.
Status: RESOLVED
```

## Decisions Made
- Use a normalized internal model for bookings, decoupling provider-specific parsing from generic Gmail layer.
- Airtable interaction must be behind a repository/service abstraction to allow future migration (e.g., PostgreSQL/Supabase).
- Used Pydantic for models to guarantee strict type enforcement and straightforward field aliasing.
- The Parser extracts fields using regular expressions to safely find the boundaries between explicit field labels instead of relying on a hardcoded layout or `take next N lines` logic.
- Validator purely returns a `ValidationResult` (is_valid, errors, warnings) without mutating `NormalizedBooking` or interacting with external services.
- **Protected Fields**: `Trip Name`, `Booking Nr.`, `Customer Name`, `Option` are completely shielded from automatic UPDATE logic to prevent unintended destructive overwrites.
- **Gmail State Machine**: Process -> if success -> Add label. If failure -> Leave unlabeled to retry.
- **Orchestration**: Dependency Injection is used to pass Repositories and Gmail clients into the Orchestrator, making testing 100% mocked and fast.

## Tests
```text
Models tests (`test_models.py`)  → PASS (3 passed)
Parser tests (`test_parser.py`)  → PASS (14 passed)
Validator tests (`test_validators.py`) → PASS (22 passed)
Logic tests (`test_logic.py`) → PASS (13 passed)
Airtable tests (`test_airtable.py`) → PASS (4 passed)
Gmail tests (`test_gmail.py`) → PASS (5 passed)
Main Orchestrator tests (`test_main.py`) → PASS (9 passed)
TOTAL: 73 tests passing.
```

## Deployment Status
LOCAL (Development phase)

## Current Work
```text
CURRENT TASK: Implement Real Gmail Client / End-to-End Real credentials testing.
CURRENT STATUS: IMPLEMENTED (Main Orchestrator), PLANNED (Real Integration Testing)
WHAT HAS BEEN DONE: 
- Project structure created successfully.
- Virtual environment created and requirements installed.
- Core Data Models created.
- Email Fixtures created.
- GetYourGuide Parser and Validator implemented.
- Repository Contract and Mock Repository built.
- Core Business Logic (CREATE, UPDATE, CANCEL) built and tested with Mock Repository.
- Airtable Repository Adapter built and tested.
- Gmail Integration Layer built and tested with Mock Client. Manual reprocessing regression implemented.
- End-to-End Orchestrator (main.py) implemented with Dependency Injection.
- Full pytest suite (61 tests) passes flawlessly covering all edge cases.
WHAT REMAINS: 
- Real credentials testing for Gmail and Airtable.
NEXT STEP: 
- Start using real credentials and implementing the actual Gmail API Client.
BLOCKERS: 
- None.
```

## Next Steps
1. Test with Real Gmail and Airtable credentials.
