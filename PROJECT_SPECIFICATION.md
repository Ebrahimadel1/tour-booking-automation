# PROJECT_SPECIFICATION.md

# Python Tourism Booking Automation
## Master Build Specification & Non-Negotiable Rules

**Document role:** This is the authoritative specification for the AI developer/agent building this project. Read it completely before writing or changing code.

## 1. Objective

Build a production-grade Python automation that reads booking emails from Gmail, detects the provider (currently GetYourGuide), parses booking data reliably, detects CREATE/UPDATE/CANCEL, safely writes to Airtable, prevents duplicates, supports manual reprocessing through the Gmail `BOOKING_PROCESSED` label, logs every important action, is fully tested, and runs unattended through GitHub Actions.

The architecture must keep business logic independent from Airtable so Airtable can later be replaced by PostgreSQL/Supabase.

## 2. Non-negotiable rules

1. Do not rewrite working business behavior without a documented reason and tests.
2. Never perform destructive Airtable updates. PATCH only fields that actually changed.
3. Cancellation has a dedicated path and may change **only** `Booking Status = Canceled`.
4. Every successful CREATE must set `Booking Status = Active`.
5. `Date Trip` is protected from accidental overwrite but MUST be updated when its actual date or time changes.
6. Date/time comparison must represent the booking's business/local time and must not be fooled by UTC/server timezone conversion.
7. Gmail label `BOOKING_PROCESSED` is the source of truth for processing state.
8. Message-ID history may be used for audit/logging but must NEVER permanently block reprocessing when the Gmail label has been removed.
9. Add `BOOKING_PROCESSED` only after the complete business operation succeeds.
10. If processing fails, do not mark the email processed.
11. Make localized changes; do not modify unrelated modules without necessity.
12. Unknown or malformed emails must never silently modify Airtable.
13. Never commit credentials, refresh tokens, Airtable tokens, or API keys.
14. Production must not be replaced in one step. Build and test Python in parallel, then cut over safely.

## 3. Previous production problems that MUST NOT return

### A. Date artifact bug

GetYourGuide emails could contain:

```text
Date
>>
October 23, 2026
```

The old parser read `>>` as the date.

**Required prevention:** after the Date label, search a bounded region for a valid month/day/year pattern and ignore artifacts such as `>>`, icons, images, and unexpected whitespace.

Support examples such as:

- `October 23, 2026`
- `October 23, 2026, 4:00 PM`
- `October 23, 2026 at 4:00 PM`

### B. Price artifact bug

Emails could contain:

```text
Price
[image: coin]
€ 93.75
```

**Required prevention:** search a bounded region after `Price` / `Total price` for currency + amount. Do not depend on immediate adjacency.

### C. Time-only update bug

A real booking changed:

```text
2026-10-15 18:00
```

to:

```text
2026-10-15 20:00
```

The old system treated it as unchanged.

**Required prevention:** compare date + time, not calendar date only.

### D. Protected Date Trip bug

`Date Trip` was treated as completely immutable.

**Required prevention:** use explicit field policies. Customer fields can remain protected while `Date Trip` is allowed to change when the booking's date/time actually changes.

### E. Gmail reprocessing bug

Removing `BOOKING_PROCESSED` still produced `MESSAGE_ALREADY_PROCESSED` because Message-ID history was treated as authoritative.

**Required prevention:**

```text
Label exists -> skip
Label absent -> eligible for processing
```

If the ID was seen before but the label is now absent, process it again and log a manual reprocessing event if useful.

### F. Cancellation overwrite risk

Cancellation must never use generic UPDATE logic.

**Required prevention:** dedicated cancellation service/path that finds the booking by Booking Nr. and PATCHes only:

```json
{
  "fields": {
    "Booking Status": "Canceled"
  }
}
```

### G. Happy-path-only testing

Clean test strings are insufficient.

**Required prevention:** real/anonymized email fixtures containing artifacts, whitespace differences, date formats, price formats, updates, cancellations, duplicates, missing records, and manual reprocessing.

## 4. Target architecture

```text
Gmail
  ↓
Gmail Integration
  ↓
Email Reader
  ↓
Provider Detection
  ↓
Provider Parser
  ↓
Validator
  ↓
Operation Detection
  ├── CREATE
  ├── UPDATE
  └── CANCEL
  ↓
Booking Service
  ↓
Repository/Data Service
  ↓
Airtable Repository
  ↓
Airtable
```

Business logic MUST NOT be tightly coupled to Airtable API calls.

## 5. Recommended project structure

```text
tour-booking-automation/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── gmail/
│   │   ├── client.py
│   │   ├── reader.py
│   │   ├── labels.py
│   │   └── messages.py
│   ├── parsers/
│   │   ├── base.py
│   │   ├── getyourguide.py
│   │   └── date_parser.py
│   ├── models/
│   │   ├── booking.py
│   │   ├── email.py
│   │   └── operations.py
│   ├── logic/
│   │   ├── create.py
│   │   ├── update.py
│   │   ├── cancel.py
│   │   └── comparison.py
│   ├── services/
│   │   ├── booking_service.py
│   │   ├── airtable.py
│   │   └── message_service.py
│   ├── repositories/
│   │   ├── booking_repository.py
│   │   └── airtable_repository.py
│   └── validators/
│       ├── booking.py
│       └── fields.py
├── tests/
│   ├── fixtures/
│   │   ├── create/
│   │   ├── update/
│   │   └── cancel/
│   ├── test_create.py
│   ├── test_update.py
│   ├── test_cancel.py
│   ├── test_parser.py
│   ├── test_date.py
│   ├── test_price.py
│   ├── test_labels.py
│   └── test_protection.py
├── .github/
│   └── workflows/
│       └── automation.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── PROJECT_SPECIFICATION.md
```

## 6. Normalized booking model

The parser should convert provider-specific emails into a normalized internal model such as:

```json
{
  "provider": "GetYourGuide",
  "booking_number": "GYGN6BWBM54M",
  "operation": "CREATE",
  "date_trip": "2026-10-23T16:00:00",
  "trip_name": "Hurghada: City Tour & Bazaar with Optional Sand Museum Visit",
  "option": "Hurghada: City Tour & Bazaar with Sand Museum Visit",
  "customer_name": "Ivon Schmied",
  "customer_email": "customer-642njiva65b7cpv6@reply.getyourguide.com",
  "customer_phone": "+491624326774",
  "guide": "German",
  "total_price_eur": 93.75,
  "adt": 2,
  "chd": 1
}
```

Provider-specific parsing belongs in the provider parser, not in the generic Gmail layer.

## 7. Gmail processing state

Use:

```text
BOOKING_PROCESSED
```

as the processing marker.

Required state machine:

```text
Email
  ↓
Has BOOKING_PROCESSED?
  ├─ YES → SKIP
  └─ NO → PROCESS
             ├─ SUCCESS → Add label
             └─ FAILURE → Keep unlabeled
```

Removing the label must make the email eligible again.

A previously seen Message ID must not override this.

The search may use `-label:BOOKING_PROCESSED`, but the application must also verify actual labels before processing.

## 8. CREATE rules

Flow:

```text
Email → Parse → Validate → Find Booking Nr.
→ Existing? protect against duplicate
→ Not existing? Create
→ Set Booking Status = Active
→ Verify success
→ Add BOOKING_PROCESSED
```

Example fields:

```json
{
  "Agency": "GetYourGuide",
  "Booking Nr.": "GYGN6BWBM54M",
  "Date Trip": "2026-10-23T16:00:00",
  "trip Name": "Hurghada: City Tour & Bazaar with Optional Sand Museum Visit",
  "Option": "Hurghada: City Tour & Bazaar with Sand Museum Visit",
  "Customer Name": "Ivon Schmied",
  "Customer Email": "customer-642njiva65b7cpv6@reply.getyourguide.com",
  "Customer Phone": "+491624326774",
  "Guide": "German",
  "Total price EUR": 93.75,
  "ADT": 2,
  "CHD": 1,
  "Booking Status": "Active"
}
```

Do not create another record if the same Booking Nr. already exists.

## 9. UPDATE rules

Flow:

```text
Email → Parse → Validate → Find by Booking Nr.
→ Read existing record
→ Normalize values
→ Compare business values
→ Build changed_fields only
→ No changes? no PATCH
→ Changes? PATCH only changed fields
→ Verify success
→ Add BOOKING_PROCESSED
```

Example:

```text
OLD Date Trip = 2026-10-15 18:00
NEW Date Trip = 2026-10-15 20:00
```

must produce:

```json
{
  "fields": {
    "Date Trip": "2026-10-15T20:00:00"
  }
}
```

No unrelated fields.

## 10. Field protection policy

Initial policy:

| Field | CREATE | UPDATE | CANCEL |
|---|---|---|---|
| Agency | Yes | Protected | No |
| Booking Nr. | Yes | Protected | Lookup only |
| Date Trip | Yes | Yes when changed | No |
| Trip Name | Yes | Protected | No |
| Option | Yes | Only if explicitly allowed | No |
| Customer Name | Yes | Protected | No |
| Customer Email | Yes | Protected | No |
| Customer Phone | Yes | Protected | No |
| Guide | Yes | Only if explicitly allowed | No |
| Total price EUR | Yes | Only if explicitly allowed | No |
| ADT | Yes | Only if explicitly allowed | No |
| CHD | Yes | Only if explicitly allowed | No |
| Hotel Name | Yes | Only if explicitly allowed | No |
| Booking Status | Active | Preserve unless explicit rule | Canceled |

Do not implement protection as one generic "never update" list. Field policy must be explicit.

## 11. Date/time rules

Date handling is critical.

The system must:

- parse date and time independently from email formatting;
- preserve intended booking/local time;
- compare date + time;
- avoid server timezone assumptions;
- avoid accidental UTC conversion changing business meaning;
- recognize time-only changes as changes.

Do not compare raw Python `datetime` objects if their timezone semantics have not been normalized deliberately.

## 12. Price rules

Support:

```text
€ 93.75
EUR 93.75
USD 120.00
```

and artifact variants such as:

```text
Price
[image: coin]
€ 93.75
```

The parser must return a numeric amount plus currency where available.

## 13. Parsing boundaries

Customer Name, Email, Phone, Guide, Hotel, Option, Price, and passenger counts must use clear field boundaries.

Never take an arbitrary number of lines after a label.

A field must stop when the next known field starts.

## 14. Cancellation rules

Cancellation has its own path.

Flow:

```text
Cancellation
  ↓
Parse Booking Nr.
  ↓
Find existing record
  ↓
PATCH only Booking Status
  ↓
Verify success
  ↓
Add BOOKING_PROCESSED
```

Required payload:

```json
{
  "records": [
    {
      "id": "recXXXXXXXXXXXXXX",
      "fields": {
        "Booking Status": "Canceled"
      }
    }
  ],
  "typecast": true
}
```

Never modify customer data, date, trip, price, passenger counts, hotel, or other fields.

If the booking does not exist, do not create a fake cancellation record. Log the missing booking and follow the configured retry/error policy.

## 15. Status rules

```text
CREATE → Active
CANCEL → Canceled
UPDATE → Preserve existing status unless an explicit business rule says otherwise
```

## 16. Duplicate protection / idempotency

The system must be safe if the same execution happens more than once.

Cases:

1. Same email runs twice.
2. Same Booking Nr. already exists.
3. Same cancellation arrives twice.
4. User removes `BOOKING_PROCESSED` and intentionally reprocesses.
5. GitHub Actions retries or overlaps.
6. Airtable succeeds but Gmail label operation fails.

CREATE must be protected by Booking Nr. lookup.

Business operations must remain idempotent even if the label is not yet present.

## 17. Error handling

### Parsing error
- Do not write partial data.
- Log `PARSING_ERROR`.
- Do not add processed label.

### Validation error
- Do not call Airtable.
- Log `VALIDATION_ERROR`.
- Do not add processed label.

### Airtable error
- Do not add processed label.
- Log `AIRTABLE_ERROR`.
- Allow safe retry.

### Gmail label failure after successful business operation
The business operation may already have succeeded. Log this separately and rely on idempotency to prevent duplication on the next run.

## 18. Logging

Log enough to reproduce a problem:

```text
timestamp
message_id
thread_id
provider
booking_number
operation
parser_result
validation_result
airtable_record_id
changed_fields
status
error_type
error_message
processing_duration
```

Recommended events:

```text
CREATE_SUCCESS
UPDATE_SUCCESS
CANCEL_SUCCESS
NO_CHANGES
DUPLICATE_PROTECTED
PARSING_ERROR
VALIDATION_ERROR
AIRTABLE_ERROR
MANUAL_REPROCESSING_DETECTED
```

Never log secrets.

## 19. Security

Never commit:

```text
GMAIL_CLIENT_SECRET
GMAIL_REFRESH_TOKEN
AIRTABLE_TOKEN
API keys
```

Use `.env` locally and GitHub Secrets in production.

Recommended secrets:

```text
GMAIL_CLIENT_ID
GMAIL_CLIENT_SECRET
GMAIL_REFRESH_TOKEN
AIRTABLE_TOKEN
AIRTABLE_BASE_ID
AIRTABLE_TABLE_NAME
```

`.env` must be ignored by Git.

## 20. GitHub Actions

Production target:

```text
GitHub Repository
       ↓
GitHub Actions
       ↓
Python Automation
       ↓
Gmail
       ↓
Airtable
```

The user's personal computer must NOT need to stay on.

The automation must be safe when:
- a run overlaps,
- a run is retried,
- a run fails,
- a scheduled run starts after an earlier run.

Do not rely only on scheduler behavior for duplicate protection; the application itself must be idempotent.

## 21. Dry-run mode

Support:

```text
DRY_RUN=true
```

In dry-run:

- read Gmail;
- parse;
- validate;
- detect operation;
- calculate intended Airtable changes;
- log intended CREATE/UPDATE/CANCEL;
- do not write to Airtable.

Do not mark an email as successfully processed merely because dry-run parsing succeeded.

## 22. Testing requirements

Tests are mandatory.

### Parser tests
- normal date;
- date with `>>`;
- date with image artifact;
- date with different whitespace;
- date with `at`;
- date with comma;
- normal price;
- price with image artifact;
- customer name boundaries;
- missing optional fields.

### Business tests
- CREATE;
- UPDATE;
- CANCEL;
- duplicate CREATE;
- duplicate UPDATE;
- duplicate CANCEL;
- missing booking;
- time-only change;
- date change;
- no-change UPDATE;
- protected fields;
- Booking Status rules.

### Gmail tests
- label exists → skip;
- label absent → process;
- old Message ID + label absent → process;
- success → add label;
- failure → do not add label.

## 23. Real email fixtures

Maintain anonymized fixtures:

```text
tests/fixtures/create/
tests/fixtures/update/
tests/fixtures/cancel/
```

At minimum:

```text
create_normal.html
create_artifact_date.html
create_artifact_price.html
update_time_only.html
update_date_change.html
cancel_normal.html
```

Never commit sensitive customer information unless properly anonymized.

## 24. Repository abstraction

Use an interface/service boundary such as:

```python
booking_repository.create(...)
booking_repository.find_by_booking_number(...)
booking_repository.update(...)
booking_repository.cancel(...)
```

Airtable-specific API code must stay inside the Airtable repository/service.

Future implementations can be:

```text
AirtableRepository
PostgresRepository
SupabaseRepository
```

without rewriting business logic.

## 25. Provider abstraction

GetYourGuide logic must not be embedded into generic Gmail processing.

Conceptually:

```text
ProviderDetector
      ↓
GetYourGuideParser
      ↓
NormalizedBooking
```

Future providers can add their own parser.

## 26. Configuration

Avoid hard-coded operational values.

Use configuration for:

```text
GMAIL_QUERY
PROCESSED_LABEL
AIRTABLE_BASE_ID
AIRTABLE_TABLE_NAME
DRY_RUN
LOG_LEVEL
```

Default processed label:

```text
BOOKING_PROCESSED
```

## 27. Code quality

The AI developer must:

- use focused functions;
- avoid giant functions;
- avoid duplicated business rules;
- use typed models where useful;
- validate all external data;
- handle API failures;
- write regression tests for bugs;
- document non-obvious decisions;
- prefer correctness and safety over cleverness;
- avoid premature optimization.

## 28. Change management

For every significant change:

1. Identify the requirement affected.
2. Identify affected files.
3. Implement the smallest safe change.
4. Add/update tests.
5. Run relevant tests.
6. Run the full relevant suite.
7. Confirm unrelated behavior is unchanged.
8. Update this specification if the intended behavior changed.

Never silently change a business rule.

## 29. Debugging procedure

When a production issue appears:

```text
1. Capture exact email/fixture.
2. Capture Message ID.
3. Capture Booking Nr.
4. Capture operation.
5. Capture parser output.
6. Capture normalized values.
7. Capture current Airtable record.
8. Capture intended changed_fields.
9. Capture actual API request.
10. Capture API response.
11. Identify exact failing layer.
12. Add a regression test.
13. Fix smallest affected component.
14. Re-run regression test.
15. Run relevant full suite.
```

Do not blindly patch symptoms.

## 30. Required operating flow

```text
GitHub Actions starts
        ↓
Authenticate Gmail
        ↓
Find eligible emails
        ↓
Verify BOOKING_PROCESSED state
        ↓
Read email
        ↓
Detect provider
        ↓
Parse
        ↓
Validate
        ↓
Detect CREATE / UPDATE / CANCEL
        ↓
Execute safe business logic
        ↓
Verify result
        ↓
Add BOOKING_PROCESSED
        ↓
Log result
        ↓
Finish
```

If a critical step fails:

```text
Do not silently continue
Do not mark as processed
Do not write partial data
Log exact failure
Allow safe retry
```

## 31. Safe migration from Apps Script

Do not immediately disable the existing production automation.

Use:

```text
OLD APPS SCRIPT → remains production
PYTHON SYSTEM   → parallel development/testing
```

Then:

1. Build Python.
2. Unit test.
3. Test anonymized real emails.
4. Compare old vs new parser outputs.
5. Run dry-run.
6. Validate intended Airtable changes.
7. Perform controlled writes.
8. Monitor.
9. Only then disable the old system.

## 32. Definition of Done

The project is complete only when all are true:

- [ ] Gmail API works.
- [ ] OAuth refresh token works unattended.
- [ ] Gmail labels work.
- [ ] GetYourGuide detection works.
- [ ] CREATE works.
- [ ] CREATE sets Active.
- [ ] UPDATE works.
- [ ] Time-only Date Trip changes work.
- [ ] Date changes work.
- [ ] Protected fields remain protected.
- [ ] CANCEL works.
- [ ] CANCEL changes only Booking Status.
- [ ] CANCEL sets Canceled.
- [ ] Duplicate CREATE is prevented.
- [ ] Duplicate CANCEL is safe.
- [ ] Removing `BOOKING_PROCESSED` enables reprocessing.
- [ ] Message-ID history cannot block manual reprocessing.
- [ ] Failed processing does not get the processed label.
- [ ] Artifact-tolerant date parsing works.
- [ ] Artifact-tolerant price parsing works.
- [ ] Customer parsing boundaries work.
- [ ] Airtable writes are minimal and safe.
- [ ] Logging works.
- [ ] Secrets are protected.
- [ ] Dry-run works.
- [ ] Automated tests pass.
- [ ] Real anonymized fixtures pass.
- [ ] GitHub Actions works.
- [ ] PC does not need to remain running.
- [ ] Production migration is tested safely.
- [ ] Airtable is isolated behind a repository/service boundary.
- [ ] Future providers/databases can be added without rewriting core business logic.

# 33. Final instruction to the AI builder

Before writing production code:

1. Read this file completely.
2. Inspect the repository and existing files.
3. Identify the current implementation state.
4. Do not assume missing behavior.
5. Build in phases.
6. Create tests alongside critical business logic.
7. Do not enable destructive production writes before testing/dry-run.
8. Preserve every rule in this document.
9. Every bug fix must include a regression test.
10. Before completion, verify every Definition of Done item.

**Most important principle:**

> The system must be designed so that unexpected email formatting, duplicate execution, retries, timezone representation, manually removed Gmail labels, cancellation emails, or partial API failures cannot silently corrupt Airtable data.

**Correctness, safety, idempotency, traceability, and testability are more important than implementation speed.**

If two requirements conflict, stop and resolve the conflict explicitly. Never guess.
