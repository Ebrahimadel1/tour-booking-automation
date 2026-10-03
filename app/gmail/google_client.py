from __future__ import annotations

import base64
import re
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.gmail.client import GmailClient
from app.gmail.labels import GmailLabels
from app.gmail.messages import GmailMessage


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"


def get_gmail_credentials() -> Credentials:
    """Load existing Gmail OAuth credentials or start OAuth flow."""

    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"Missing Google OAuth credentials: {CREDENTIALS_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
        )

        credentials = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent",
        )

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return credentials


class GoogleGmailClient(GmailClient):
    """Real Gmail API implementation of the GmailClient contract."""

    def __init__(self, credentials: Credentials | None = None):
        self.credentials = credentials or get_gmail_credentials()

        self.service = build(
            "gmail",
            "v1",
            credentials=self.credentials,
            cache_discovery=False,
        )

    def search_messages(self, query: str) -> list[GmailMessage]:
        """Search Gmail and return full GmailMessage objects."""

        messages: list[GmailMessage] = []
        page_token: str | None = None

        while True:
            response = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    pageToken=page_token,
                )
                .execute()
            )

            for item in response.get("messages", []):
                message_id = item["id"]

                raw_message = (
                    self.service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message_id,
                        format="full",
                    )
                    .execute()
                )

                messages.append(self._convert_message(raw_message))

            page_token = response.get("nextPageToken")

            if not page_token:
                break

        return messages

    def get_label_id(self, label_name: str) -> str | None:
        """Return Gmail label ID, creating the label if necessary."""

        response = (
            self.service.users()
            .labels()
            .list(userId="me")
            .execute()
        )

        for label in response.get("labels", []):
            if label.get("name") == label_name:
                return label.get("id")

        # Create the label if it does not exist.
        created = (
            self.service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )

        return created.get("id")

    def add_label(self, message_id: str, label_id: str) -> bool:
        """Add a Gmail label to a message."""

        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={
                "addLabelIds": [label_id],
            },
        ).execute()

        return True

    def remove_label(self, message_id: str, label_id: str) -> bool:
        """Remove a Gmail label from a message."""

        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={
                "removeLabelIds": [label_id],
            },
        ).execute()

        return True

    @staticmethod
    def _convert_message(raw_message: dict[str, Any]) -> GmailMessage:
        """Convert Gmail API message to the application's GmailMessage."""

        payload = raw_message.get("payload", {})

        headers = {
            header.get("name", "").lower(): header.get("value", "")
            for header in payload.get("headers", [])
        }

        plain_text, html = GoogleGmailClient._extract_bodies(payload)

        received_at = None

        internal_date = raw_message.get("internalDate")

        if internal_date:
            from datetime import datetime, timezone

            received_at = datetime.fromtimestamp(
                int(internal_date) / 1000,
                tz=timezone.utc,
            )
        elif headers.get("date"):
            try:
                received_at = parsedate_to_datetime(headers["date"])
            except Exception:
                received_at = None

        return GmailMessage(
            thread_id=raw_message.get("threadId", ""),
            message_id=raw_message.get("id", ""),
            subject=headers.get("subject", ""),
            sender=headers.get("from", ""),
            received_at=received_at,
            plain_text=plain_text,
            html=html,
            labels=raw_message.get("labelIds", []),
        )

    @staticmethod
    def _extract_bodies(
        payload: dict[str, Any],
    ) -> tuple[str, str]:
        """Extract plain text and HTML recursively from Gmail payload."""

        plain_parts: list[str] = []
        html_parts: list[str] = []

        def walk(part: dict[str, Any]) -> None:
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            data = body.get("data")

            if data:
                try:
                    decoded = base64.urlsafe_b64decode(data).decode(
                        "utf-8",
                        errors="replace",
                    )
                except Exception:
                    decoded = ""

                if mime_type == "text/plain":
                    plain_parts.append(decoded)

                elif mime_type == "text/html":
                    html_parts.append(decoded)

            for child in part.get("parts", []) or []:
                walk(child)

        walk(payload)

        plain_text = "\n".join(plain_parts)
        html = "\n".join(html_parts)

        if not plain_text and html:
            plain_text = GoogleGmailClient._html_to_text(html)

        return plain_text, html

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Basic HTML-to-text fallback."""

        text = re.sub(
            r"<(script|style).*?>.*?</\1>",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        return text.strip()


if __name__ == "__main__":
    print("Connecting to Gmail...")

    client = GoogleGmailClient()

    label_id = client.get_label_id(
        GmailLabels.BOOKING_PROCESSED
    )

    print("Gmail connection successful!")
    print(f"Processed label ID: {label_id}")

    messages = client.search_messages(
        'from:(getyourguide.com) -label:BOOKING_PROCESSED'
    )

    print(f"Found {len(messages)} unprocessed messages.")

    for message in messages[:10]:
        print("-" * 60)
        print(f"Message ID: {message.message_id}")
        print(f"Subject: {message.subject}")
        print(f"From: {message.sender}")
        print(f"Date: {message.received_at}")