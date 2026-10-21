import os
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dateutil import tz
from dateutil import parser as dateutil_parser

from app.models.booking import AirtableBookingRecord
from app.repositories.booking_repository import BookingRepository

logger = logging.getLogger(__name__)


class BaserowRepository(BookingRepository):
    """
    Repository implementation for Baserow databases (such as TourCare).
    Implements BookingRepository interface for seamless multi-platform sync.
    Normalizes local datetime to UTC when sending to Baserow, and parses UTC
    back to local time when reading from Baserow, preventing timezone hour shifts.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        table_id: Optional[str] = None,
        token: Optional[str] = None,
        local_timezone: Optional[str] = None
    ):
        raw_url = base_url or os.getenv("BASEROW_URL", "https://booking.tourcare.ai")
        self.base_url = raw_url.rstrip("/") if raw_url else ""
        self.table_id = str(table_id or os.getenv("BASEROW_TABLE_ID", "1194"))
        self.token = token or os.getenv("BASEROW_TOKEN", "")
        self.local_timezone = local_timezone or os.getenv("LOCAL_TIMEZONE", "Africa/Cairo")

        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

        self.table_url = (
            f"{self.base_url}/api/database/rows/table/{self.table_id}/"
            if self.base_url and self.table_id
            else ""
        )

    def _format_date_for_baserow(self, date_val: Any) -> Any:
        """
        Converts a local date/time (string or datetime) into a UTC ISO 8601 string
        ending in 'Z' for Baserow.

        Baserow stores all timestamps internally in UTC and applies the local 
        timezone (e.g. Africa/Cairo, EEST UTC+3) when rendering in the UI.
        If a naive local timestamp (e.g. 18:00) is submitted directly without timezone,
        Baserow interprets it as UTC, causing the UI to add +3 hours and display 21:00.
        Normalizing to UTC (e.g. 15:00:00Z) ensures the Baserow UI displays exactly 18:00.
        """
        if not date_val:
            return date_val

        try:
            tz_local = tz.gettz(self.local_timezone) or tz.gettz("Africa/Cairo")
            tz_utc = tz.tzutc()

            if isinstance(date_val, datetime):
                dt = date_val
            elif isinstance(date_val, str):
                cleaned = date_val.strip()
                # If pure date YYYY-MM-DD without time, do not alter timezone
                if ":" not in cleaned and "T" not in cleaned:
                    return date_val
                dt = dateutil_parser.parse(cleaned)
            else:
                return date_val

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz_local)

            utc_dt = dt.astimezone(tz_utc)
            return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception as e:
            logger.warning(f"Could not format date '{date_val}' for Baserow: {e}")
            return date_val

    def _format_date_from_baserow(self, date_val: Any) -> Any:
        """
        Converts a UTC timestamp returned by Baserow (e.g. '2026-10-21T15:00:00Z')
        back into a local naive ISO string (e.g. '2026-10-21T18:00:00') matching
        the local time expected by AirtableBookingRecord and logic comparisons.
        """
        if not date_val or not isinstance(date_val, str):
            return date_val

        try:
            cleaned = date_val.strip()
            if ":" not in cleaned and "T" not in cleaned:
                return date_val

            dt = dateutil_parser.parse(cleaned)
            if dt.tzinfo is not None:
                tz_local = tz.gettz(self.local_timezone) or tz.gettz("Africa/Cairo")
                local_dt = dt.astimezone(tz_local)
                return local_dt.strftime("%Y-%m-%dT%H:%M:%S")
            return date_val
        except Exception as e:
            logger.warning(f"Could not format date '{date_val}' from Baserow: {e}")
            return date_val

    def find_by_booking_number(
        self,
        booking_nr: str
    ) -> Optional[AirtableBookingRecord]:
        if not self.table_url or not self.token:
            logger.warning("Baserow URL or Token not configured, skipping find.")
            return None

        params = {
            "user_field_names": "true",
            "search": booking_nr
        }

        response = requests.get(
            self.table_url,
            headers=self.headers,
            params=params,
            timeout=15
        )

        if not response.ok:
            raise RuntimeError(
                f"Baserow FIND failed: HTTP {response.status_code} | "
                f"Response: {response.text}"
            )

        data = response.json()
        results = data.get("results", [])

        # Match exact booking number
        target_row = None
        for row in results:
            if str(row.get("Booking Nr.", "")).strip() == booking_nr.strip():
                target_row = row
                break

        if not target_row:
            return None

        target_row_copy = dict(target_row)
        if "Date Trip" in target_row_copy and target_row_copy["Date Trip"]:
            target_row_copy["Date Trip"] = self._format_date_from_baserow(target_row_copy["Date Trip"])

        return AirtableBookingRecord(**target_row_copy)

    def create(self, record: AirtableBookingRecord) -> bool:
        if not self.table_url or not self.token:
            logger.warning("Baserow URL or Token not configured, skipping create.")
            return False

        fields = record.model_dump(
            by_alias=True,
            exclude_none=True
        )

        if "Date Trip" in fields and fields["Date Trip"]:
            fields["Date Trip"] = self._format_date_for_baserow(fields["Date Trip"])

        params = {
            "user_field_names": "true"
        }

        response = requests.post(
            self.table_url,
            headers=self.headers,
            params=params,
            json=fields,
            timeout=15
        )

        if not response.ok:
            raise RuntimeError(
                f"Baserow CREATE failed: HTTP {response.status_code} | "
                f"Response: {response.text}"
            )

        return True

    def update(
        self,
        booking_nr: str,
        changed_fields: Dict[str, Any]
    ) -> bool:
        if not self.table_url or not self.token:
            logger.warning("Baserow URL or Token not configured, skipping update.")
            return False

        # Find row ID by search
        params = {
            "user_field_names": "true",
            "search": booking_nr
        }

        response = requests.get(
            self.table_url,
            headers=self.headers,
            params=params,
            timeout=15
        )

        if not response.ok:
            raise RuntimeError(
                f"Baserow FIND FOR UPDATE failed: "
                f"HTTP {response.status_code} | "
                f"Response: {response.text}"
            )

        data = response.json()
        results = data.get("results", [])

        target_id = None
        for row in results:
            if str(row.get("Booking Nr.", "")).strip() == booking_nr.strip():
                target_id = row.get("id")
                break

        if target_id is None:
            return False

        payload = dict(changed_fields)
        if "Date Trip" in payload and payload["Date Trip"]:
            payload["Date Trip"] = self._format_date_for_baserow(payload["Date Trip"])

        patch_url = f"{self.table_url}{target_id}/"
        patch_response = requests.patch(
            patch_url,
            headers=self.headers,
            params={"user_field_names": "true"},
            json=payload,
            timeout=15
        )

        if not patch_response.ok:
            raise RuntimeError(
                f"Baserow UPDATE failed: "
                f"HTTP {patch_response.status_code} | "
                f"Response: {patch_response.text}"
            )

        return True
