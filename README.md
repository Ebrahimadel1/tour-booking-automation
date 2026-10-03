# Python Tourism Booking Automation

Production-oriented automation for processing tourism booking emails from Gmail and synchronizing them safely with Airtable.

> **Primary specification:** `PROJECT_SPECIFICATION.md`
>
> **Important:** `PROJECT_SPECIFICATION.md` is the authoritative source for business rules and safety requirements. Read it before implementing or changing the system.

---

## 1. What this project does

The system receives booking-related emails through Gmail and processes them automatically.

Current provider:

- GetYourGuide

Current operations:

- CREATE
- UPDATE
- CANCEL

Main flow:

```text
Gmail
  ↓
Python Automation
  ↓
Provider Detection
  ↓
GetYourGuide Parser
  ↓
Validation
  ↓
CREATE / UPDATE / CANCEL
  ↓
Airtable
  ↓
BOOKING_PROCESSED label
```

The system is designed to run unattended through GitHub Actions, so the user's personal computer does not need to remain switched on.

---

## 2. Read this before coding

Before changing or adding code:

1. Read `PROJECT_SPECIFICATION.md` completely.
2. Understand the business rules.
3. Inspect the existing repository.
4. Do not assume behavior that is not documented.
5. Add tests for critical logic.
6. Never connect destructive production writes before testing/dry-run validation.

The specification contains the rules for:

- Gmail processing
- GetYourGuide parsing
- CREATE
- UPDATE
- CANCEL
- Booking Status
- protected fields
- Date/Time handling
- duplicate protection
- Gmail label behavior
- error handling
- logging
- testing
- deployment
- migration

---

## 3. Core business rules

### CREATE

A valid new booking must:

1. Be parsed.
2. Be validated.
3. Be checked by Booking Number.
4. Avoid duplicate creation.
5. Create the Airtable record.
6. Set:

```text
Booking Status = Active
```

7. Confirm success.
8. Add:

```text
BOOKING_PROCESSED
```

---

### UPDATE

An UPDATE must:

1. Find the existing booking by Booking Number.
2. Read the current record.
3. Normalize values.
4. Compare business values.
5. Build only the fields that changed.
6. PATCH only those fields.
7. Never overwrite unrelated/protected fields.
8. Add `BOOKING_PROCESSED` only after success.

Example:

```text
18:00 → 20:00
```

must be recognized as a real `Date Trip` change even when the calendar date is identical.

---

### CANCEL

Cancellation is a separate business operation.

It must:

1. Find the booking by Booking Number.
2. PATCH only:

```json
{
  "Booking Status": "Canceled"
}
```

3. Never overwrite other booking fields.
4. Add `BOOKING_PROCESSED` only after success.

---

## 4. Gmail processing state

The label:

```text
BOOKING_PROCESSED
```

is the source of truth for whether an email has been processed.

```text
Label exists
    ↓
SKIP

Label absent
    ↓
PROCESS
```

Removing the label manually must make the message eligible for processing again.

A previous Message ID must not permanently block reprocessing.

Message IDs may be stored for logging/audit, but they are not the authoritative processing state.

---

## 5. Previous production bugs

The new system must explicitly prevent these known problems:

### Date artifact

Example:

```text
Date
>>
October 23, 2026
```

The parser must find the real date instead of treating `>>` as the date.

### Price artifact

Example:

```text
Price
[image: coin]
€ 93.75
```

The parser must still extract the price.

### Time-only update

Example:

```text
18:00 → 20:00
```

must update `Date Trip`.

### Protected Date Trip

`Date Trip` must not be treated as permanently immutable. It may change when the actual booking date/time changes.

### Manual Gmail reprocessing

Removing `BOOKING_PROCESSED` must allow processing again.

### Cancellation overwrite

Cancellation must never reuse generic UPDATE behavior.

### Partial/unsafe writes

Only changed fields should be PATCHed.

More details are in `PROJECT_SPECIFICATION.md`.

---

## 6. Project structure

Recommended structure:

```text
tour-booking-automation/
│
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── gmail/
│   │   ├── client.py
│   │   ├── reader.py
│   │   ├── labels.py
│   │   └── messages.py
│   │
│   ├── parsers/
│   │   ├── base.py
│   │   ├── getyourguide.py
│   │   └── date_parser.py
│   │
│   ├── models/
│   │   ├── booking.py
│   │   ├── email.py
│   │   └── operations.py
│   │
│   ├── logic/
│   │   ├── create.py
│   │   ├── update.py
│   │   ├── cancel.py
│   │   └── comparison.py
│   │
│   ├── services/
│   │   ├── booking_service.py
│   │   ├── airtable.py
│   │   └── message_service.py
│   │
│   ├── repositories/
│   │   ├── booking_repository.py
│   │   └── airtable_repository.py
│   │
│   └── validators/
│       ├── booking.py
│       └── fields.py
│
├── tests/
│   ├── fixtures/
│   │   ├── create/
│   │   ├── update/
│   │   └── cancel/
│   │
│   ├── test_create.py
│   ├── test_update.py
│   ├── test_cancel.py
│   ├── test_parser.py
│   ├── test_date.py
│   ├── test_price.py
│   ├── test_labels.py
│   └── test_protection.py
│
├── .github/
│   └── workflows/
│       └── automation.yml
│
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── PROJECT_SPECIFICATION.md
```

The AI developer may adjust the structure if there is a documented technical reason, but separation of concerns must remain.

---

## 7. Local development setup

Recommended Python version:

```text
Python 3.10+
```

Create a virtual environment:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 8. Environment variables

Create a local `.env` file for development.

Example:

```env
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=

AIRTABLE_TOKEN=
AIRTABLE_BASE_ID=
AIRTABLE_TABLE_NAME=

GMAIL_QUERY=
PROCESSED_LABEL=BOOKING_PROCESSED

DRY_RUN=true
LOG_LEVEL=INFO
```

Never commit `.env`.

Add it to `.gitignore`.

---

## 9. Gmail authentication

The system uses the Gmail API with OAuth 2.0.

The production environment must be able to authenticate without user interaction every time.

Use the OAuth refresh token securely.

Never place the refresh token directly in source code.

For local development, credentials come from environment variables.

For GitHub Actions, credentials come from GitHub Secrets.

---

## 10. Airtable configuration

The Airtable integration must use configuration/environment variables.

The Airtable token must never be committed.

The Airtable-specific implementation should remain behind the repository/service layer.

Business logic should not contain raw Airtable API calls throughout the codebase.

---

## 11. Dry-run mode

Before production writes, use:

```env
DRY_RUN=true
```

Dry-run should:

```text
Read Gmail
    ↓
Parse
    ↓
Validate
    ↓
Detect operation
    ↓
Find existing record when needed
    ↓
Calculate intended changes
    ↓
Log intended operation
    ↓
DO NOT WRITE TO AIRTABLE
```

Do not mark a message as successfully processed merely because dry-run completed.

---

## 12. Testing

Run the full test suite with:

```bash
pytest
```

Run with more detailed output:

```bash
pytest -v
```

Important tests include:

```text
CREATE
UPDATE
CANCEL
Duplicate CREATE
Duplicate CANCEL
Time-only Date Trip change
Date change
Protected fields
Booking Status
Date parsing
Price parsing
Customer parsing
Gmail label behavior
Manual reprocessing
Failed processing
```

Every production bug discovered must result in a regression test.

---

## 13. Real email fixtures

Use anonymized email fixtures.

Example:

```text
tests/fixtures/create/create_normal.html
tests/fixtures/create/create_artifact_date.html
tests/fixtures/create/create_artifact_price.html

tests/fixtures/update/update_time_only.html
tests/fixtures/update/update_date_change.html

tests/fixtures/cancel/cancel_normal.html
```

Do not commit real customer personal data.

---

## 14. Production architecture

Production target:

```text
                    GitHub
                      │
                      ▼
               GitHub Actions
                      │
                      ▼
              Python Automation
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
          Gmail              Airtable
```

The user's PC does not need to remain on.

The application must be idempotent because scheduled jobs can be retried or overlap.

---

## 15. GitHub Actions

Production secrets should be configured in GitHub:

```text
GMAIL_CLIENT_ID
GMAIL_CLIENT_SECRET
GMAIL_REFRESH_TOKEN
AIRTABLE_TOKEN
AIRTABLE_BASE_ID
AIRTABLE_TABLE_NAME
```

Do not put secret values in:

- Python files
- YAML files
- README
- logs
- test fixtures
- Git history

---

## 16. Deployment strategy

Do not immediately replace the old Apps Script production system.

Use:

```text
Old Apps Script
      ↓
continues production

Python System
      ↓
development + testing + dry-run
```

Then:

1. Build Python system.
2. Run unit tests.
3. Test real anonymized emails.
4. Compare old and new parser results.
5. Run dry-run.
6. Validate intended Airtable changes.
7. Perform controlled production writes.
8. Monitor.
9. Switch production only after successful validation.

---

## 17. Troubleshooting order

When something goes wrong, do not immediately change code.

Check in this order:

```text
1. Gmail message
2. Message ID
3. Gmail labels
4. Subject
5. Provider detection
6. Parsed operation
7. Parsed Booking Number
8. Parsed Date/Time
9. Parsed fields
10. Validation
11. Existing Airtable record
12. Changed fields
13. Airtable request
14. Airtable response
15. Processed label operation
```

Then identify which layer actually failed.

---

## 18. Safety principles

The project prioritizes:

1. Data safety
2. Correctness
3. Idempotency
4. Traceability
5. Testability
6. Maintainability
7. Performance

Do not sacrifice data safety for implementation speed.

---

## 19. Future extensibility

The system should eventually support:

```text
More booking providers
        ↓
Provider-specific parsers
```

and:

```text
Airtable
PostgreSQL
Supabase
Other database
```

without rewriting the core booking business logic.

---

## 20. Definition of Done

The project is ready for production only when:

- [ ] Gmail API works.
- [ ] OAuth works unattended.
- [ ] GetYourGuide parser works.
- [ ] CREATE works.
- [ ] CREATE sets Active.
- [ ] UPDATE works.
- [ ] Date-only changes work.
- [ ] Time-only changes work.
- [ ] Protected fields remain protected.
- [ ] CANCEL works.
- [ ] CANCEL changes only Booking Status.
- [ ] CANCEL sets Canceled.
- [ ] Duplicate CREATE is prevented.
- [ ] Duplicate CANCEL is safe.
- [ ] Removing `BOOKING_PROCESSED` enables reprocessing.
- [ ] Message-ID history cannot block manual reprocessing.
- [ ] Failed operations do not receive `BOOKING_PROCESSED`.
- [ ] Artifact-tolerant date parsing works.
- [ ] Artifact-tolerant price parsing works.
- [ ] Airtable writes are minimal.
- [ ] Logging works.
- [ ] Secrets are protected.
- [ ] Dry-run works.
- [ ] Tests pass.
- [ ] Real anonymized fixtures pass.
- [ ] GitHub Actions works.
- [ ] PC does not need to remain running.
- [ ] Production migration is safe.
- [ ] Airtable is isolated behind a service/repository layer.

---

## 21. AI Builder instruction

**Read `PROJECT_SPECIFICATION.md` before implementing anything.**

The AI developer must treat the specification as the primary source of truth.

Do not:

- guess business behavior;
- silently change business rules;
- make destructive Airtable updates;
- mark failed emails as processed;
- treat Message-ID history as stronger than Gmail label state;
- permanently block manual reprocessing;
- treat Date Trip as permanently immutable;
- use generic UPDATE logic for cancellation;
- ignore timezone semantics;
- assume email formatting is fixed;
- deploy directly to production without tests.

When a bug is fixed:

```text
Bug
 ↓
Root cause
 ↓
Minimal fix
 ↓
Regression test
 ↓
Relevant test suite
```

Before declaring the project complete, verify the entire `Definition of Done` in `PROJECT_SPECIFICATION.md`.

---

## 22. Project files

The root of the project should contain at least:

```text
PROJECT_SPECIFICATION.md
README.md
requirements.txt
.env.example
.gitignore
```

The three most important files at the beginning are:

```text
PROJECT_SPECIFICATION.md
README.md
requirements.txt
```

`PROJECT_SPECIFICATION.md` defines what the system must do.

`README.md` explains how to work with the project.

`requirements.txt` defines the Python dependencies.
